from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from integrations.roads_api import snap_to_roads
from integrations.firebase_admin import rtdb_set, rtdb_push, init_firebase
from firebase_admin import db

# Optional: auto-trigger Gemini TRACK_TICK (internal call)
# If you don't want this, keep it False and let frontend/center ping /gemini/run periodically.
ENABLE_AUTO_GEMINI = False
AUTO_GEMINI_MIN_INTERVAL_S = 20  # rate limit per booking

try:
    import httpx
except Exception:
    httpx = None  # safe fallback

router = APIRouter(prefix="/tracking", tags=["tracking"])

# In-memory store for demo / debugging
LATEST_BY_BOOKING: dict[str, dict] = {}
LAST_AUTO_GEMINI_AT: dict[str, float] = {}  # epoch seconds per booking


class TrackUpdateReq(BaseModel):
    bookingId: str = Field(..., min_length=8)
    lat: float
    lng: float
    accuracy_m: Optional[float] = None
    speed_mps: Optional[float] = None
    heading_deg: Optional[float] = None
    timestamp_ms: Optional[int] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(x: Optional[float]) -> Optional[float]:
    try:
        return None if x is None else float(x)
    except Exception:
        return None


def _compute_signals(prev: Optional[Dict[str, Any]], cur: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight derived signals for Gemini TRACK_TICK.
    No heavy geo math; just useful heuristics.
    """
    # current snapped point is preferred
    snapped = cur.get("snapped") or {}
    raw = cur.get("raw") or {}

    speed = _safe_float(cur.get("speed_mps"))
    accuracy = _safe_float(cur.get("accuracy_m"))
    source = snapped.get("source") or "UNKNOWN"

    # Simple flags
    low_speed = (speed is not None and speed < 0.3)  # ~standing still
    poor_accuracy = (accuracy is not None and accuracy > 40.0)
    snapped_failed = (source == "RAW_FALLBACK")

    # stationary counter (best-effort)
    stationary_streak = 0
    if prev and isinstance(prev.get("signals"), dict):
        stationary_streak = int(prev["signals"].get("stationary_streak") or 0)

    if low_speed:
        stationary_streak = min(stationary_streak + 1, 1000)
    else:
        stationary_streak = 0

    # Quick drift check (not exact distance; just large delta in lat/lng)
    drift_flag = False
    if prev:
        prev_snap = (prev.get("snapped") or {})
        try:
            dlat = abs(float(snapped.get("lat", 0)) - float(prev_snap.get("lat", 0)))
            dlng = abs(float(snapped.get("lng", 0)) - float(prev_snap.get("lng", 0)))
            if dlat > 0.01 or dlng > 0.01:  # very rough (~1km+)
                drift_flag = True
        except Exception:
            drift_flag = False

    return {
        "speed_mps": speed,
        "low_speed": low_speed,
        "stationary_streak": stationary_streak,
        "accuracy_m": accuracy,
        "poor_accuracy": poor_accuracy,
        "snapped_failed": snapped_failed,
        "drift_flag": drift_flag,
        "snapped_source": source,
        "computedAt": _now_iso(),
    }


def _get_case_coverage(booking_id: str) -> str:
    """
    Reads /cases/{bookingId}/coverage.
    Returns "SLICE" if missing (safe default).
    """
    try:
        init_firebase()
        cov = db.reference(f"/cases/{booking_id}/coverage").get()
        return cov or "SLICE"
    except Exception:
        return "SLICE"


async def _maybe_trigger_gemini_track_tick(booking_id: str) -> None:
    """
    Optional internal auto-trigger for TRACK_TICK.
    Rate-limited and best-effort; won't break tracking.
    """
    if not ENABLE_AUTO_GEMINI or httpx is None:
        return

    # Only for FULL coverage
    coverage = _get_case_coverage(booking_id)
    if coverage != "FULL":
        return

    # Rate limit
    now_epoch = datetime.now(timezone.utc).timestamp()
    last = float(LAST_AUTO_GEMINI_AT.get(booking_id) or 0)
    if (now_epoch - last) < AUTO_GEMINI_MIN_INTERVAL_S:
        return

    LAST_AUTO_GEMINI_AT[booking_id] = now_epoch

    # IMPORTANT: set your backend base URL here if needed
    # If running in same server, you might not want internal HTTP at all.
    GEMINI_URL = f"http://127.0.0.1:8000/gemini/run/{booking_id}"

    payload = {
        "checkpoint": "TRACK_TICK",
        "userSignal": None,
        "note": "auto_track_tick",
        "max_recent_messages": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            await client.post(GEMINI_URL, json=payload)
    except Exception:
        # best effort only
        return


@router.post("/update")
async def tracking_update(req: TrackUpdateReq):
    # 1️⃣ Sanity check
    if not (-90 <= req.lat <= 90) or not (-180 <= req.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid lat/lng range")

    now = _now_iso()

    raw_point = {"lat": req.lat, "lng": req.lng}

    # 2️⃣ Snap to roads (best effort)
    snapped = await snap_to_roads(req.lat, req.lng)
    if snapped:
        snapped_point = {"lat": snapped[0], "lng": snapped[1], "source": "ROADS_API"}
    else:
        snapped_point = {"lat": req.lat, "lng": req.lng, "source": "RAW_FALLBACK"}

    # 3️⃣ Unified payload (realtime event)
    payload: Dict[str, Any] = {
        "bookingId": req.bookingId,
        "raw": raw_point,
        "snapped": snapped_point,
        "accuracy_m": req.accuracy_m,
        "speed_mps": req.speed_mps,
        "heading_deg": req.heading_deg,
        "timestamp_ms": req.timestamp_ms,
        "receivedAt": now,
    }

    # 4️⃣ Derived signals for Gemini (lightweight)
    prev = LATEST_BY_BOOKING.get(req.bookingId)
    signals = _compute_signals(prev, payload)
    payload["signals"] = signals

    # 5️⃣ Keep in-memory (local debug / fallback)
    LATEST_BY_BOOKING[req.bookingId] = payload

    # 6️⃣ Firebase realtime write (best effort, do NOT crash demo)
    try:
        # latest position (overwrite)
        rtdb_set(f"/live/{req.bookingId}/latest", payload)

        # history stream (append) - Gemini TRACK_TICK can use last N points
        rtdb_push(f"/live/{req.bookingId}/history", payload)

        # optional: also store signals in a fixed location for quick UI
        rtdb_set(f"/live/{req.bookingId}/signals", signals)
    except Exception:
        pass

    # 7️⃣ Optional: auto-trigger Gemini track tick (FULL coverage only)
    # If you prefer polling from frontend/center, keep ENABLE_AUTO_GEMINI=False.
    try:
        await _maybe_trigger_gemini_track_tick(req.bookingId)
    except Exception:
        pass

    return {
        "status": "ok",
        "saved": True,
        "receivedAt": now,
        "snapped": snapped_point,
        "signals": signals,
    }


@router.get("/latest/{bookingId}")
def tracking_latest(bookingId: str):
    data = LATEST_BY_BOOKING.get(bookingId)
    if not data:
        raise HTTPException(status_code=404, detail="No tracking data yet for this bookingId")
    return data

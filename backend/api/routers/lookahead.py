# api/routers/lookahead.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from firebase_admin import db
from integrations.firebase_admin import init_firebase
from integrations.places_api import segment_places_summary

# ✅ OSM/Overpass summary (segment-based)
try:
    from integrations.osm_overpass import segment_overpass_summary
except Exception:
    segment_overpass_summary = None  # type: ignore

try:
    from integrations.polyline_tools import decode_polyline
except Exception:
    decode_polyline = None  # type: ignore

router = APIRouter(prefix="/lookahead", tags=["lookahead"])


# -----------------------------
# Request model
# -----------------------------
class LookaheadReq(BaseModel):
    bookingId: str = Field(..., min_length=6)
    distance_m: int = Field(500, ge=100, le=2000)

    # sample points along next segment (fractions of segment length)
    sample_fracs: List[float] = Field(default_factory=lambda: [0.25, 0.60, 1.0])

    # Places config
    places_radius_m: int = Field(200, ge=50, le=500)
    places_max_results: int = Field(20, ge=1, le=50)

    # OSM config (demo-safe)
    osm_radius_m: int = Field(500, ge=100, le=1500)

    # ✅ NEW: micro trail target length
    micro_distance_m: int = Field(100, ge=50, le=300)

    # ✅ NEW: keep stored geometry light
    store_segment_points_max: int = Field(60, ge=0, le=200)


# -----------------------------
# Helpers
# -----------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_root(booking_id: str) -> str:
    return f"/cases/{booking_id}"


def _live_latest_path(booking_id: str) -> str:
    return f"/live/{booking_id}/latest"


def _lookahead_path(booking_id: str) -> str:
    return f"/cases/{booking_id}/lookahead/latest"


def _haversine_m(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    import math

    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _closest_index(points: List[Tuple[float, float]], cur: Tuple[float, float]) -> int:
    best_i = 0
    best_d = float("inf")
    for i, p in enumerate(points):
        d = _haversine_m(p, cur)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


def _extract_polyline_from_case(case: Dict[str, Any]) -> Optional[str]:
    journey = case.get("journey") or {}
    if isinstance(journey, dict) and isinstance(journey.get("polyline"), str):
        return journey["polyline"]

    if isinstance(case.get("polyline"), str):
        return case["polyline"]

    route = case.get("route") or {}
    if isinstance(route, dict) and isinstance(route.get("polyline"), str):
        return route["polyline"]

    return None


def _to_latlng_dict(lat: float, lng: float) -> Dict[str, float]:
    return {"lat": float(lat), "lng": float(lng)}


def _reduce_points(points: List[Dict[str, float]], max_n: int) -> List[Dict[str, float]]:
    """
    Reduce points to <= max_n evenly spaced points.
    If max_n <= 0, return [].
    """
    if max_n <= 0:
        return []
    n = len(points)
    if n <= max_n:
        return points
    if max_n == 1:
        return [points[-1]]
    # even spacing including first and last
    idxs = [round(i * (n - 1) / (max_n - 1)) for i in range(max_n)]
    out: List[Dict[str, float]] = []
    last_i = -1
    for i in idxs:
        if i != last_i:
            out.append(points[i])
            last_i = i
    return out


def _compute_micro_trail(
    segment_points: List[Dict[str, float]],
    target_m: int,
    max_points: int = 3,
) -> Dict[str, Any]:
    """
    Build first ~target_m forward trail from segment_points.
    Returns 2–5 points max (default 3) with end point.
    """
    if not segment_points:
        return {"distance_m": target_m, "points": [], "end": None}

    # convert to tuples
    pts: List[Tuple[float, float]] = [(p["lat"], p["lng"]) for p in segment_points]

    walked = 0.0
    picked: List[Dict[str, float]] = [segment_points[0]]
    i = 0

    while i < len(pts) - 1 and walked < float(target_m):
        a = pts[i]
        b = pts[i + 1]
        walked += _haversine_m(a, b)
        picked.append(_to_latlng_dict(b[0], b[1]))
        i += 1
        if len(picked) > 1000:
            break

    # downsample for subcenter (keep tiny)
    picked_small = _reduce_points(picked, max_points)
    end = picked_small[-1] if picked_small else None

    return {
        "distance_m": int(target_m),
        "points": picked_small,
        "end": end,
        "points_full_count": len(picked),
    }


def _area_label_from_case(case: Dict[str, Any], seg_start_index: int, seg_total_points_hint: int) -> str:
    """
    Deterministic area label:
    - Prefer case.journey.areas if present (list of {index, name} or strings)
    - Map seg_start_index to nearest area index by proportional scaling.
    """
    journey = case.get("journey") or {}
    areas = None
    if isinstance(journey, dict):
        areas = journey.get("areas")

    if not areas:
        # fallback: try case.areas
        areas = case.get("areas")

    if not areas or not isinstance(areas, list) or len(areas) == 0:
        return "—"

    # Normalize to list of names
    names: List[str] = []
    for a in areas:
        if isinstance(a, str):
            names.append(a)
        elif isinstance(a, dict) and isinstance(a.get("name"), str):
            names.append(a["name"])
    if not names:
        return "—"

    # Map polyline index -> area bucket
    # seg_total_points_hint is roughly polyline length; if not known use 1.
    denom = max(int(seg_total_points_hint) - 1, 1)
    frac = max(0.0, min(1.0, float(seg_start_index) / float(denom)))
    a_idx = round(frac * (len(names) - 1))
    a_idx = max(0, min(len(names) - 1, a_idx))
    return names[a_idx] or "—"


def _segment_from_polyline(encoded_polyline: str, current: Tuple[float, float], distance_m: int) -> Dict[str, Any]:
    if not decode_polyline:
        raise RuntimeError(
            "decode_polyline not found. Export decode_polyline(encoded)->[{lat,lng},...] in integrations/polyline_tools.py"
        )

    raw_pts = decode_polyline(encoded_polyline)
    if not raw_pts or len(raw_pts) < 2:
        raise HTTPException(status_code=400, detail="Polyline decode failed or too few points")

    pts: List[Tuple[float, float]] = [(float(p["lat"]), float(p["lng"])) for p in raw_pts]

    start_i = _closest_index(pts, current)

    seg: List[Tuple[float, float]] = [pts[start_i]]
    walked = 0.0
    i = start_i

    while i < len(pts) - 1 and walked < float(distance_m):
        a = pts[i]
        b = pts[i + 1]
        d = _haversine_m(a, b)
        walked += d
        seg.append(b)
        i += 1
        if len(seg) > 4000:
            break

    end = seg[-1]

    cum: List[float] = [0.0]
    for k in range(1, len(seg)):
        cum.append(cum[-1] + _haversine_m(seg[k - 1], seg[k]))
    total = max(cum[-1], 1.0)

    def point_at_frac(frac: float) -> Tuple[float, float]:
        target = max(0.0, min(1.0, float(frac))) * total
        for k in range(1, len(cum)):
            if cum[k] >= target:
                return seg[k]
        return end

    return {
        "start_index": start_i,
        "end_index": i,
        "segment_m_approx": round(total, 2),
        "segment_points": [_to_latlng_dict(lat, lng) for (lat, lng) in seg],
        "segment_end": _to_latlng_dict(end[0], end[1]),
        "sample_points": [],
        "polyline_points_count": len(pts),
        "point_at_frac": point_at_frac,  # internal callable
    }


# -----------------------------
# Endpoint
# -----------------------------
@router.post("/500m")
async def lookahead_500m(req: LookaheadReq):
    """
    POST /lookahead/500m

    Reads:
      /cases/{bookingId} -> polyline
      /live/{bookingId}/latest -> current snapped point

    Computes:
      next {distance_m} segment

    Samples:
      points at req.sample_fracs

    Calls (ONLY HERE):
      - Places Nearby Search on each sample point
      - OSM/Overpass segment summary (optional, fail-safe)

    Stores (single source of truth):
      /cases/{bookingId}/lookahead/latest
        - segment summary (+ optional reduced points)
        - samplePoints
        - places_summary
        - osm_summary
        - microTrail100m
        - locationHint (areaLabel + optional nearbyAddress)
    """
    init_firebase()

    case = db.reference(_case_root(req.bookingId)).get()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found for this bookingId")

    polyline = _extract_polyline_from_case(case)
    if not polyline:
        raise HTTPException(
            status_code=400,
            detail="Polyline not found in case. Store it in /cases/{bookingId}/journey/polyline during booking confirm.",
        )

    live_latest = db.reference(_live_latest_path(req.bookingId)).get()
    if not live_latest or not isinstance(live_latest, dict):
        raise HTTPException(status_code=400, detail="Live latest not found. Send /tracking/update first.")

    snapped = live_latest.get("snapped") or live_latest.get("raw") or {}
    if not isinstance(snapped, dict) or "lat" not in snapped or "lng" not in snapped:
        raise HTTPException(status_code=400, detail="Live latest missing snapped/raw lat/lng")

    cur = (float(snapped["lat"]), float(snapped["lng"]))
    seg_info = _segment_from_polyline(polyline, cur, req.distance_m)

    # sample points along the computed segment
    point_at_frac = seg_info.pop("point_at_frac")
    samples: List[Dict[str, float]] = []
    for f in req.sample_fracs:
        p = point_at_frac(float(f))
        samples.append(_to_latlng_dict(p[0], p[1]))
    seg_info["sample_points"] = samples

    # ✅ NEW: micro trail (~100m) derived from the segment points
    micro = _compute_micro_trail(
        segment_points=seg_info.get("segment_points", []),
        target_m=req.micro_distance_m,
        max_points=3,  # keep tiny for subcenter
    )

    # ✅ NEW: deterministic area label (based on case journey areas + polyline index)
    area_label = _area_label_from_case(
        case=case,
        seg_start_index=int(seg_info.get("start_index", 0)),
        seg_total_points_hint=int(seg_info.get("polyline_points_count", 1)),
    )

    # ✅ optional address (keep deploy-safe; plug integration later)
    nearby_address: Optional[str] = None
    location_hint = {
        "areaLabel": area_label,
        "nearbyAddress": nearby_address,
        "source": "none" if not nearby_address else "reverse_geocode",
    }

    # ✅ Places summary
    places = await segment_places_summary(
        samples=samples,
        radius_m=req.places_radius_m,
        max_results=req.places_max_results,
    )

    # ✅ OSM summary (fail-safe)
    osm_summary: Optional[Dict[str, Any]] = None
    osm_warning: Optional[str] = None

    if segment_overpass_summary is None:
        osm_warning = "integrations.osm_overpass.segment_overpass_summary not available"
    else:
        try:
            osm_summary = await segment_overpass_summary(
                samples=samples,
                radius_m=req.osm_radius_m,
            )
        except Exception as e:
            osm_summary = {
                "samples": samples,
                "radius_m": req.osm_radius_m,
                "merged": {},
                "per_sample": [],
                "error": str(e)[:180],
            }
            osm_warning = "OSM/Overpass unavailable; continuing with Places only"

    now = _now_iso()

    # ✅ keep stored geometry light
    seg_points_full = seg_info.get("segment_points", [])
    seg_points_reduced = _reduce_points(seg_points_full, req.store_segment_points_max)

    stored_snapshot: Dict[str, Any] = {
        "at": now,
        "distance_m": req.distance_m,
        "sampleFractions": req.sample_fracs,
        "samplePoints": samples,
        "segment": {
            "start_index": seg_info.get("start_index"),
            "end_index": seg_info.get("end_index"),
            "segment_m_approx": seg_info.get("segment_m_approx"),
            "segment_end": seg_info.get("segment_end"),
            "pointsReduced": seg_points_reduced,
        },
        "places_summary": places,
        "osm_summary": osm_summary,
        "microTrail100m": micro,
        "locationHint": location_hint,
    }
    if osm_warning:
        stored_snapshot["osm_warning"] = osm_warning

    # Store latest lookahead snapshot (so gemini worker + UI can reuse it)
    db.reference(_lookahead_path(req.bookingId)).set(stored_snapshot)
    db.reference(_case_root(req.bookingId)).update({"updatedAt": now})

    # Response can include full segment geometry for UI/debug (not stored)
    return {
        "status": "ok",
        "bookingId": req.bookingId,
        "at": now,
        "distance_m_requested": req.distance_m,
        "current": {"source": "live_latest", "snapped": _to_latlng_dict(cur[0], cur[1])},
        "segment": seg_info,  # full geometry in response for UI/debug
        "microTrail100m": micro,
        "locationHint": location_hint,
        "places_summary": places,
        "osm_summary": osm_summary,
        "osm_warning": osm_warning,
        "lookahead_latest": stored_snapshot,  # exactly what we stored
    }

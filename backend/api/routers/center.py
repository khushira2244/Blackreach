from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from integrations.firebase_admin import init_firebase
from firebase_admin import db

router = APIRouter(prefix="/center", tags=["center"])


def _get(path: str):
    init_firebase()
    return db.reference(path).get()


@router.get("/main/active")
def main_active():
    """
    Returns a list of active cases for the Main Center dashboard.
    """
    cases = _get("/cases") or {}
    out: List[Dict[str, Any]] = []

    for booking_id, c in cases.items():
        state = c.get("state")
        if state in ("ACTIVE", "IN_ZONE", "EMERGENCY"):
            out.append(
                {
                    "bookingId": booking_id,
                    "state": state,
                    "mode": c.get("mode"),
                    "updatedAt": c.get("updatedAt"),
                    "subcenter": c.get("subcenter", {}),
                    "personnel": c.get("personnel", {}),
                }
            )

    # Sort by updatedAt (latest first) if present
    out.sort(key=lambda x: x.get("updatedAt") or "", reverse=True)
    return {"status": "ok", "active": out, "count": len(out)}


@router.get("/main/room/{bookingId}")
def main_room(bookingId: str):
    """
    Single payload for the "Surveillance Room" screen.
    Combines:
      - case brain (/cases/{bookingId})
      - live tracking (/live/{bookingId}/latest)
      - recent timeline events (last N)
    """
    case = _get(f"/cases/{bookingId}")
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    latest = _get(f"/live/{bookingId}/latest")  # may be None if tracking not started yet
    timeline = _get(f"/cases/{bookingId}/timeline") or {}

  
    events: List[Dict[str, Any]] = []
    for _, v in timeline.items():
        if isinstance(v, dict):
            events.append(v)
    events.sort(key=lambda e: e.get("at") or "", reverse=True)
    events = events[:20]

    return {
        "status": "ok",
        "bookingId": bookingId,
        "case": case,
        "live": {"latest": latest},
        "timeline": events,
    }


@router.get("/subcenter/{subcenterId}/queue")
def subcenter_queue(subcenterId: str):
    """
    List cases assigned/activated for a given subcenter.
    """
    cases = _get("/cases") or {}
    out: List[Dict[str, Any]] = []

    for booking_id, c in cases.items():
        sub = c.get("subcenter") or {}
        if sub.get("activated") and sub.get("subcenter_id") == subcenterId:
            out.append(
                {
                    "bookingId": booking_id,
                    "state": c.get("state"),
                    "updatedAt": c.get("updatedAt"),
                    "personnel": c.get("personnel", {}),
                    "note": sub.get("note"),
                }
            )

    out.sort(key=lambda x: x.get("updatedAt") or "", reverse=True)
    return {"status": "ok", "subcenterId": subcenterId, "queue": out, "count": len(out)}


@router.get("/subcenter/{subcenterId}/room/{bookingId}")
def subcenter_room(subcenterId: str, bookingId: str):
    """
    Subcenter view for a specific booking.
    Ensures the case is assigned to this subcenter.
    """
    case = _get(f"/cases/{bookingId}")
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    sub = case.get("subcenter") or {}
    if not (sub.get("activated") and sub.get("subcenter_id") == subcenterId):
        raise HTTPException(status_code=403, detail="Case not assigned to this subcenter")

    latest = _get(f"/live/{bookingId}/latest")
    timeline = _get(f"/cases/{bookingId}/timeline") or {}

    events: List[Dict[str, Any]] = []
    for _, v in timeline.items():
        if isinstance(v, dict):
            events.append(v)
    events.sort(key=lambda e: e.get("at") or "", reverse=True)
    events = events[:20]

    return {
        "status": "ok",
        "subcenterId": subcenterId,
        "bookingId": bookingId,
        "case": case,
        "live": {"latest": latest},
        "timeline": events,
    }

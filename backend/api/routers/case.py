from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from integrations.firebase_admin import init_firebase
from  integrations.firebase_admin import db

router = APIRouter(prefix="/case", tags=["case"])

CaseState = Literal["ACTIVE", "IN_ZONE", "EMERGENCY", "RESOLVED"]
PersonnelStatus = Literal["PENDING", "ACK", "ENROUTE", "ARRIVED", "RESOLVED"]

Coverage = Literal["SLICE", "FULL"]


class SelectedSlice(BaseModel):
    start_index: int = Field(..., ge=0)
    end_index: int = Field(..., ge=0)
    areas: list[str] = Field(..., min_length=2)


class CaseCreateReq(BaseModel):
    bookingId: str = Field(..., min_length=8)
    mode: Literal["TRACKING", "PERSONNEL"] = "TRACKING"
    selected: SelectedSlice
    coverage: Coverage = "SLICE"
    user_note: Optional[str] = None


class EmergencyReq(BaseModel):
    reason: str = Field(..., min_length=2)


class ActivateSubcenterReq(BaseModel):
    subcenter_id: str = Field(..., min_length=2)
    note: Optional[str] = None

    # ✅ NEW (optional): operator context (written by gemini normally)
    areaLabel: Optional[str] = None
    nearbyAddress: Optional[str] = None
    microTrailEnd: Optional[Dict[str, float]] = None
    brief: Optional[Dict[str, Any]] = None


class StateChangeReq(BaseModel):
    state: CaseState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_root(booking_id: str) -> str:
    return f"/cases/{booking_id}"


def _timeline_push(booking_id: str, event: str, extra: Optional[Dict[str, Any]] = None) -> None:
    init_firebase()
    now = _now_iso()
    payload: Dict[str, Any] = {"at": now, "event": event}
    if extra:
        payload["extra"] = extra
    db.reference(f"/cases/{booking_id}/timeline").push(payload)


def _get_case_or_404(booking_id: str) -> Dict[str, Any]:
    init_firebase()
    data = db.reference(_case_root(booking_id)).get()
    if not data:
        raise HTTPException(status_code=404, detail="Case not found for this bookingId")
    return data


@router.post("/create")
def create_case(req: CaseCreateReq):
    # Validate slice indices
    if req.selected.start_index >= req.selected.end_index:
        raise HTTPException(status_code=400, detail="end_index must be greater than start_index")

    if req.selected.start_index >= len(req.selected.areas):
        raise HTTPException(status_code=400, detail="start_index must be < len(areas)")

    if req.selected.end_index >= len(req.selected.areas):
        raise HTTPException(status_code=400, detail="end_index must be < len(areas)")

    init_firebase()
    root = _case_root(req.bookingId)
    existing = db.reference(root).get()
    if existing:
        return {"status": "exists", "case": existing}

    now = _now_iso()
    case_obj = {
        "bookingId": req.bookingId,
        "createdAt": now,
        "updatedAt": now,
        "state": "ACTIVE",
        "mode": req.mode,
        "coverage": req.coverage,
        "selected": req.selected.model_dump(),
        "emergency": {"active": False},

        # ✅ subcenter metadata (expanded)
        "subcenter": {
            "activated": False,
            "subcenter_id": None,
            "activatedAt": None,
            "note": None,

            # ✅ NEW: operator hints (written by gemini using lookahead snapshot)
            "areaLabel": None,
            "nearbyAddress": None,
            "microTrailEnd": None,
            "brief": None,
        },

        "personnel": {"status": "PENDING"},
        "user_note": req.user_note,

        # ✅ stable defaults (important)
        # NOTE: lookahead truth lives at /cases/{bookingId}/lookahead/latest
        # We keep this pointer shape to avoid breaking older frontend reads.
        "lookahead": {"latest": None},
        "ai": {"latest": None},

        # ✅ NEW: optional UI badges (set by gemini worker)
        "lastRiskColor": None,
        "lastFpsProfile": None,
    }

    db.reference(root).set(case_obj)
    _timeline_push(req.bookingId, "CASE_CREATED", {"mode": req.mode, "coverage": req.coverage})

    return {"status": "ok", "case": case_obj}


@router.get("/{bookingId}")
def get_case(bookingId: str):
    case = _get_case_or_404(bookingId)
    return {"status": "ok", "case": case}


@router.post("/{bookingId}/state")
def set_state(bookingId: str, req: StateChangeReq):
    _get_case_or_404(bookingId)
    init_firebase()
    now = _now_iso()

    db.reference(_case_root(bookingId)).update({"state": req.state, "updatedAt": now})
    _timeline_push(bookingId, "STATE_CHANGED", {"state": req.state})

    return {"status": "ok", "bookingId": bookingId, "state": req.state}


@router.post("/{bookingId}/emergency")
def trigger_emergency(bookingId: str, req: EmergencyReq):
    _get_case_or_404(bookingId)
    init_firebase()
    now = _now_iso()

    db.reference(_case_root(bookingId)).update(
        {
            "state": "EMERGENCY",
            "updatedAt": now,
            "emergency/active": True,
            "emergency/reason": req.reason,
            "emergency/triggeredAt": now,
        }
    )
    _timeline_push(bookingId, "EMERGENCY_TRIGGERED", {"reason": req.reason})

    return {"status": "ok", "bookingId": bookingId, "state": "EMERGENCY"}


@router.post("/{bookingId}/activate-subcenter")
def activate_subcenter(bookingId: str, req: ActivateSubcenterReq):
    _get_case_or_404(bookingId)
    init_firebase()
    now = _now_iso()

    update_obj: Dict[str, Any] = {
        "updatedAt": now,
        "subcenter/activated": True,
        "subcenter/subcenter_id": req.subcenter_id,
        "subcenter/activatedAt": now,
        "subcenter/note": req.note,
    }

    # ✅ optional metadata if caller provides it (gemini usually does)
    if req.areaLabel is not None:
        update_obj["subcenter/areaLabel"] = req.areaLabel
    if req.nearbyAddress is not None:
        update_obj["subcenter/nearbyAddress"] = req.nearbyAddress
    if req.microTrailEnd is not None:
        update_obj["subcenter/microTrailEnd"] = req.microTrailEnd
    if req.brief is not None:
        update_obj["subcenter/brief"] = req.brief

    db.reference(_case_root(bookingId)).update(update_obj)
    _timeline_push(bookingId, "SUBCENTER_ACTIVATED", {"subcenter_id": req.subcenter_id})

    return {"status": "ok", "bookingId": bookingId, "subcenter_id": req.subcenter_id}


@router.post("/{bookingId}/personnel/enroute")
def personnel_enroute(bookingId: str):
    _get_case_or_404(bookingId)
    init_firebase()
    now = _now_iso()

    db.reference(_case_root(bookingId)).update(
        {
            "updatedAt": now,
            "personnel/status": "ENROUTE",
            "personnel/enrouteAt": now,
        }
    )
    _timeline_push(bookingId, "PERSONNEL_ENROUTE")

    return {"status": "ok", "bookingId": bookingId, "personnel_status": "ENROUTE"}


@router.post("/{bookingId}/personnel/arrived")
def personnel_arrived(bookingId: str):
    _get_case_or_404(bookingId)
    init_firebase()
    now = _now_iso()

    db.reference(_case_root(bookingId)).update(
        {
            "updatedAt": now,
            "personnel/status": "ARRIVED",
            "personnel/arrivedAt": now,
        }
    )
    _timeline_push(bookingId, "PERSONNEL_ARRIVED")

    return {"status": "ok", "bookingId": bookingId, "personnel_status": "ARRIVED"}


@router.post("/{bookingId}/resolve")
def resolve_case(bookingId: str):
    _get_case_or_404(bookingId)
    init_firebase()
    now = _now_iso()

    db.reference(_case_root(bookingId)).update(
        {
            "updatedAt": now,
            "state": "RESOLVED",
            "personnel/status": "RESOLVED",
            "personnel/resolvedAt": now,
        }
    )
    _timeline_push(bookingId, "CASE_RESOLVED")

    return {"status": "ok", "bookingId": bookingId, "state": "RESOLVED"}

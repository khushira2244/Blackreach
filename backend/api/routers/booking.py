from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone

from firebase_admin import db
from integrations.firebase_admin import init_firebase

router = APIRouter(prefix="/booking", tags=["booking"])

SecurityTier = Literal["MONITORING", "RETIRED", "COMBAT"]
CompanionMode = Literal["NORMAL_SLICE", "COMPANION_PLUS"]
Coverage = Literal["SLICE", "FULL"]


class BookingConfirmReq(BaseModel):
    # From /journey/plan
    origin: Dict[str, float]
    destination: Dict[str, float]
    polyline: str = Field(..., min_length=10)
    distance_m: int = Field(..., ge=1)
    duration_s: int = Field(..., ge=1)

    # Slider selection
    areas: List[Dict[str, Any]]  # [{index, name}, ...]
    start_index: int = Field(..., ge=0)
    end_index: int = Field(..., ge=0)

    # From /journey/price
    covered_km: float = Field(..., ge=0.0)
    estimatedPriceINR: int = Field(..., ge=0)
    securityTier: SecurityTier = "MONITORING"

    # Existing: user chooses companion mode at booking time
    companionMode: CompanionMode = "NORMAL_SLICE"

    # ✅ NEW: coverage switch (slider coverage vs whole journey security)
    coverage: Coverage = "SLICE"

    notes: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ✅ FIX 1: ensure firebase is initialized here too
def _timeline_push(booking_id: str, event: str, extra: Optional[Dict[str, Any]] = None) -> None:
    init_firebase()
    payload: Dict[str, Any] = {"at": _now_iso(), "event": event}
    if extra:
        payload["extra"] = extra
    db.reference(f"/cases/{booking_id}/timeline").push(payload)


# ✅ UPDATED: allow chat init with starting mode (LOCKED for SLICE, AI_ACTIVE for FULL)
def _ensure_chat_initialized(
    booking_id: str, starting_mode: Literal["LOCKED", "AI_ACTIVE", "HUMAN_ACTIVE"] = "LOCKED"
) -> None:
    chat_root = f"/chats/{booking_id}"
    if db.reference(chat_root).get():
        return

    now = _now_iso()
    db.reference(chat_root).set({"bookingId": booking_id, "createdAt": now, "updatedAt": now, "mode": starting_mode})

    if starting_mode == "LOCKED":
        text = "🔒 Chat is locked. It will unlock when you enter the security zone or if Companion flags a RED risk."
    elif starting_mode == "AI_ACTIVE":
        text = "✅ Full security enabled — AI companion is active for this journey."
    else:
        text = "🧑‍💼 Human operator connected."

    db.reference(f"{chat_root}/messages").push(
        {
            "bookingId": booking_id,
            "at": now,
            "sender": "system",
            "text": text,
        }
    )


def get_decision_head(tier: SecurityTier) -> dict:
    if tier == "COMBAT":
        return {
            "name": "Anita Rao",
            "role": "Combat Response Lead",
            "experienceYears": 11,
            "specialty": ["Rapid dispatch", "High-risk escort", "Crowd control"],
            "guarantee": "Priority dispatch + fastest response window",
        }
    if tier == "RETIRED":
        return {
            "name": "Meera Nair",
            "role": "Retired Safety Captain",
            "experienceYears": 18,
            "specialty": ["De-escalation", "Safe routing", "Family coordination"],
            "guarantee": "Confirmed watch + guided assistance",
        }
    return {
        "name": "Kavya Singh",
        "role": "Monitoring Supervisor",
        "experienceYears": 7,
        "specialty": ["Live monitoring", "AI-assisted check-ins", "Escalation handling"],
        "guarantee": "Continuous monitoring + guided check-ins",
    }


@router.post("/confirm")
def confirm_booking(req: BookingConfirmReq):
    init_firebase()

    # ✅ FIX 2: don’t mutate req.* fields; use locals
    start_index = req.start_index
    end_index = req.end_index

    # ✅ Validation: only enforce slider indices when coverage is SLICE
    if req.coverage == "SLICE":
        if start_index >= end_index:
            raise HTTPException(status_code=400, detail="end_index must be greater than start_index")
        if start_index >= len(req.areas):
            raise HTTPException(status_code=400, detail="start_index must be < len(areas)")
        if end_index >= len(req.areas):
            raise HTTPException(status_code=400, detail="end_index must be < len(areas)")
    else:
        # FULL coverage: normalize selection to whole journey (keeps downstream code simple)
        if len(req.areas) == 0:
            raise HTTPException(status_code=400, detail="areas must not be empty")
        start_index = 0
        end_index = len(req.areas) - 1

    booking_id = str(uuid4())
    now = _now_iso()

    selected_areas = req.areas[start_index : end_index + 1]
    decision_head = get_decision_head(req.securityTier)

    # 1) Save booking (optional, but helpful)
    booking_obj = {
        "bookingId": booking_id,
        "status": "CONFIRMED",
        "createdAt": now,
        "securityTier": req.securityTier,
        "companionMode": req.companionMode,
        "coverage": req.coverage,  # ✅ NEW
        "journey": {
            "origin": req.origin,
            "destination": req.destination,
            "distance_m": req.distance_m,
            "duration_s": req.duration_s,
            "polyline": req.polyline,
        },
        "selection": {
            "areas": req.areas,
            "start_index": start_index,
            "end_index": end_index,
            "selectedAreas": selected_areas,
            "covered_km": req.covered_km,
        },
        "pricing": {"estimatedPriceINR": req.estimatedPriceINR},
        "decisionHead": decision_head,
        "notes": req.notes,
    }
    db.reference(f"/bookings/{booking_id}").set(booking_obj)

    # 2) Create case brain
    case_obj = {
        "bookingId": booking_id,
        "createdAt": now,
        "updatedAt": now,
        "state": "ACTIVE",
        "mode": "TRACKING",
        "securityTier": req.securityTier,
        "companionMode": req.companionMode,
        "coverage": req.coverage,  # ✅ NEW (Gemini reads this)
        "journey": booking_obj["journey"],
        "selected": {
            "areas": [a.get("name", "Area") for a in req.areas],
            "start_index": start_index,
            "end_index": end_index,
        },
        "emergency": {"active": False},

        # ✅ FIX 3: match schema used by case.py + gemini flows
        "subcenter": {
            "activated": False,
            "subcenter_id": None,
            "activatedAt": None,
            "note": None,
        },
        "personnel": {"status": "PENDING"},
        "user_note": req.notes,

        # ✅ stable defaults so frontend/gemini don't null-guess
        "lookahead": {"latest": None},
        "ai": {"latest": None},
    }
    db.reference(f"/cases/{booking_id}").set(case_obj)
    _timeline_push(booking_id, "CASE_CREATED", {"source": "booking_confirm"})

    # ✅ If FULL coverage: mark it explicitly in timeline
    if req.coverage == "FULL":
        _timeline_push(booking_id, "FULL_SECURITY_ENABLED", {"coverage": "FULL"})

    # 3) Initialize chat:
    #    - FULL: AI_ACTIVE immediately
    #    - SLICE: LOCKED (existing behavior)
    starting_mode = "AI_ACTIVE" if req.coverage == "FULL" else "LOCKED"
    _ensure_chat_initialized(booking_id, starting_mode=starting_mode)

    return {
        "bookingId": booking_id,
        "status": "CONFIRMED",
        "createdAt": now,
        "securityTier": req.securityTier,
        "companionMode": req.companionMode,
        "coverage": req.coverage,  # ✅ NEW
        "guarantee": decision_head["guarantee"],
        "journey": booking_obj["journey"],
        "selection": booking_obj["selection"],
        "pricing": booking_obj["pricing"],
        "decisionHead": decision_head,
        "next": {"tracking": "NOT_STARTED", "centerBrief": "PENDING"},
        "savedToFirebase": True,
        "notes": req.notes,
    }

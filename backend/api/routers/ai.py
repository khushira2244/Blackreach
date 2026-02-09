from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from integrations.firebase_admin import init_firebase
from firebase_admin import db

router = APIRouter(prefix="/ai", tags=["ai"])

Checkpoint = Literal["INITIAL", "ZONE_ENTRY", "EMERGENCY", "FINAL"]


class AIBriefReq(BaseModel):
    checkpoint: Checkpoint
    text: str = Field(..., min_length=5)
    riskColor: Optional[Literal["BLUE", "YELLOW", "RED"]] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/brief/{bookingId}")
def write_ai_brief(bookingId: str, req: AIBriefReq):
    """
    Stores AI reasoning output into the case record.
    Later this will be replaced by Gemini output.
    """
    init_firebase()
    root = f"/cases/{bookingId}"

    case = db.reference(root).get()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    now = _now_iso()

    payload = {
        "checkpoint": req.checkpoint,
        "text": req.text,
        "riskColor": req.riskColor,
        "at": now,
    }

    # Write brief
    db.reference(f"{root}/ai_briefs/{req.checkpoint}").set(payload)

    # Optional: also append to timeline for visibility
    db.reference(f"{root}/timeline").push(
        {
            "at": now,
            "event": "AI_BRIEF_WRITTEN",
            "extra": {
                "checkpoint": req.checkpoint,
                "riskColor": req.riskColor,
            },
        }
    )

    return {
        "status": "ok",
        "bookingId": bookingId,
        "checkpoint": req.checkpoint,
    }

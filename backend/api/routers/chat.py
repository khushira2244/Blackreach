from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from firebase_admin import db
from integrations.firebase_admin import init_firebase

router = APIRouter(prefix="/chat", tags=["chat"])

ChatMode = Literal["LOCKED", "AI_ACTIVE", "HUMAN_ACTIVE"]
Sender = Literal["user", "ai", "human", "system"]


class ChatMessageReq(BaseModel):
    sender: Sender
    text: str = Field(..., min_length=1, max_length=500)
    riskColor: Optional[Literal["BLUE", "YELLOW", "RED"]] = None


class HumanTakeoverReq(BaseModel):
    note: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chat_root(booking_id: str) -> str:
    return f"/chats/{booking_id}"


def _case_root(booking_id: str) -> str:
    return f"/cases/{booking_id}"


def _push_timeline(booking_id: str, event: str, extra: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {"at": _now_iso(), "event": event}
    if extra:
        payload["extra"] = extra
    db.reference(f"/cases/{booking_id}/timeline").push(payload)


def _push_system_message(booking_id: str, text: str) -> None:
    now = _now_iso()
    db.reference(f"{_chat_root(booking_id)}/messages").push(
        {
            "bookingId": booking_id,
            "at": now,
            "sender": "system",
            "text": text,
        }
    )
    db.reference(_chat_root(booking_id)).update({"updatedAt": now})


# ✅ UPDATED: allow initializing chat in LOCKED or AI_ACTIVE (or HUMAN_ACTIVE if needed)
def _ensure_chat_initialized(booking_id: str, starting_mode: ChatMode = "LOCKED") -> None:
    chat_root = _chat_root(booking_id)
    if db.reference(chat_root).get():
        return

    now = _now_iso()
    db.reference(chat_root).set(
        {"bookingId": booking_id, "createdAt": now, "updatedAt": now, "mode": starting_mode}
    )

    if starting_mode == "LOCKED":
        text = "🔒 Chat is locked. It unlocks in security zone or if Companion flags RED risk."
    elif starting_mode == "AI_ACTIVE":
        text = "✅ Full journey security enabled — AI companion is now active."
    else:
        text = "🧑‍💼 Human operator connected — you can message now."

    db.reference(f"{chat_root}/messages").push(
        {"bookingId": booking_id, "at": now, "sender": "system", "text": text}
    )


@router.post("/init/{bookingId}")
def init_chat(
    bookingId: str,
    # ✅ NEW: optional query param so you can test FULL in Swagger:
    # /chat/init/{id}?mode=AI_ACTIVE
    mode: ChatMode = Query("LOCKED"),
):
    init_firebase()
    _ensure_chat_initialized(bookingId, starting_mode=mode)
    _push_timeline(bookingId, "CHAT_INITIALIZED", {"mode": mode})
    return {"status": "ok", "bookingId": bookingId, "mode": mode}


@router.post("/{bookingId}/message")
def post_message(bookingId: str, req: ChatMessageReq):
    init_firebase()
    _ensure_chat_initialized(bookingId)

    mode = db.reference(f"{_chat_root(bookingId)}/mode").get() or "LOCKED"
    if mode == "LOCKED" and req.sender != "system":
        raise HTTPException(status_code=403, detail="Chat is LOCKED")

    now = _now_iso()
    msg: Dict[str, Any] = {
        "bookingId": bookingId,
        "at": now,
        "sender": req.sender,
        "text": req.text,
    }
    if req.riskColor:
        msg["riskColor"] = req.riskColor

    db.reference(f"{_chat_root(bookingId)}/messages").push(msg)
    db.reference(_chat_root(bookingId)).update({"updatedAt": now})

    return {"status": "ok", "bookingId": bookingId, "mode": mode}


@router.get("/{bookingId}")
def get_chat(bookingId: str, limit: int = 20):
    init_firebase()
    chat = db.reference(_chat_root(bookingId)).get()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    ref = (
        db.reference(f"{_chat_root(bookingId)}/messages")
        .order_by_key()
        .limit_to_last(max(1, min(limit, 50)))
    )
    msgs = ref.get() or {}
    out: List[Dict[str, Any]] = []
    for k in sorted(msgs.keys()):
        v = msgs[k]
        if isinstance(v, dict):
            out.append(v)

    return {
        "status": "ok",
        "chat": {"bookingId": bookingId, "mode": chat.get("mode", "LOCKED"), "messages": out},
    }


@router.post("/{bookingId}/unlock")
def unlock_chat(bookingId: str):
    init_firebase()
    _ensure_chat_initialized(bookingId)

    now = _now_iso()
    db.reference(_chat_root(bookingId)).update({"mode": "AI_ACTIVE", "updatedAt": now})
    _push_system_message(bookingId, "✅ Chat unlocked — AI companion is now active.")
    _push_timeline(bookingId, "CHAT_UNLOCKED", {"mode": "AI_ACTIVE"})
    return {"status": "ok", "bookingId": bookingId, "mode": "AI_ACTIVE"}


@router.post("/{bookingId}/human-takeover")
def human_takeover(bookingId: str, req: HumanTakeoverReq):
    init_firebase()
    _ensure_chat_initialized(bookingId)

    now = _now_iso()
    db.reference(_chat_root(bookingId)).update({"mode": "HUMAN_ACTIVE", "updatedAt": now})
    _push_system_message(bookingId, "🧑‍💼 Human operator connected — you can message now.")
    _push_timeline(bookingId, "HUMAN_TAKEOVER", {"note": req.note})
    return {"status": "ok", "bookingId": bookingId, "mode": "HUMAN_ACTIVE"}


@router.post("/{bookingId}/sync-with-case")
def sync_with_case(bookingId: str):
    """
    Glue endpoint:
    case.state IN_ZONE -> chat AI_ACTIVE
    case.state EMERGENCY -> chat HUMAN_ACTIVE
    """
    init_firebase()
    _ensure_chat_initialized(bookingId)

    case = db.reference(_case_root(bookingId)).get()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    state = case.get("state") or "ACTIVE"
    current_mode = db.reference(f"{_chat_root(bookingId)}/mode").get() or "LOCKED"

    target_mode: ChatMode = current_mode
    system_msg: Optional[str] = None

    if state == "IN_ZONE":
        target_mode = "AI_ACTIVE"
        system_msg = "✅ Entered security zone — AI companion activated."
    elif state == "EMERGENCY":
        target_mode = "HUMAN_ACTIVE"
        system_msg = "🧑‍💼 Emergency detected — human operator connected."

    if target_mode != current_mode:
        now = _now_iso()
        db.reference(_chat_root(bookingId)).update({"mode": target_mode, "updatedAt": now})

        if system_msg:
            _push_system_message(bookingId, system_msg)

        _push_timeline(bookingId, "CHAT_SYNCED_WITH_CASE", {"state": state, "mode": target_mode})

    return {"status": "ok", "bookingId": bookingId, "caseState": state, "chatMode": target_mode}

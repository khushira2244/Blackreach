# backend/api/routers/gemini.py

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from integrations.firebase_admin import init_firebase, db
from integrations.gemini_vertex import generate_vigilant_response
import json
import re


router = APIRouter(prefix="/gemini", tags=["gemini-worker"])

Checkpoint = Literal["INITIAL", "ZONE_ENTRY", "EMERGENCY_CHECK", "FINAL", "TRACK_TICK"]
UserSignal = Optional[Literal["OK", "UNEASY", "EMERGENCY"]]

RiskColor = Literal["GREEN", "ORANGE", "RED"]
FpsProfile = Literal["LOW", "MEDIUM", "HIGH"]
SubcenterAdvice = Literal["ACTIVATE", "NONE"]

Action = Literal[
    "NONE",
    "UNLOCK_CHAT",
    "HUMAN_TAKEOVER",
    "TRIGGER_EMERGENCY",
    "SET_IN_ZONE",
    "ACTIVATE_SUBCENTER",
]


# -----------------------------
# Request / Response Models
# -----------------------------
class GeminiRunReq(BaseModel):
    checkpoint: Checkpoint = "INITIAL"
    userSignal: UserSignal = None
    note: Optional[str] = None
    max_recent_messages: int = Field(10, ge=0, le=50)


# -----------------------------
# Helpers
# -----------------------------



def _extract_json(text: str) -> dict:
    if not text:
        return {}
    # try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # try find first {...} block
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_root(booking_id: str) -> str:
    return f"/cases/{booking_id}"


def _live_root(booking_id: str) -> str:
    return f"/live/{booking_id}"


def _chat_root(booking_id: str) -> str:
    return f"/chats/{booking_id}"


def _push_timeline(booking_id: str, event: str, extra: Optional[Dict[str, Any]] = None) -> None:
    init_firebase()
    payload: Dict[str, Any] = {"at": _now_iso(), "event": event}
    if extra:
        payload["extra"] = extra
    db.reference(f"/cases/{booking_id}/timeline").push(payload)


def _get_case_or_404(booking_id: str) -> Dict[str, Any]:
    init_firebase()
    case = db.reference(_case_root(booking_id)).get()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found for this bookingId")
    return case


def _get_live_latest(booking_id: str) -> Optional[Dict[str, Any]]:
    init_firebase()
    return db.reference(f"{_live_root(booking_id)}/latest").get()


def _get_live_history(booking_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    init_firebase()
    ref = db.reference(f"{_live_root(booking_id)}/history").order_by_key().limit_to_last(max(1, min(limit, 50)))
    items = ref.get() or {}
    out: List[Dict[str, Any]] = []
    for k in sorted(items.keys()):
        v = items[k]
        if isinstance(v, dict):
            out.append(v)
    return out


def _get_chat_mode(booking_id: str) -> str:
    init_firebase()
    return db.reference(f"{_chat_root(booking_id)}/mode").get() or "LOCKED"


def _get_recent_messages(booking_id: str, limit: int) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    init_firebase()
    ref = db.reference(f"{_chat_root(booking_id)}/messages").order_by_key().limit_to_last(limit)
    msgs = ref.get() or {}
    out: List[Dict[str, Any]] = []
    for k in sorted(msgs.keys()):
        v = msgs[k]
        if isinstance(v, dict):
            out.append(v)
    return out


def _push_ai_message(booking_id: str, text: str, riskColor: Optional[RiskColor] = None) -> None:
    init_firebase()
    now = _now_iso()
    msg: Dict[str, Any] = {"bookingId": booking_id, "at": now, "sender": "ai", "text": text}
    if riskColor:
        msg["riskColor"] = riskColor
    db.reference(f"{_chat_root(booking_id)}/messages").push(msg)
    db.reference(_chat_root(booking_id)).update({"updatedAt": now})


def _push_system_message(booking_id: str, text: str) -> None:
    init_firebase()
    now = _now_iso()
    db.reference(f"{_chat_root(booking_id)}/messages").push(
        {"bookingId": booking_id, "at": now, "sender": "system", "text": text}
    )
    db.reference(_chat_root(booking_id)).update({"updatedAt": now})


def _write_ai_brief(booking_id: str, checkpoint: str, brief: str, riskColor: RiskColor) -> None:
    init_firebase()
    now = _now_iso()
    payload = {"at": now, "checkpoint": checkpoint, "riskColor": riskColor, "brief": brief}
    db.reference(f"{_case_root(booking_id)}/ai_briefs/{checkpoint}").set(payload)
    db.reference(_case_root(booking_id)).update({"updatedAt": now})


def _set_chat_mode(booking_id: str, mode: str) -> None:
    init_firebase()
    now = _now_iso()
    db.reference(_chat_root(booking_id)).update({"mode": mode, "updatedAt": now})


def _set_case_state(booking_id: str, state: str) -> None:
    init_firebase()
    now = _now_iso()
    db.reference(_case_root(booking_id)).update({"state": state, "updatedAt": now})


def _trigger_emergency(booking_id: str, reason: str) -> None:
    init_firebase()
    now = _now_iso()
    db.reference(_case_root(booking_id)).update(
        {
            "state": "EMERGENCY",
            "updatedAt": now,
            "emergency/active": True,
            "emergency/reason": reason,
            "emergency/triggeredAt": now,
        }
    )


# ✅ read latest lookahead result from Firebase
def _get_lookahead_latest(booking_id: str) -> Optional[Dict[str, Any]]:
    init_firebase()
    return db.reference(f"{_case_root(booking_id)}/lookahead/latest").get()


def _build_subcenter_brief_from_lookahead(
    lookahead_latest: Optional[Dict[str, Any]],
    riskColor: RiskColor,
    reasons: List[str],
) -> Dict[str, Any]:
    """
    IMPORTANT: Gemini must NOT invent coords.
    This brief is built only from the stored lookahead snapshot.
    """
    lh = lookahead_latest or {}

    location_hint = lh.get("locationHint") or {}
    micro = lh.get("microTrail100m") or {}

    area_label = location_hint.get("areaLabel") or "—"
    nearby = location_hint.get("nearbyAddress")  # may be None
    micro_end = micro.get("end")  # {lat,lng} or None

    if micro_end is None:
        micro_end = lh.get("end_point") or lh.get("segmentEnd") or (lh.get("segment") or {}).get("segment_end")

    return {
        "areaLabel": area_label,
        "nearbyAddress": nearby,
        "microTrail100m": {
            "distance_m": micro.get("distance_m", 100),
            "end": micro_end,
            "points": micro.get("points", []),
        },
        "riskColor": riskColor,
        "reasons": (reasons or [])[:6],
        "source": "lookahead_latest",
    }


def _activate_subcenter_if_needed(
    booking_id: str,
    reason: str,
    lookahead_latest: Optional[Dict[str, Any]] = None,
    riskColor: Optional[RiskColor] = None,
    reasons: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Activates a subcenter if not already activated.
    Always re-reads case from Firebase to avoid double activation.
    Returns subcenter_id if activated, else None.
    """
    init_firebase()
    latest_case = db.reference(_case_root(booking_id)).get() or {}
    subcenter = latest_case.get("subcenter") or {}

    if subcenter.get("activated"):
        return None

    now = _now_iso()
    subcenter_id = "SC-01"

    update_payload: Dict[str, Any] = {
        "updatedAt": now,
        "subcenter/activated": True,
        "subcenter/subcenter_id": subcenter_id,
        "subcenter/activatedAt": now,
        "subcenter/note": f"Activated by Gemini: {reason}",
    }

    # ✅ attach operator brief sourced from lookahead snapshot (no AI coords)
    if riskColor and reasons is not None:
        brief_obj = _build_subcenter_brief_from_lookahead(lookahead_latest, riskColor, reasons)
        update_payload["subcenter/areaLabel"] = brief_obj.get("areaLabel")
        update_payload["subcenter/nearbyAddress"] = brief_obj.get("nearbyAddress")
        update_payload["subcenter/microTrailEnd"] = (brief_obj.get("microTrail100m") or {}).get("end")
        update_payload["subcenter/brief"] = brief_obj

    db.reference(_case_root(booking_id)).update(update_payload)

    _push_timeline(
        booking_id,
        "SUBCENTER_ACTIVATED_BY_GEMINI",
        {"subcenter_id": subcenter_id, "reason": reason},
    )

    return subcenter_id


# -----------------------------
# ✅ NEW: Gemini input echo (deploy-safe)
# -----------------------------
def _safe_gemini_input_echo(prompt_name: str, compact_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return ONLY a summarized Gemini input for Swagger/judges.
    Never return full chat logs, full OSM dumps, or huge geometry arrays.
    """
    booking_id = compact_context.get("bookingId")
    checkpoint = compact_context.get("checkpoint")

    live = compact_context.get("liveLatest") or {}
    snapped = (live.get("snapped") if isinstance(live, dict) else None) or {}

    lookahead = compact_context.get("lookahead") or {}
    location_hint = (lookahead.get("locationHint") if isinstance(lookahead, dict) else None) or {}
    micro = (lookahead.get("microTrail100m") if isinstance(lookahead, dict) else None) or {}

    micro_end = micro.get("end") if isinstance(micro, dict) else None
    micro_points = micro.get("points") if isinstance(micro, dict) else None
    micro_points_count = len(micro_points) if isinstance(micro_points, list) else 0

    places_present = bool(lookahead.get("places_summary"))
    osm_present = bool(lookahead.get("osm_summary"))

    return {
        "promptName": prompt_name,
        "checkpoint": checkpoint,
        "bookingId": booking_id,
        "contextSummary": {
            "liveSnapped": (
                {"lat": snapped.get("lat"), "lng": snapped.get("lng")}
                if isinstance(snapped, dict) and ("lat" in snapped and "lng" in snapped)
                else None
            ),
            "lookahead": {
                "distance_m": lookahead.get("distance_m", 500),
                "areaLabel": location_hint.get("areaLabel"),
                "nearbyAddress": location_hint.get("nearbyAddress"),
                "microTrailEnd": micro_end,
                "microTrailPointsCount": micro_points_count,
                "placesSummaryPresent": places_present,
                "osmSummaryPresent": osm_present,
            },
        },
    }


# -----------------------------
# Vertex decision helper (REAL)
# -----------------------------
def _vertex_decide(
    context: Dict[str, Any],
    checkpoint: Checkpoint,
    userSignal: UserSignal,
    note: Optional[str],
) -> Dict[str, Any]:
    """
    Calls Vertex Gemini via integrations.gemini_vertex.generate_vigilant_response(compact_context)
    """
    case = context.get("case") or {}
    lookahead = context.get("lookaheadLatest") or {}

    compact_lookahead: Dict[str, Any] = {
        "at": lookahead.get("at"),
        "distance_m": lookahead.get("distance_m", 500),
        "segmentEnd": (lookahead.get("segment") or {}).get("segment_end") or lookahead.get("segmentEnd"),
        "samplePoints": lookahead.get("samplePoints") or lookahead.get("samples"),
        "places_summary": lookahead.get("places_summary"),
        "osm_summary": lookahead.get("osm_summary"),
        "microTrail100m": lookahead.get("microTrail100m"),
        "locationHint": lookahead.get("locationHint"),
    }

    compact_context: Dict[str, Any] = {
        "bookingId": context.get("bookingId"),
        "checkpoint": checkpoint,
        "userSignal": userSignal,
        "note": note,
        "case": {
            "state": case.get("state"),
            "mode": case.get("mode"),
            "coverage": case.get("coverage"),
            "selected": case.get("selected"),
            "emergency": case.get("emergency"),
            "subcenter": case.get("subcenter"),
            "personnel": case.get("personnel"),
        },
        "liveLatest": context.get("liveLatest"),
        "liveHistory": context.get("liveHistory") or [],
        "chatMode": context.get("chatMode"),
        "recentMessages": (context.get("recentMessages") or [])[-10:],
        "lookahead": compact_lookahead,
    }

    # ✅ prompt name label for debugging / demo transparency
    prompt_name = "vigilant_v1"

    out = generate_vigilant_response(compact_context) or {}

    risk = out.get("riskColor") or "GREEN"
    fps = out.get("fpsProfile") or "LOW"
    subcenter_advice = out.get("subcenterAdvice") or "NONE"
    reasons = out.get("reasons") or []

    brief = out.get("brief") or ""
    action = out.get("action") or "NONE"
    msgs = out.get("chatMessages") or out.get("messages") or []

    if not isinstance(brief, str):
        brief = str(brief)
    brief = brief.strip()[:500]

    if risk in ("BLUE", "YELLOW", "RED"):
        risk = {"BLUE": "GREEN", "YELLOW": "ORANGE", "RED": "RED"}[risk]

    if risk not in ("GREEN", "ORANGE", "RED"):
        risk = "GREEN"
    if fps not in ("LOW", "MEDIUM", "HIGH"):
        fps = "LOW"
    if subcenter_advice not in ("ACTIVATE", "NONE"):
        subcenter_advice = "NONE"
    if action not in (
        "NONE",
        "UNLOCK_CHAT",
        "HUMAN_TAKEOVER",
        "TRIGGER_EMERGENCY",
        "SET_IN_ZONE",
        "ACTIVATE_SUBCENTER",
    ):
        action = "NONE"
    if not isinstance(msgs, list):
        msgs = []
    if not isinstance(reasons, list):
        reasons = []

    clean_msgs: List[str] = []
    for m in msgs:
        if isinstance(m, str) and m.strip():
            clean_msgs.append(m.strip())

    clean_reasons: List[str] = []
    for r in reasons:
        try:
            s = str(r).strip()
        except Exception:
            s = ""
        if s:
            clean_reasons.append(s[:120])
    clean_reasons = clean_reasons[:6]

    # ✅ NEW: summarized echo of what we sent to Gemini (safe)
    gemini_input_echo = _safe_gemini_input_echo(prompt_name, compact_context)

    return {
        "riskColor": risk,
        "brief": brief,
        "action": action,
        "chatMessages": clean_msgs,
        "fpsProfile": fps,
        "subcenterAdvice": subcenter_advice,
        "reasons": clean_reasons,
        "geminiInput": gemini_input_echo,  # ✅ NEW
    }


# -----------------------------
# MOCK Gemini Worker (rules)
# -----------------------------
def _mock_gemini_worker(context: Dict[str, Any], checkpoint: Checkpoint, userSignal: UserSignal) -> Dict[str, Any]:
    case = context.get("case") or {}
    chat_mode = context.get("chatMode") or "LOCKED"
    coverage = case.get("coverage") or "SLICE"
    subcenter = (case.get("subcenter") or {})
    already_active = bool(subcenter.get("activated"))

    risk: RiskColor = "GREEN"
    fps: FpsProfile = "LOW"
    subcenter_advice: SubcenterAdvice = "NONE"
    reasons: List[str] = []

    action: Action = "NONE"
    brief = "Monitoring initialized."
    chat_messages: List[str] = []

    if checkpoint == "INITIAL":
        risk = "GREEN"
        fps = "LOW"
        brief = "Journey received. Monitoring plan loaded."
        if coverage == "FULL":
            chat_messages = ["✅ Full security enabled. I’m monitoring your journey end-to-end."]
        else:
            chat_messages = ["✅ Monitoring started. I’ll stay with you during your selected security window."]
        action = "NONE"

    elif checkpoint == "ZONE_ENTRY":
        risk = "ORANGE"
        fps = "MEDIUM"
        brief = "Zone entry detected. Starting check-ins."
        if chat_mode == "LOCKED":
            action = "UNLOCK_CHAT"

        chat_messages = [
            "You are entering the monitored zone. Choose one option:",
            "✅ I’m okay",
            "⚠️ I feel uneasy",
            "🚨 Emergency",
        ]

    elif checkpoint == "TRACK_TICK":
        risk = "ORANGE"
        fps = "MEDIUM"
        brief = "Tracking signal evaluation in progress."
        action = "NONE"

        if coverage == "FULL" and not already_active:
            subcenter_advice = "ACTIVATE"
            reasons = ["mock_tracking_anomaly"]
            brief = "Anomalous movement signal detected. Advising subcenter activation for precautionary monitoring."

    elif checkpoint == "EMERGENCY_CHECK":
        if userSignal == "OK":
            risk = "GREEN"
            fps = "LOW"
            brief = "User confirmed OK. Continue monitoring."
            chat_messages = ["Got it. Stay on your route. I’m here if anything changes."]
            action = "NONE"

        elif userSignal == "UNEASY":
            risk = "ORANGE"
            fps = "MEDIUM"
            brief = "User feels uneasy. Starting safety questions."
            chat_messages = [
                "I’m here. Quick check:",
                "1) Are you alone right now?",
                "2) Do you see a lit shop/cafe nearby?",
                "3) Can you move towards a busier road for 1–2 minutes?",
                "If you want, press 🚨 Emergency anytime.",
            ]
            action = "NONE"

        elif userSignal == "EMERGENCY":
            risk = "RED"
            fps = "HIGH"
            subcenter_advice = "ACTIVATE"
            reasons = ["user_emergency_signal"]
            brief = "Emergency signal received. Escalating to human operator + subcenter."
            chat_messages = [
                "🚨 Emergency escalation initiated.",
                "A human operator is joining now. Stay on the line if possible.",
            ]
            action = "TRIGGER_EMERGENCY"
        else:
            risk = "ORANGE"
            fps = "MEDIUM"
            brief = "Emergency check requested. Awaiting user confirmation."
            chat_messages = ["Are you safe right now? Reply with ✅ OK or 🚨 Emergency."]
            action = "NONE"

    elif checkpoint == "FINAL":
        risk = "GREEN"
        fps = "LOW"
        brief = "Journey closed. Summary saved."
        chat_messages = ["✅ Case closed. If you need anything else, I’m here."]
        action = "NONE"

    # ✅ NEW: also echo a safe “geminiInput” for mock (same structure)
    prompt_name = "mock_v1"
    compact_context_for_echo = {
        "bookingId": context.get("bookingId"),
        "checkpoint": checkpoint,
        "liveLatest": context.get("liveLatest"),
        "lookahead": {
            "distance_m": (context.get("lookaheadLatest") or {}).get("distance_m", 500),
            "locationHint": (context.get("lookaheadLatest") or {}).get("locationHint"),
            "microTrail100m": (context.get("lookaheadLatest") or {}).get("microTrail100m"),
            "places_summary": (context.get("lookaheadLatest") or {}).get("places_summary"),
            "osm_summary": (context.get("lookaheadLatest") or {}).get("osm_summary"),
        },
    }

    return {
        "riskColor": risk,
        "brief": brief,
        "chatMessages": chat_messages,
        "action": action,
        "fpsProfile": fps,
        "subcenterAdvice": subcenter_advice,
        "reasons": reasons,
        "geminiInput": _safe_gemini_input_echo(prompt_name, compact_context_for_echo),  # ✅ NEW
        "suggestedCaseState": ("IN_ZONE" if checkpoint == "ZONE_ENTRY" else None),
    }


# -----------------------------
# Endpoint
# -----------------------------
@router.post("/run/{bookingId}")
def run_gemini_worker(bookingId: str, req: GeminiRunReq):
    """
    Gemini worker runner.
    Reads case + live + chat mode (+ recent messages + lookahead),
    decides,
    writes ai_briefs + ai messages,
    optionally escalates (unlock chat / emergency / human takeover / subcenter activation).
    """
    case = _get_case_or_404(bookingId)
    live_latest = _get_live_latest(bookingId)
    live_history = _get_live_history(bookingId, limit=20)
    chat_mode = _get_chat_mode(bookingId)
    recent_msgs = _get_recent_messages(bookingId, req.max_recent_messages)

    lookahead_latest = _get_lookahead_latest(bookingId)

    context = {
        "bookingId": bookingId,
        "case": case,
        "liveLatest": live_latest,
        "liveHistory": live_history,
        "chatMode": chat_mode,
        "recentMessages": recent_msgs,
        "lookaheadLatest": lookahead_latest,
    }

    try:
        result = _vertex_decide(context, req.checkpoint, req.userSignal, req.note)
        _push_timeline(bookingId, "VERTEX_GEMINI_USED", {"checkpoint": req.checkpoint})
    except Exception as e:
        result = _mock_gemini_worker(context, req.checkpoint, req.userSignal)
        _push_timeline(
            bookingId,
            "VERTEX_GEMINI_FALLBACK_TO_MOCK",
            {"error": str(e)[:180], "checkpoint": req.checkpoint},
        )

    riskColor: RiskColor = result.get("riskColor", "GREEN")
    brief: str = result.get("brief", "")
    messages: List[str] = result.get("chatMessages") or []
    action: Action = result.get("action", "NONE")

    fpsProfile: FpsProfile = result.get("fpsProfile", "LOW")
    subcenterAdvice: SubcenterAdvice = result.get("subcenterAdvice", "NONE")
    reasons: List[str] = result.get("reasons") or []

    # ✅ NEW: echo what we sent to Gemini (safe summary)
    gemini_input = result.get("geminiInput")

    _write_ai_brief(bookingId, req.checkpoint, brief, riskColor)
    _push_timeline(bookingId, "GEMINI_BRIEF_WRITTEN", {"checkpoint": req.checkpoint, "riskColor": riskColor})

    init_firebase()
    now = _now_iso()
    db.reference(f"{_case_root(bookingId)}/ai/latest").set(
        {
            "at": now,
            "checkpoint": req.checkpoint,
            "riskColor": riskColor,
            "fpsProfile": fpsProfile,
            "subcenterAdvice": subcenterAdvice,
            "reasons": reasons,
        }
    )

    db.reference(_case_root(bookingId)).update(
        {
            "updatedAt": now,
            "lastRiskColor": riskColor,
            "lastFpsProfile": fpsProfile,
        }
    )

    if req.checkpoint == "ZONE_ENTRY" and (case.get("state") != "IN_ZONE"):
        _set_case_state(bookingId, "IN_ZONE")
        _push_timeline(bookingId, "STATE_CHANGED_BY_GEMINI", {"state": "IN_ZONE"})

    if action == "SET_IN_ZONE" and (case.get("state") != "IN_ZONE"):
        _set_case_state(bookingId, "IN_ZONE")
        _push_timeline(bookingId, "STATE_CHANGED_BY_GEMINI", {"state": "IN_ZONE", "via": "action"})

    escalations: Dict[str, Any] = {"action": action}

    if action == "UNLOCK_CHAT":
        if chat_mode == "LOCKED":
            _set_chat_mode(bookingId, "AI_ACTIVE")
            _push_system_message(bookingId, "✅ Chat unlocked — AI companion is now active.")
            _push_timeline(bookingId, "CHAT_UNLOCKED_BY_GEMINI", {"mode": "AI_ACTIVE"})
            escalations["chatMode"] = "AI_ACTIVE"
        else:
            escalations["chatMode"] = chat_mode

    elif action == "TRIGGER_EMERGENCY":
        reason = "gemini_emergency_signal"
        if req.userSignal == "EMERGENCY":
            reason = "user_emergency_signal"

        _trigger_emergency(bookingId, reason=reason)
        _push_timeline(bookingId, "EMERGENCY_TRIGGERED_BY_GEMINI", {"reason": reason})

        subcenter_id = _activate_subcenter_if_needed(
            bookingId,
            reason="emergency_escalation",
            lookahead_latest=lookahead_latest,
            riskColor="RED",
            reasons=(reasons or ["emergency_escalation"]),
        )
        if subcenter_id:
            escalations["subcenter"] = subcenter_id

        _set_chat_mode(bookingId, "HUMAN_ACTIVE")
        _push_system_message(bookingId, "🧑‍💼 Human operator connected — you can message now.")
        _push_timeline(bookingId, "HUMAN_TAKEOVER_BY_GEMINI", {"mode": "HUMAN_ACTIVE"})
        escalations["caseState"] = "EMERGENCY"
        escalations["chatMode"] = "HUMAN_ACTIVE"

    elif action == "HUMAN_TAKEOVER":
        _set_chat_mode(bookingId, "HUMAN_ACTIVE")
        _push_system_message(bookingId, "🧑‍💼 Human operator connected — you can message now.")
        _push_timeline(bookingId, "HUMAN_TAKEOVER_BY_GEMINI", {"mode": "HUMAN_ACTIVE"})
        escalations["chatMode"] = "HUMAN_ACTIVE"

    elif action == "ACTIVATE_SUBCENTER":
        subcenter_id = _activate_subcenter_if_needed(
            bookingId,
            reason="tracking_signal",
            lookahead_latest=lookahead_latest,
            riskColor=riskColor,
            reasons=reasons,
        )
        if subcenter_id:
            escalations["subcenter"] = subcenter_id

    if subcenterAdvice == "ACTIVATE":
        reason_str = ("; ".join(reasons)[:120] or "gemini_advice")
        sub_id = _activate_subcenter_if_needed(
            bookingId,
            reason=f"lookahead_{riskColor.lower()}|{reason_str}",
            lookahead_latest=lookahead_latest,
            riskColor=riskColor,
            reasons=reasons,
        )
        if sub_id:
            escalations["subcenter"] = sub_id
            _push_system_message(bookingId, f"🏢 Subcenter activated ({sub_id}) due to {riskColor} risk.")
            brief_obj = _build_subcenter_brief_from_lookahead(lookahead_latest, riskColor, reasons)
            _push_timeline(bookingId, "SUBCENTER_OPERATOR_BRIEF", brief_obj)

    final_mode = (escalations.get("chatMode") or chat_mode)

    if final_mode in ("AI_ACTIVE", "HUMAN_ACTIVE"):
        for m in messages:
            _push_ai_message(bookingId, m, riskColor=riskColor)
        _push_timeline(bookingId, "GEMINI_MESSAGES_SENT", {"count": len(messages), "checkpoint": req.checkpoint})
        sent_count = len(messages)
    else:
        _push_timeline(
            bookingId,
            "GEMINI_MESSAGES_SKIPPED_LOCKED",
            {"count": len(messages), "checkpoint": req.checkpoint},
        )
        sent_count = 0

    return {
        "status": "ok",
        "bookingId": bookingId,
        "checkpoint": req.checkpoint,
        "riskColor": riskColor,
        "fpsProfile": fpsProfile,
        "subcenterAdvice": subcenterAdvice,
        "reasons": reasons,
        "brief": brief,
        "messages_sent": sent_count,
        "escalations": escalations,
        "live_latest_present": bool(live_latest),
        "lookahead_present": bool(lookahead_latest),
        # ✅ NEW: show judges exactly what evidence was fed to Gemini (safe summary)
        "geminiInput": gemini_input,
    }

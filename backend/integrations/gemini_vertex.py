import json
import os
from typing import Any, Dict, List, Literal, Optional

# Google Gen AI SDK (supports Vertex AI)
# pip install google-genai
from google import genai
from google.genai import types
from google.auth import credentials
from google.oauth2 import service_account


RiskColor = Literal["BLUE", "YELLOW", "RED"]
Action = Literal[
    "NONE",
    "UNLOCK_CHAT",
    "HUMAN_TAKEOVER",
    "TRIGGER_EMERGENCY",
    "SET_IN_ZONE",
]


# -----------------------------
# Env helper (unchanged)
# -----------------------------
def _get_env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if not val:
        raise RuntimeError(f"{name} is missing in environment")
    return val


# -----------------------------
# Fallback (unchanged)
# -----------------------------
def _fallback_response(context: Dict[str, Any]) -> Dict[str, Any]:
    checkpoint = (context.get("checkpoint") or "INITIAL").upper()
    user_signal = context.get("userSignal")

    if checkpoint == "ZONE_ENTRY":
        return {
            "riskColor": "YELLOW",
            "brief": "Zone entry detected. Unlocking AI companion chat and starting check-ins.",
            "chatMessages": [
                "You are entering the monitored zone. Choose one option:",
                "✅ I’m okay",
                "⚠️ I feel uneasy",
                "🚨 Emergency",
            ],
            "action": "UNLOCK_CHAT",
        }

    if checkpoint == "EMERGENCY_CHECK" and user_signal == "EMERGENCY":
        return {
            "riskColor": "RED",
            "brief": "Emergency signal received. Escalating to human operator.",
            "chatMessages": [
                "🚨 Emergency escalation initiated.",
                "A human operator is joining now. Stay on the line if possible.",
            ],
            "action": "TRIGGER_EMERGENCY",
        }

    return {
        "riskColor": "BLUE",
        "brief": "Monitoring active. No escalations required at this time.",
        "chatMessages": ["✅ Monitoring active. I’m here if anything changes."],
        "action": "NONE",
    }


# -----------------------------
# MAIN FUNCTION (SAFE CHANGE)
# -----------------------------
def generate_vigilant_response(context_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real Vertex AI Gemini call.

    Input: compact context json (built in router)
    Output (strict contract):
      {
        "riskColor": "BLUE|YELLOW|RED",
        "fpsProfile": "LOW|MEDIUM|HIGH",
        "subcenterAdvice": "ACTIVATE|NONE",
        "reasons": ["..."],
        "brief": "...",
        "chatMessages": ["..."],
        "action": "NONE|UNLOCK_CHAT|HUMAN_TAKEOVER|TRIGGER_EMERGENCY|SET_IN_ZONE|ACTIVATE_SUBCENTER"
      }
    """

    # ---- Vertex config ----
    project_id = _get_env("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")  # don't hard-crash if missing
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )

    # ---- Response schema (structured JSON) ----
    response_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "riskColor": {"type": "string", "enum": ["BLUE", "YELLOW", "RED"]},
            "fpsProfile": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
            "subcenterAdvice": {"type": "string", "enum": ["ACTIVATE", "NONE"]},
            "reasons": {"type": "array", "items": {"type": "string"}},

            "brief": {"type": "string"},
            "chatMessages": {"type": "array", "items": {"type": "string"}},
            "action": {
                "type": "string",
                "enum": [
                    "NONE",
                    "UNLOCK_CHAT",
                    "HUMAN_TAKEOVER",
                    "TRIGGER_EMERGENCY",
                    "SET_IN_ZONE",
                    "ACTIVATE_SUBCENTER",
                ],
            },
        },
        "required": ["riskColor", "fpsProfile", "subcenterAdvice", "reasons", "brief", "chatMessages", "action"],
        "additionalProperties": False,
    }

    # ---- System instruction ----
    system_instruction = """
You are Blackreach Vigilant Companion (backend worker).
You MUST output only valid JSON matching the provided schema.

You do NOT predict crime. You only use journey + environment signals.

Rules:
- ZONE_ENTRY -> usually UNLOCK_CHAT and YELLOW.
- If userSignal == EMERGENCY -> TRIGGER_EMERGENCY and RED and subcenterAdvice=ACTIVATE.
- If chatMode is LOCKED and you want interaction -> UNLOCK_CHAT.
- Keep brief short (1-2 lines). Chat messages must be short and actionable.
- reasons: max 6 short strings (no long paragraphs).
"""

    payload_str = json.dumps(context_json, ensure_ascii=False)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=f"Context JSON:\n{payload_str}\n\nReturn decision JSON now.")],
        )
    ]

    config = types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.9,
        max_output_tokens=450,
        response_mime_type="application/json",
        response_schema=response_schema,
        system_instruction=system_instruction,
    )

    try:
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
    except Exception:
        # Safe fallback
        fb = _fallback_response(context_json)
        # Ensure new keys exist
        fb.setdefault("fpsProfile", "LOW")
        fb.setdefault("subcenterAdvice", "NONE")
        fb.setdefault("reasons", [])
        if fb.get("action") == "TRIGGER_EMERGENCY":
            fb["subcenterAdvice"] = "ACTIVATE"
            if not fb["reasons"]:
                fb["reasons"] = ["user_emergency_signal"]
        return fb

    text = getattr(resp, "text", None)
    if not text:
        fb = _fallback_response(context_json)
        fb.setdefault("fpsProfile", "LOW")
        fb.setdefault("subcenterAdvice", "NONE")
        fb.setdefault("reasons", [])
        return fb

    try:
        data = json.loads(text)
    except Exception:
        fb = _fallback_response(context_json)
        fb.setdefault("fpsProfile", "LOW")
        fb.setdefault("subcenterAdvice", "NONE")
        fb.setdefault("reasons", [])
        return fb

    # ---- Final guardrails ----
    risk = data.get("riskColor")
    fps = data.get("fpsProfile")
    subcenter_advice = data.get("subcenterAdvice")
    reasons = data.get("reasons")
    action = data.get("action")
    brief = data.get("brief")
    msgs = data.get("chatMessages")

    if risk not in ("BLUE", "YELLOW", "RED"):
        return _fallback_response(context_json) | {"fpsProfile": "LOW", "subcenterAdvice": "NONE", "reasons": []}
    if fps not in ("LOW", "MEDIUM", "HIGH"):
        fps = "LOW"
    if subcenter_advice not in ("ACTIVATE", "NONE"):
        subcenter_advice = "NONE"
    if action not in ("NONE", "UNLOCK_CHAT", "HUMAN_TAKEOVER", "TRIGGER_EMERGENCY", "SET_IN_ZONE", "ACTIVATE_SUBCENTER"):
        return _fallback_response(context_json) | {"fpsProfile": "LOW", "subcenterAdvice": "NONE", "reasons": []}
    if not isinstance(brief, str) or not isinstance(msgs, list):
        return _fallback_response(context_json) | {"fpsProfile": "LOW", "subcenterAdvice": "NONE", "reasons": []}
    if not isinstance(reasons, list):
        reasons = []

    safe_msgs: List[str] = []
    for m in msgs:
        if isinstance(m, str) and m.strip():
            safe_msgs.append(m.strip())
    safe_msgs = safe_msgs[:8]

    safe_reasons: List[str] = []
    for r in reasons:
        s = str(r).strip()
        if s:
            safe_reasons.append(s[:120])
    safe_reasons = safe_reasons[:6]

    # If emergency action, ensure advice set
    if action == "TRIGGER_EMERGENCY":
        subcenter_advice = "ACTIVATE"
        if not safe_reasons:
            safe_reasons = ["user_emergency_signal"]

    return {
        "riskColor": risk,
        "fpsProfile": fps,
        "subcenterAdvice": subcenter_advice,
        "reasons": safe_reasons,
        "brief": brief.strip()[:500],
        "chatMessages": safe_msgs,
        "action": action,
    }

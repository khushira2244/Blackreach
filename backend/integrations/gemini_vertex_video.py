# integrations/gemini_vertex_video.py

import json
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from google.oauth2 import service_account


def _get_env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if not val:
        raise RuntimeError(f"{name} is missing in environment")
    return val


def _video_fallback() -> Dict[str, Any]:
    return {
        "isEmergency": False,
        "confidence": 0.2,
        "signals": ["uncertain_visual_context"],
        "summary": "Unable to determine a clear emergency from the provided frames.",
    }


def generate_video_emergency_response(context_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Video-only Gemini call (separate from vigilant worker).
    Returns:
      { isEmergency: bool, confidence: float(0..1), signals: [str], summary: str }
    """

    project_id = _get_env("GOOGLE_CLOUD_PROJECT")
    location = _get_env("GOOGLE_CLOUD_LOCATION", "asia-south1")
    model = _get_env("GEMINI_MODEL", "gemini-2.5-flash")

    # IMPORTANT: use your own variable (does NOT touch Firebase)
    sa_path = _get_env("VERTEX_SA_PATH")
    creds = service_account.Credentials.from_service_account_file(sa_path)

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        credentials=creds,
    )

    response_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "isEmergency": {"type": "boolean"},
            "confidence": {"type": "number"},
            "signals": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
        },
        "required": ["isEmergency", "confidence", "signals", "summary"],
        "additionalProperties": False,
    }

    system_instruction = """
You are a VIDEO EMERGENCY CLASSIFIER.
Use ONLY the provided frames + note. Do NOT use any route/chat/tracking info.
Output ONLY JSON matching the schema.

Emergency = visible immediate harm, assault, fire/smoke, weapon threat, severe distress, unconsciousness, blood, accident.
If unclear, set isEmergency=false and confidence low.
signals = short keywords like: ["weapon_visible","assault","blood","fire_smoke","panic_run","crowd_fleeing","unconscious"]
"""

    payload_str = json.dumps(context_json, ensure_ascii=False)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=f"Context JSON:\n{payload_str}\n\nReturn JSON now.")],
        )
    ]

    config = types.GenerateContentConfig(
        temperature=0.1,
        top_p=0.9,
        max_output_tokens=300,
        response_mime_type="application/json",
        response_schema=response_schema,
        system_instruction=system_instruction,
    )

    try:
        resp = client.models.generate_content(model=model, contents=contents, config=config)
    except Exception:
        return _video_fallback()

    text = getattr(resp, "text", None)
    if not text:
        return _video_fallback()

    try:
        data = json.loads(text)
    except Exception:
        return _video_fallback()

    # guardrails
    is_em = bool(data.get("isEmergency"))
    try:
        conf = float(data.get("confidence", 0.0))
    except Exception:
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    sig = data.get("signals")
    if not isinstance(sig, list):
        sig = []
    sig = [str(s).strip()[:40] for s in sig if str(s).strip()][:10]

    summ = data.get("summary")
    if not isinstance(summ, str):
        summ = str(summ)
    summ = summ.strip()[:500]

    return {"isEmergency": is_em, "confidence": conf, "signals": sig, "summary": summ}

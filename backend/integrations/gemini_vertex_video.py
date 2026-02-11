import base64
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
    Video-only Gemini call via Vertex AI.
    Returns:
      { isEmergency: bool, confidence: float(0..1), signals: [str], summary: str }
    """

    # ------------------------
    # ENV
    # ------------------------
    # project_id = _get_env("GOOGLE_CLOUD_PROJECT")
    # location = "asia-south1"  # hardcoded working location
    # model = "gemini-2.0-flash"  # hardcoded working model


    project_id = _get_env("GOOGLE_CLOUD_PROJECT")
    location = "us-central1"          # hardcoded region (recommended)
    model = "gemini-2.0-flash" 

   # hardcoded working model


    # ------------------------
    # FIXED AUTH (IMPORTANT)
    # ------------------------
    sa_path = _get_env("VERTEX_SA_PATH")

    creds = service_account.Credentials.from_service_account_file(
        sa_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    # important for billing / token audience
    creds = creds.with_quota_project(project_id)

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        credentials=creds,
    )

    # ------------------------
    # RESPONSE SCHEMA
    # ------------------------
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
Use ONLY the provided frames + note.
Do NOT use route/chat/tracking information.
Return ONLY valid JSON matching the schema.

Emergency = visible immediate harm, assault, fire/smoke, weapon threat,
severe distress, unconsciousness, blood, accident.

If unclear, set isEmergency=false and confidence low.
signals = short keywords.
"""

    # ------------------------
    # BUILD IMAGE PARTS
    # ------------------------
    video = (context_json or {}).get("video") or {}
    frames = video.get("frames") or []

    parts: List[types.Part] = []

    # 1) Add images first
    for f in frames[:6]:
        b64 = (f.get("data_b64") or "").strip()
        if not b64:
            continue

        # remove accidental data URL prefix
        if b64.startswith("data:image"):
            b64 = b64.split(",", 1)[-1].strip()

        try:
            img_bytes = base64.b64decode(b64)  # safe decode
        except Exception:
            continue

        mime = f.get("mimeType") or "image/jpeg"

        parts.append(
            types.Part(
                inline_data=types.Blob(
                    mime_type=mime,
                    data=img_bytes,
                )
            )
        )

    # 2) Add text instruction
    prompt = json.dumps(context_json, ensure_ascii=False)
    parts.append(types.Part(text=prompt))

    contents = [types.Content(role="user", parts=parts)]

    config = types.GenerateContentConfig(
        temperature=0.1,
        top_p=0.9,
        max_output_tokens=300,
        response_mime_type="application/json",
        response_schema=response_schema,
        system_instruction=system_instruction,
    )

    # ------------------------
    # CALL GEMINI
    # ------------------------
    try:
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
    except Exception as e:
        return {
            "isEmergency": False,
            "confidence": 0.2,
            "signals": ["video_analysis_failed"],
            "summary": f"Gemini call failed: {repr(e)[:300]}",
        }

    text = getattr(resp, "text", None)
    if not text:
        return _video_fallback()

    try:
        data = json.loads(text)
    except Exception:
        return _video_fallback()

    # ------------------------
    # GUARDRAILS
    # ------------------------
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

    return {
        "isEmergency": is_em,
        "confidence": conf,
        "signals": sig,
        "summary": summ,
    }

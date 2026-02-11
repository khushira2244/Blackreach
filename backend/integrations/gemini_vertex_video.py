# integrations/gemini_vertex_video.py
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


def _guess_mime(b64: str) -> str:
    head = (b64 or "")[:10]
    if head.startswith("/9j/"):
        return "image/jpeg"
    if head.startswith("iVBORw0"):
        return "image/png"
    return "image/jpeg"


def _strip_data_prefix(b64: str) -> str:
    if not b64:
        return b64
    if "base64," in b64:
        return b64.split("base64,", 1)[1]
    return b64


def _safe_json_parse(s: str):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None

    # Find first complete JSON object {...} anywhere in the text
    start = s.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(s)):
            ch = s[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = s[start : i + 1].strip()
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break
    return None


def generate_video_emergency_response(context: Dict[str, Any]) -> Dict[str, Any]:
    def _video_fallback() -> Dict[str, Any]:
        return {
            "isEmergency": False,
            "confidence": 0.2,
            "signals": ["uncertain_visual_context"],
            "summary": "Unable to determine a clear emergency from the provided frames.",
        }

    video = context.get("video") or {}
    frames = video.get("frames") or []
    if not isinstance(frames, list) or len(frames) == 0:
        return _video_fallback()

    project_id = _get_env("GOOGLE_CLOUD_PROJECT")
    location =  "global"  
    model =  "gemini-3-flash-preview" 

    sa_path = _get_env("VERTEX_SA_PATH")
    creds = service_account.Credentials.from_service_account_file(
        sa_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    ).with_quota_project(project_id)

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        credentials=creds,
    )

    # ✅ Keep text SHORT. Do NOT dump full context JSON.
    note = (context.get("note") or "")[:250]
    fps = context.get("fpsRate")
    frame_count = len(frames)

    user_prompt = f"""
You are an emergency classifier for a personal safety system.

Return ONLY a JSON object (no markdown, no backticks, no extra words) with EXACT keys:
{{
  "isEmergency": true/false,
  "confidence": 0..1,
  "signals": ["short_tag", ...],
  "summary": "short"
}}

Decision rules:
- If clear violence / injury / restraint / severe distress / threat -> isEmergency=true
- If normal selfie / unclear -> isEmergency=false (confidence low)

Context: fpsRate={fps}, frameCount={frame_count}, note="{note}"
NOW RETURN JSON ONLY.
""".strip()

    parts: List[types.Part] = [types.Part(text=user_prompt)]

    # Add images
    for f in frames[:6]:  # ✅ fewer frames = more output space
        b64 = _strip_data_prefix((f or {}).get("data_b64") or "")
        if not b64:
            continue
        try:
            img_bytes = base64.b64decode(b64)
        except Exception:
            continue
        mime = _guess_mime(b64)
        parts.append(types.Part(inline_data=types.Blob(mime_type=mime, data=img_bytes)))

    if len(parts) == 1:
        return _video_fallback()

    contents = [types.Content(role="user", parts=parts)]

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=512,  # ✅ give room for JSON
        top_p=0.9,
    )

    try:
        resp = client.models.generate_content(model=model, contents=contents, config=config)

        # ✅ Extract text from candidates (more reliable than resp.text for preview models)
        raw_text = ""
        try:
            cand = resp.candidates[0]
            raw_text = "".join(
                [getattr(p, "text", "") for p in cand.content.parts if getattr(p, "text", None)]
            ).strip()
        except Exception:
            raw_text = (getattr(resp, "text", "") or "").strip()

        data = _safe_json_parse(raw_text)

        if not data:
            return {
                "isEmergency": False,
                "confidence": 0.2,
                "signals": ["debug_no_json"],
                "summary": f"Gemini returned non-JSON. raw_text={repr(raw_text)[:800]}",
            }

        # ✅ minimal guardrails
        data.setdefault("isEmergency", False)
        data.setdefault("confidence", 0.2)
        data.setdefault("signals", ["model_output"])
        data.setdefault("summary", "ok")
        return data

    except Exception as e:
        return {
            "isEmergency": False,
            "confidence": 0.2,
            "signals": ["video_analysis_failed"],
            "summary": f"Gemini call failed: {type(e).__name__}: {str(e)[:240]}",
        }

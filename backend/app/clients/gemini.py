import base64

import httpx

from backend.app.clients.http import api_client
from backend.app.config import get_settings

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-1.5-flash:generateContent"
)

_ANALYSIS_PROMPT = (
    "Listen to this music clip and describe it concisely in 3-4 sentences. "
    "Cover: genre and subgenre, mood and emotion, tempo (slow/mid/fast), "
    "key instruments, vocal style (if any), production style, and energy level. "
    "Focus on characteristics that would help find musically similar songs."
)


async def analyze_audio_preview(preview_url: str) -> str | None:
    """Download a 30-second preview and return Gemini's musical analysis.

    Returns None when the API key is not configured or the request fails,
    so callers can degrade gracefully without the audio context.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    try:
        async with api_client() as client:
            audio_response = await client.get(str(preview_url), timeout=15.0)
            audio_response.raise_for_status()
            audio_b64 = base64.b64encode(audio_response.content).decode()
            raw_mime = audio_response.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
            # Normalize non-standard MIME types to ones Gemini accepts.
            mime_type = {
                "audio/x-m4a": "audio/mp4",
                "audio/m4a": "audio/mp4",
                "audio/x-aac": "audio/aac",
                "audio/x-mpeg": "audio/mpeg",
            }.get(raw_mime, raw_mime)
    except httpx.HTTPError:
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": audio_b64}},
                    {"text": _ANALYSIS_PROMPT},
                ]
            }
        ]
    }

    try:
        async with api_client() as client:
            response = await client.post(
                f"{GEMINI_URL}?key={settings.gemini_api_key}",
                json=payload,
                timeout=20.0,
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return None

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return None

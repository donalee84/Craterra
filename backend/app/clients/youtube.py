import httpx

from backend.app.clients.http import api_client, request_with_retries
from backend.app.config import get_settings
from backend.app.services.text_match import normalize_key

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


async def search_youtube_music(artist: str, title: str) -> bool:
    """Return True if a matching song is found on YouTube.

    Used as a strict final gate for AI-generated (Track 2) suggestions to
    filter hallucinations before they reach the UI. Returns True (pass) when
    the API key is not configured so the gate is transparent in dev/test.
    """
    settings = get_settings()
    if not settings.youtube_api_key:
        return True

    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                YOUTUBE_SEARCH_URL,
                service="youtube",
                params={
                    "part": "snippet",
                    "q": f"{artist} {title}",
                    "type": "video",
                    "videoCategoryId": "10",
                    "maxResults": 3,
                    "key": settings.youtube_api_key,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return True

    artist_tokens = set(normalize_key(artist).split())
    title_tokens = {tok for tok in normalize_key(title).split() if len(tok) > 1}

    for item in response.json().get("items", []):
        snippet = item.get("snippet", {})
        yt_title_tokens = set(normalize_key(snippet.get("title", "")).split())
        yt_channel_tokens = set(normalize_key(snippet.get("channelTitle", "")).split())

        artist_hit = artist_tokens & (yt_title_tokens | yt_channel_tokens)
        title_hit = title_tokens & yt_title_tokens
        if artist_hit and title_hit:
            return True

    return False

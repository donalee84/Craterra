from typing import Any

import httpx

from backend.app.clients.http import api_client, request_with_retries
from backend.app.schemas import TrackValidationResult

DEEZER_SEARCH_URL = "https://api.deezer.com/search"
DEEZER_ARTIST_SEARCH_URL = "https://api.deezer.com/search/artist"


async def resolve_artist_name(name: str | None) -> str | None:
    """Return Deezer's canonical (often romanized) artist name for a query.

    Last.fm indexes artists by romanized name, so "아이유" -> "IU" lets the
    candidate pool resolve for non-Latin artist input.
    """
    if not name:
        return None
    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                DEEZER_ARTIST_SEARCH_URL,
                service="deezer",
                params={"q": name, "limit": 1},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return None

    data = response.json().get("data", [])
    if not data:
        return None
    return data[0].get("name") or None


async def search_deezer(query: str) -> TrackValidationResult | None:
    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                DEEZER_SEARCH_URL,
                service="deezer",
                params={"q": query, "limit": 1},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return None

    data = response.json().get("data", [])
    if not data:
        return None

    track: dict[str, Any] = data[0]
    artist = track.get("artist") or {}
    album = track.get("album") or {}

    return TrackValidationResult(
        source="deezer",
        title=track.get("title") or query,
        artist=artist.get("name") or "Unknown artist",
        album=album.get("title"),
        release_date=None,
        artwork_url=album.get("cover_medium") or album.get("cover_big"),
        preview_url=track.get("preview"),
        external_url=track.get("link"),
        confidence=0.92,
    )

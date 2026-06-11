from typing import Any

import httpx

from backend.app.clients.http import api_client
from backend.app.schemas import TrackValidationResult

DEEZER_SEARCH_URL = "https://api.deezer.com/search"


async def search_deezer(query: str) -> TrackValidationResult | None:
    try:
        async with api_client() as client:
            response = await client.get(DEEZER_SEARCH_URL, params={"q": query, "limit": 1})
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


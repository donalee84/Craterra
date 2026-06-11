from typing import Any

import httpx

from backend.app.clients.http import api_client
from backend.app.schemas import TrackValidationResult

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


async def search_itunes(query: str) -> TrackValidationResult | None:
    try:
        async with api_client() as client:
            response = await client.get(
                ITUNES_SEARCH_URL,
                params={"term": query, "media": "music", "entity": "song", "limit": 1},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return None

    results = response.json().get("results", [])
    if not results:
        return None

    track: dict[str, Any] = results[0]

    return TrackValidationResult(
        source="itunes",
        title=track.get("trackName") or query,
        artist=track.get("artistName") or "Unknown artist",
        album=track.get("collectionName"),
        release_date=track.get("releaseDate"),
        artwork_url=track.get("artworkUrl100"),
        preview_url=track.get("previewUrl"),
        external_url=track.get("trackViewUrl"),
        confidence=0.72,
    )


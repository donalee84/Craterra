from typing import Any

import httpx

from backend.app.clients.http import api_client, request_with_retries
from backend.app.schemas import TrackValidationResult

MUSICBRAINZ_SEARCH_URL = "https://musicbrainz.org/ws/2/recording"


async def search_musicbrainz(query: str) -> TrackValidationResult | None:
    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                MUSICBRAINZ_SEARCH_URL,
                service="musicbrainz",
                params={"query": query, "fmt": "json", "limit": 1},
                headers={"User-Agent": "Craterra/0.1.0 (local-development)"},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return None

    recordings = response.json().get("recordings", [])
    if not recordings:
        return None

    recording: dict[str, Any] = recordings[0]
    artist_credit = recording.get("artist-credit") or []
    release_list = recording.get("releases") or []
    release = release_list[0] if release_list else {}

    artist = "Unknown artist"
    if artist_credit:
        artist = artist_credit[0].get("name") or artist

    return TrackValidationResult(
        source="musicbrainz",
        title=recording.get("title") or query,
        artist=artist,
        album=release.get("title"),
        release_date=release.get("date"),
        artwork_url=None,
        preview_url=None,
        external_url=None,
        confidence=0.8,
    )

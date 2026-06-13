from typing import Any

import httpx

from backend.app.clients.http import api_client, request_with_retries
from backend.app.schemas import CandidateTrack

LISTENBRAINZ_API_URL = "https://api.listenbrainz.org"
MUSICBRAINZ_ARTIST_URL = "https://musicbrainz.org/ws/2/artist"
USER_AGENT = "Craterra/0.1.0 (local-development)"


async def get_artist_top_recordings(
    artist_name: str | None,
    limit: int = 10,
) -> list[CandidateTrack]:
    if not artist_name:
        return []

    artist_mbid = await _lookup_artist_mbid(artist_name)
    if not artist_mbid:
        return []

    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                f"{LISTENBRAINZ_API_URL}/1/popularity/top-recordings-for-artist/{artist_mbid}",
                service="listenbrainz",
                params={"count": limit},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return []

    payload = response.json()
    if not isinstance(payload, list):
        return []

    return [_normalize_recording(recording) for recording in payload[:limit]]


async def _lookup_artist_mbid(artist_name: str) -> str | None:
    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                MUSICBRAINZ_ARTIST_URL,
                service="musicbrainz",
                params={
                    "query": f'artist:"{artist_name}"',
                    "fmt": "json",
                    "limit": 1,
                },
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return None

    artists = response.json().get("artists", [])
    if not artists:
        return None
    return artists[0].get("id")


def _normalize_recording(recording: dict[str, Any]) -> CandidateTrack:
    listeners = _safe_int(recording.get("total_user_count"))
    playcount = _safe_int(recording.get("total_listen_count"))
    recording_mbid = recording.get("recording_mbid")

    return CandidateTrack(
        title=recording.get("recording_name") or "Unknown title",
        artist=recording.get("artist_name") or "Unknown artist",
        source="listenbrainz:top-recordings-for-artist",
        listeners=listeners,
        playcount=playcount,
        external_url=(
            f"https://listenbrainz.org/player?recording_mbids={recording_mbid}"
            if recording_mbid
            else None
        ),
    )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

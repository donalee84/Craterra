import asyncio
from typing import Any

import httpx

from backend.app.clients.http import api_client, request_with_retries
from backend.app.config import get_settings
from backend.app.schemas import CandidateTrack

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"


class LastFmNotConfiguredError(RuntimeError):
    pass


class LastFmApiError(RuntimeError):
    pass


async def get_candidate_tracks(
    query: str,
    limit: int = 10,
    root_title: str | None = None,
    root_artist: str | None = None,
) -> tuple[list[CandidateTrack], bool]:
    """Return (candidates, has_direct_similar).

    has_direct_similar=True means Last.fm returned track.getSimilar data
    specifically for the root track. False means we fell back to a search-
    based path, which finds similar tracks for a different song — a weaker
    signal that should trigger the Track 2 AI-generation path in dig.py.
    """
    settings = get_settings()
    if not settings.lastfm_api_key:
        raise LastFmNotConfiguredError("LASTFM_API_KEY is not configured.")

    if root_title and root_artist:
        similar_tracks = await _track_get_similar(
            title=root_title,
            artist=root_artist,
            api_key=settings.lastfm_api_key,
            limit=limit,
        )
        if similar_tracks:
            return similar_tracks, True

    search_results = await _track_search(query, settings.lastfm_api_key, limit=1)
    if not search_results:
        return [], False

    root = search_results[0]
    title = root.get("name") or query
    artist = root.get("artist") or ""

    similar_tracks = await _track_get_similar(
        title=title,
        artist=artist,
        api_key=settings.lastfm_api_key,
        limit=limit,
    )

    if similar_tracks:
        return similar_tracks, False

    return _normalize_search_results(search_results, limit=limit), False


async def get_similar_artist_tracks(
    artist: str | None,
    limit: int = 12,
    per_artist: int = 2,
) -> list[CandidateTrack]:
    """Top tracks from artists Last.fm considers similar to the seed artist.

    Broadens the pool with *other* artists so niche seeds are not dominated by
    the seed artist's own catalog.
    """
    settings = get_settings()
    if not settings.lastfm_api_key or not artist:
        return []

    similar = await _artist_get_similar(artist, settings.lastfm_api_key, limit=8)
    if not similar:
        return []

    # Bound concurrency so this fan-out does not trip Last.fm's per-key rate
    # limit (which would silently empty the pool, especially for niche seeds
    # where this is the only source with data).
    semaphore = asyncio.Semaphore(3)

    async def _bounded(name: str) -> list[CandidateTrack]:
        async with semaphore:
            return await _artist_get_top_tracks(name, settings.lastfm_api_key, limit=per_artist)

    results = await asyncio.gather(
        *[_bounded(name) for name in similar],
        return_exceptions=True,
    )

    candidates: list[CandidateTrack] = []
    for result in results:
        if isinstance(result, list):
            candidates.extend(result)
    return candidates[:limit]


async def _artist_get_similar(artist: str, api_key: str, limit: int) -> list[str]:
    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                LASTFM_API_URL,
                service="lastfm",
                params={
                    "method": "artist.getSimilar",
                    "artist": artist,
                    "api_key": api_key,
                    "format": "json",
                    "limit": limit,
                    "autocorrect": 1,
                },
            )
            _raise_for_lastfm_error(response)
    except (httpx.HTTPError, LastFmApiError):
        return []

    artists = response.json().get("similarartists", {}).get("artist", [])
    if isinstance(artists, dict):
        artists = [artists]
    return [artist.get("name") for artist in artists if artist.get("name")][:limit]


async def _artist_get_top_tracks(artist: str, api_key: str, limit: int) -> list[CandidateTrack]:
    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                LASTFM_API_URL,
                service="lastfm",
                params={
                    "method": "artist.getTopTracks",
                    "artist": artist,
                    "api_key": api_key,
                    "format": "json",
                    "limit": limit,
                    "autocorrect": 1,
                },
            )
            _raise_for_lastfm_error(response)
    except (httpx.HTTPError, LastFmApiError):
        return []

    tracks = response.json().get("toptracks", {}).get("track", [])
    if isinstance(tracks, dict):
        tracks = [tracks]
    return [_normalize_artist_top_track(track) for track in tracks[:limit]]


def _normalize_artist_top_track(track: dict[str, Any]) -> CandidateTrack:
    artist = track.get("artist") or {}
    playcount = _safe_int(track.get("playcount"))
    listeners = _safe_int(track.get("listeners"))
    rarity_score = _rarity_score(playcount=playcount, listeners=listeners)
    return CandidateTrack(
        title=track.get("name") or "Unknown title",
        artist=artist.get("name") or "Unknown artist",
        source="lastfm:artist.topTracks",
        playcount=playcount,
        listeners=listeners,
        rarity_score=rarity_score,
        rarity_label=_rarity_label(rarity_score),
        external_url=track.get("url") or None,
    )


async def _track_search(query: str, api_key: str, limit: int) -> list[dict[str, Any]]:
    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                LASTFM_API_URL,
                service="lastfm",
                params={
                    "method": "track.search",
                    "track": query,
                    "api_key": api_key,
                    "format": "json",
                    "limit": limit,
                },
            )
            _raise_for_lastfm_error(response)
    except httpx.HTTPError:
        return []

    matches = response.json().get("results", {}).get("trackmatches", {}).get("track", [])
    if isinstance(matches, dict):
        return [matches]
    return matches


async def _track_get_similar(
    title: str,
    artist: str,
    api_key: str,
    limit: int,
) -> list[CandidateTrack]:
    if not artist:
        return []

    try:
        async with api_client() as client:
            response = await request_with_retries(
                client,
                "GET",
                LASTFM_API_URL,
                service="lastfm",
                params={
                    "method": "track.getSimilar",
                    "track": title,
                    "artist": artist,
                    "api_key": api_key,
                    "format": "json",
                    "limit": limit,
                    "autocorrect": 1,
                },
            )
            _raise_for_lastfm_error(response)
    except httpx.HTTPError:
        return []

    tracks = response.json().get("similartracks", {}).get("track", [])
    if isinstance(tracks, dict):
        tracks = [tracks]

    return [_normalize_similar_track(track) for track in tracks[:limit]]


def _normalize_search_results(
    tracks: list[dict[str, Any]],
    limit: int,
) -> list[CandidateTrack]:
    return [_normalize_search_track(track) for track in tracks[:limit]]


def _normalize_search_track(track: dict[str, Any]) -> CandidateTrack:
    return CandidateTrack(
        title=track.get("name") or "Unknown title",
        artist=track.get("artist") or "Unknown artist",
        source="lastfm:track.search",
        listeners=_safe_int(track.get("listeners")),
        rarity_score=_rarity_score(listeners=_safe_int(track.get("listeners"))),
        rarity_label=_rarity_label(_rarity_score(listeners=_safe_int(track.get("listeners")))),
        external_url=track.get("url") or None,
    )


def _normalize_similar_track(track: dict[str, Any]) -> CandidateTrack:
    artist = track.get("artist") or {}
    playcount = _safe_int(track.get("playcount"))
    rarity_score = _rarity_score(playcount=playcount)
    return CandidateTrack(
        title=track.get("name") or "Unknown title",
        artist=artist.get("name") or "Unknown artist",
        source="lastfm:track.getSimilar",
        match_score=_safe_float(track.get("match")),
        playcount=playcount,
        rarity_score=rarity_score,
        rarity_label=_rarity_label(rarity_score),
        external_url=track.get("url") or None,
    )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rarity_score(
    *,
    playcount: int | None = None,
    listeners: int | None = None,
) -> float | None:
    value = playcount if playcount is not None else listeners
    if value is None:
        return None

    if value <= 100_000:
        return 1.0
    if value <= 500_000:
        return 0.85
    if value <= 1_000_000:
        return 0.7
    if value <= 5_000_000:
        return 0.55
    if value <= 15_000_000:
        return 0.35
    return 0.15


def _rarity_label(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 0.85:
        return "Deep cut"
    if score >= 0.55:
        return "Underplayed"
    if score >= 0.35:
        return "Familiar"
    return "Popular"


def _raise_for_lastfm_error(response: httpx.Response) -> None:
    if response.status_code >= 400:
        try:
            data = response.json()
        except ValueError as exc:
            raise LastFmApiError(f"Last.fm returned HTTP {response.status_code}.") from exc
        message = data.get("message") or f"HTTP {response.status_code}"
        raise LastFmApiError(f"Last.fm API error: {message}")

    # Last.fm reports API errors (e.g. invalid key) as HTTP 200 with an error
    # field, so guard against silently treating them as empty results.
    try:
        data = response.json()
    except ValueError:
        return
    if isinstance(data, dict) and data.get("error"):
        message = data.get("message") or f"error {data.get('error')}"
        raise LastFmApiError(f"Last.fm API error: {message}")

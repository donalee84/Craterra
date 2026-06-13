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
                params={
                    "query": query,
                    "fmt": "json",
                    "limit": 1,
                    "inc": "artist-rels+work-rels+work-level-rels",
                },
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
        relationship_summary=_relationship_summary(recording),
        confidence=0.8,
    )


def _relationship_summary(recording: dict[str, Any]) -> list[str]:
    summaries: list[str] = []

    for relation in recording.get("relations") or []:
        summary = _format_relation(relation)
        if summary:
            summaries.append(summary)

    for work in recording.get("works") or []:
        work_title = work.get("title")
        if work_title:
            summaries.append(f"work: {work_title}")
        for relation in work.get("relations") or []:
            summary = _format_relation(relation)
            if summary:
                summaries.append(summary)

    return _dedupe(summaries, limit=6)


def _format_relation(relation: dict[str, Any]) -> str | None:
    relation_type = relation.get("type")
    target_name = _relation_target_name(relation)
    if not relation_type or not target_name:
        return None

    attributes = relation.get("attributes") or []
    attribute_text = f" ({', '.join(attributes)})" if attributes else ""
    return f"{relation_type}: {target_name}{attribute_text}"


def _relation_target_name(relation: dict[str, Any]) -> str | None:
    for key in ("artist", "work", "recording", "release", "release-group", "url"):
        target = relation.get(key)
        if not isinstance(target, dict):
            continue
        return target.get("name") or target.get("title") or target.get("resource")
    return None


def _dedupe(values: list[str], limit: int) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
        if len(deduped) >= limit:
            break
    return deduped

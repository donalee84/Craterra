import logging
import re

from fastapi import HTTPException, status

from backend.app.clients.lastfm import (
    LastFmApiError,
    LastFmNotConfiguredError,
    get_candidate_tracks,
    get_similar_artist_tracks,
)
from backend.app.clients.listenbrainz import get_artist_top_recordings
from backend.app.clients.openrouter import (
    OpenRouterCurationError,
    OpenRouterNotConfiguredError,
    curate_candidates,
)
from backend.app.clients.deezer import resolve_artist_name, search_deezer
from backend.app.schemas import CandidateTrack, DigRequest, DigResponse, RecommendationCard
from backend.app.services.outbound_links import build_outbound_links
from backend.app.services.persistence import get_session_profile, save_dig_history
from backend.app.services.text_match import normalize_key as _normalize_key, text_close as _text_close
from backend.app.services.validation import validate_track


async def build_dig_response(request: DigRequest) -> DigResponse:
    if request.artist:
        # Trust the explicit artist/song fields. Resolve the artist to Deezer's
        # canonical (romanized) name so Last.fm, which indexes by romanized
        # name, can find similar tracks (e.g. "아이유" -> "IU").
        seed_artist = await resolve_artist_name(request.artist) or request.artist
        seed_title = request.query
        seed_query = f"{seed_artist} {seed_title}"
    else:
        # Legacy free-text query: let Deezer normalize the whole string.
        root_validation = await search_deezer(request.query)
        seed_artist = root_validation.artist if root_validation else None
        seed_title = root_validation.title if root_validation else None
        seed_query = request.query

    try:
        candidates = await get_candidate_tracks(
            seed_query,
            limit=25,
            root_title=seed_title,
            root_artist=seed_artist,
        )
    except LastFmNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LASTFM_API_KEY is required before /dig can build a candidate pool.",
        ) from exc
    except LastFmApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    listenbrainz_candidates = await get_artist_top_recordings(
        seed_artist,
        limit=10,
    )
    similar_artist_candidates = await get_similar_artist_tracks(
        seed_artist,
        limit=14,
    )
    candidates = _merge_candidates(
        candidates,
        similar_artist_candidates,
        listenbrainz_candidates,
        limit=45,
    )

    _apply_relative_rarity(candidates)

    if not candidates:
        return DigResponse(
            query=request.query,
            candidates=[],
            recommendations=[],
            next_step="No Last.fm or ListenBrainz candidates found for this query.",
        )

    session_profile = await get_session_profile(request.session_id)
    curation_candidates = _prepare_curation_candidates(
        candidates,
        root_title=seed_title,
        root_artist=seed_artist,
        distance_level=request.distance_level,
        limit=18,
    )

    try:
        picks, model_used, usage = await curate_candidates(
            request,
            curation_candidates,
            session_profile=session_profile,
            root_title=seed_title,
            root_artist=seed_artist,
        )
    except OpenRouterNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENROUTER_API_KEY is required before /dig can curate recommendations.",
        ) from exc
    except OpenRouterCurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenRouter curation failed: {exc}",
        ) from exc

    recommendations: list[RecommendationCard] = []
    for pick in picks:
        candidate = curation_candidates[pick.candidate_index]
        validation_response = await validate_track(
            f"{candidate.artist} {candidate.title}",
            match_artist=candidate.artist,
            match_title=candidate.title,
        )
        result = validation_response.result
        if result is None:
            # Drop picks we cannot confirm as the same track on
            # Deezer/MusicBrainz/iTunes so the UI never shows an unfindable,
            # hallucination-looking track.
            continue
        recommendations.append(
            RecommendationCard(
                title=candidate.title,
                artist=candidate.artist,
                reason=pick.reason,
                confidence=pick.confidence,
                rarity_score=candidate.rarity_score,
                rarity_label=candidate.rarity_label,
                candidate_source=candidate.source,
                validation=validation_response.result,
                checked_sources=validation_response.checked_sources,
                outbound_links=build_outbound_links(candidate.artist, candidate.title),
            )
        )

    _log_openrouter_usage(model_used, usage)
    await save_dig_history(request, recommendations, model_used, usage)

    return DigResponse(
        query=request.query,
        candidates=candidates,
        recommendations=recommendations,
        model_used=model_used,
        usage=usage,
        next_step="Tune dig-pattern learning and share cards next.",
    )


def _log_openrouter_usage(model_used, usage) -> None:
    if not usage:
        return

    logging.getLogger("craterra.cost").info(
        "openrouter_usage",
        extra={
            "model": model_used,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost": usage.cost,
        },
    )


def _merge_candidates(
    *sources: list[CandidateTrack],
    limit: int,
) -> list[CandidateTrack]:
    merged: list[CandidateTrack] = []
    seen: set[tuple[str, str]] = set()

    for source in sources:
        for candidate in source:
            key = (candidate.artist.casefold().strip(), candidate.title.casefold().strip())
            if key in seen:
                continue
            seen.add(key)
            merged.append(candidate)
            if len(merged) >= limit:
                return merged

    return merged


def _prepare_curation_candidates(
    candidates: list[CandidateTrack],
    *,
    root_title: str | None,
    root_artist: str | None,
    distance_level: int,
    limit: int,
) -> list[CandidateTrack]:
    root_title_key = _normalize_key(root_title)
    root_artist_key = _normalize_key(root_artist)

    without_seed = [
        candidate
        for candidate in candidates
        if not (
            root_title_key
            and root_artist_key
            and _normalize_key(candidate.title) == root_title_key
            and _normalize_key(candidate.artist) == root_artist_key
        )
    ]

    non_filler = [candidate for candidate in without_seed if not _is_filler_track(candidate.title)]
    if len(non_filler) >= min(8, limit):
        without_seed = non_filler

    if distance_level >= 2 and root_artist_key:
        other_artists = [
            candidate
            for candidate in without_seed
            if not _artist_matches_root(candidate.artist, root_artist_key)
        ]
        if len(other_artists) >= min(6, limit):
            without_seed = other_artists

    if distance_level >= 4:
        without_seed = sorted(
            without_seed,
            key=lambda candidate: (
                0 if (candidate.rarity_score or 0) >= 0.28 else 1,
                -(candidate.rarity_score or 0),
                -(candidate.match_score or 0),
            ),
        )
    elif distance_level >= 3:
        without_seed = sorted(
            without_seed,
            key=lambda candidate: (
                0 if (candidate.rarity_label or "") != "Obvious" else 1,
                -(candidate.match_score or 0),
                -(candidate.rarity_score or 0),
            ),
        )

    return without_seed[:limit]


def _apply_relative_rarity(candidates: list[CandidateTrack]) -> None:
    popularity_values = [
        _popularity_value(candidate)
        for candidate in candidates
        if _popularity_value(candidate) is not None
    ]
    if len(popularity_values) < 2:
        return

    minimum = min(popularity_values)
    maximum = max(popularity_values)
    if minimum == maximum:
        return

    for candidate in candidates:
        popularity = _popularity_value(candidate)
        if popularity is None:
            continue

        score = round((maximum - popularity) / (maximum - minimum), 3)
        candidate.rarity_score = score
        candidate.rarity_label = _relative_rarity_label(score)


def _popularity_value(candidate: CandidateTrack) -> int | None:
    return candidate.playcount if candidate.playcount is not None else candidate.listeners


def _relative_rarity_label(score: float) -> str:
    if score >= 0.78:
        return "Deepest here"
    if score >= 0.52:
        return "Less played"
    if score >= 0.28:
        return "Mid-known"
    return "Obvious"


_FILLER_TITLE_RE = re.compile(r"\b(interlude|intro|outro|skit|skits)\b", re.IGNORECASE)
_COLLAB_SPLIT_RE = re.compile(r"\s*(?:,|&|feat\.?|ft\.?|/|\bx\b|\bwith\b|\bvs\.?)\s*", re.IGNORECASE)


def _is_filler_track(title: str | None) -> bool:
    return bool(title and _FILLER_TITLE_RE.search(title))


def _artist_matches_root(artist: str | None, root_artist_key: str) -> bool:
    """True when the candidate is by, or a collaboration including, the seed artist."""
    if not root_artist_key:
        return False
    if _normalize_key(artist) == root_artist_key:
        return True
    return root_artist_key in {_normalize_key(part) for part in _COLLAB_SPLIT_RE.split(artist or "")}

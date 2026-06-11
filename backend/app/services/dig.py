from fastapi import HTTPException, status

from backend.app.clients.lastfm import (
    LastFmApiError,
    LastFmNotConfiguredError,
    get_candidate_tracks,
)
from backend.app.clients.listenbrainz import get_artist_top_recordings
from backend.app.clients.openrouter import (
    OpenRouterCurationError,
    OpenRouterNotConfiguredError,
    curate_candidates,
)
from backend.app.clients.deezer import search_deezer
from backend.app.schemas import CandidateTrack, DigRequest, DigResponse, RecommendationCard
from backend.app.services.outbound_links import build_outbound_links
from backend.app.services.persistence import get_session_profile, save_dig_history
from backend.app.services.validation import validate_track


async def build_dig_response(request: DigRequest) -> DigResponse:
    root_validation = await search_deezer(request.query)

    try:
        candidates = await get_candidate_tracks(
            request.query,
            limit=25,
            root_title=root_validation.title if root_validation else None,
            root_artist=root_validation.artist if root_validation else None,
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
        root_validation.artist if root_validation else None,
        limit=10,
    )
    candidates = _merge_candidates(candidates, listenbrainz_candidates, limit=35)

    _apply_relative_rarity(candidates)

    if not candidates:
        return DigResponse(
            query=request.query,
            candidates=[],
            recommendations=[],
            next_step="No Last.fm or ListenBrainz candidates found for this query.",
        )

    session_profile = await get_session_profile(request.session_id)
    curation_candidates = candidates[:18]

    try:
        picks, model_used = await curate_candidates(
            request,
            curation_candidates,
            session_profile=session_profile,
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
        validation_response = await validate_track(f"{candidate.artist} {candidate.title}")
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

    await save_dig_history(request, recommendations, model_used)

    return DigResponse(
        query=request.query,
        candidates=candidates,
        recommendations=recommendations,
        model_used=model_used,
        next_step="Add Bandcamp / Apple Music outbound links next.",
    )


def _merge_candidates(
    primary: list[CandidateTrack],
    secondary: list[CandidateTrack],
    limit: int,
) -> list[CandidateTrack]:
    merged: list[CandidateTrack] = []
    seen: set[tuple[str, str]] = set()

    for candidate in [*primary, *secondary]:
        key = (candidate.artist.casefold().strip(), candidate.title.casefold().strip())
        if key in seen:
            continue
        seen.add(key)
        merged.append(candidate)
        if len(merged) >= limit:
            break

    return merged


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

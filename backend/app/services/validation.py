from backend.app.clients.deezer import search_deezer, search_deezer_candidates
from backend.app.clients.itunes import search_itunes
from backend.app.clients.musicbrainz import search_musicbrainz
from backend.app.clients.youtube import search_youtube_music
from backend.app.schemas import TrackValidationResult, ValidateResponse, ValidationSource
from backend.app.services.text_match import text_close


async def validate_track(
    query: str,
    *,
    match_artist: str | None = None,
    match_title: str | None = None,
    require_youtube: bool = False,
) -> ValidateResponse:
    """Validate a track across Deezer -> MusicBrainz -> iTunes.

    When match_artist/match_title are given, sources return the result that
    actually matches the target instead of their top search hit, so a real
    track is not rejected just because the engine ranked a cover/remix first.

    When require_youtube=True (Track 2 / AI-generated suggestions), the result
    must also be confirmed on YouTube to filter hallucinations. Each YouTube
    call costs 100 units so this flag should only be set for AI-generated picks.
    """
    checked_sources: list[ValidationSource] = []
    result = await _find_track(query, match_artist, match_title, checked_sources)

    if result is None:
        return ValidateResponse(query=query, found=False, checked_sources=checked_sources)

    if require_youtube and match_artist and match_title:
        checked_sources.append("youtube")
        if not await search_youtube_music(match_artist, match_title):
            return ValidateResponse(query=query, found=False, checked_sources=checked_sources)

    return ValidateResponse(
        query=query,
        found=True,
        result=result,
        checked_sources=checked_sources,
    )


async def _find_track(
    query: str,
    match_artist: str | None,
    match_title: str | None,
    checked_sources: list[ValidationSource],
) -> TrackValidationResult | None:
    checked_sources.append("deezer")
    deezer_match = _best_match(
        await search_deezer_candidates(query, limit=8),
        match_artist,
        match_title,
    )
    if deezer_match is not None:
        return deezer_match

    for source, search in (
        ("musicbrainz", search_musicbrainz),
        ("itunes", search_itunes),
    ):
        checked_sources.append(source)
        result = await search(query)
        if result is not None and _accepts(result, match_artist, match_title):
            return result

    return None


def _best_match(
    results: list[TrackValidationResult],
    match_artist: str | None,
    match_title: str | None,
) -> TrackValidationResult | None:
    if not results:
        return None
    if match_artist is None or match_title is None:
        return results[0]
    for result in results:
        if _accepts(result, match_artist, match_title):
            return result
    return None


def _accepts(
    result: TrackValidationResult,
    match_artist: str | None,
    match_title: str | None,
) -> bool:
    if match_artist is None or match_title is None:
        return True
    return text_close(result.artist, match_artist) and text_close(result.title, match_title)

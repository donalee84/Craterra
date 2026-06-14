from backend.app.clients.deezer import search_deezer_candidates
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
    youtube_fallback: bool = False,
) -> ValidateResponse:
    """Validate a track across Deezer -> MusicBrainz -> iTunes (-> YouTube).

    When match_artist/match_title are given, sources return the result that
    actually matches the target instead of their top search hit.

    When youtube_fallback=True (Track 2), YouTube is used as a final source
    if Deezer/MusicBrainz/iTunes all fail to confirm the track. This allows
    niche or regional songs not well-indexed on Deezer to still pass through
    as long as they exist on YouTube.
    """
    checked_sources: list[ValidationSource] = []
    result = await _find_track(
        query, match_artist, match_title, checked_sources, youtube_fallback
    )

    if result is None:
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
    youtube_fallback: bool = False,
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

    # YouTube as final fallback for Track 2: confirms the song exists even
    # when major catalogs don't index it well (e.g. Korean indie/rock).
    if youtube_fallback and match_artist and match_title:
        checked_sources.append("youtube")
        if await search_youtube_music(match_artist, match_title):
            return TrackValidationResult(
                source="youtube",
                title=match_title,
                artist=match_artist,
                confidence=0.6,
            )

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

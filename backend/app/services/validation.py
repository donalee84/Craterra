from backend.app.clients.deezer import search_deezer
from backend.app.clients.itunes import search_itunes
from backend.app.clients.musicbrainz import search_musicbrainz
from backend.app.schemas import TrackValidationResult, ValidateResponse, ValidationSource


async def validate_track(query: str) -> ValidateResponse:
    checked_sources: list[ValidationSource] = []

    for source, search in (
        ("deezer", search_deezer),
        ("musicbrainz", search_musicbrainz),
        ("itunes", search_itunes),
    ):
        checked_sources.append(source)
        result = await search(query)
        if result is not None:
            return ValidateResponse(
                query=query,
                found=True,
                result=result,
                checked_sources=checked_sources,
            )

    return ValidateResponse(query=query, found=False, checked_sources=checked_sources)


from urllib.parse import urlencode

from backend.app.config import get_settings
from backend.app.schemas import OutboundLink


def build_outbound_links(artist: str, title: str) -> list[OutboundLink]:
    query = f"{artist} {title}".strip()
    return [
        OutboundLink(
            service="youtube",
            label="YouTube",
            url=f"https://www.youtube.com/results?{urlencode({'search_query': query})}",
        ),
        OutboundLink(
            service="bandcamp",
            label="Bandcamp",
            url=f"https://bandcamp.com/search?{urlencode({'q': query})}",
        ),
        OutboundLink(
            service="apple_music",
            label="Apple Music",
            url=_apple_music_url(query),
        ),
    ]


def _apple_music_url(query: str) -> str:
    params = {"term": query}
    affiliate_token = get_settings().apple_music_affiliate_token
    if affiliate_token:
        params["at"] = affiliate_token
    return f"https://music.apple.com/search?{urlencode(params)}"

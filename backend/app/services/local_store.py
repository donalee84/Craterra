import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from backend.app.config import get_settings
from backend.app.schemas import (
    DigRequest,
    FeedbackRequest,
    FeedbackResponse,
    OpenRouterUsage,
    OutboundClickRequest,
    RecommendationCard,
    SessionTasteProfile,
)

_LOCK = Lock()


def save_feedback(request: FeedbackRequest) -> FeedbackResponse:
    write_feedback_record(build_feedback_record(request))

    return FeedbackResponse(saved=True, session_id=request.session_id)


def build_feedback_record(request: FeedbackRequest) -> dict[str, Any]:
    return {
        "session_id": request.session_id,
        "song_name": request.song_name,
        "artist_name": request.artist_name,
        "vote": request.vote,
        "created_at": datetime.now(UTC).isoformat(),
    }


def write_feedback_record(record: dict[str, Any]) -> None:
    with _LOCK:
        _feedback_path().parent.mkdir(parents=True, exist_ok=True)
        with _feedback_path().open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_outbound_click_record(request: OutboundClickRequest) -> dict[str, Any]:
    return {
        "session_id": request.session_id,
        "service": request.service,
        "song_name": request.song_name,
        "artist_name": request.artist_name,
        "url": str(request.url),
        "created_at": datetime.now(UTC).isoformat(),
    }


def write_outbound_click_record(record: dict[str, Any]) -> None:
    with _LOCK:
        _outbound_clicks_path().parent.mkdir(parents=True, exist_ok=True)
        with _outbound_clicks_path().open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_session_profile(session_id: str | None) -> SessionTasteProfile | None:
    if not session_id:
        return None

    return build_session_profile(session_id, _read_feedback_records())


def build_session_profile(session_id: str, records: list[dict[str, Any]]) -> SessionTasteProfile:
    liked_tracks: Counter[str] = Counter()
    disliked_tracks: Counter[str] = Counter()
    liked_artists: Counter[str] = Counter()
    disliked_artists: Counter[str] = Counter()

    for record in records:
        if record.get("session_id") != session_id:
            continue

        track_key = _track_key(record.get("artist_name"), record.get("song_name"))
        artist_key = str(record.get("artist_name") or "").strip()
        vote = bool(record.get("vote"))

        if track_key:
            (liked_tracks if vote else disliked_tracks)[track_key] += 1
        if artist_key:
            (liked_artists if vote else disliked_artists)[artist_key] += 1

    return SessionTasteProfile(
        session_id=session_id,
        liked_tracks=_top_keys(liked_tracks),
        disliked_tracks=_top_keys(disliked_tracks),
        liked_artists=_top_keys(liked_artists),
        disliked_artists=_top_keys(disliked_artists),
    )


def save_dig_history(
    request: DigRequest,
    recommendations: list[RecommendationCard],
    model_used: str | None,
    usage: OpenRouterUsage | None = None,
) -> None:
    if not request.session_id:
        return

    write_dig_history_record(build_dig_history_record(request, recommendations, model_used, usage))


def build_dig_history_record(
    request: DigRequest,
    recommendations: list[RecommendationCard],
    model_used: str | None,
    usage: OpenRouterUsage | None = None,
) -> dict[str, Any]:
    return {
        "session_id": request.session_id,
        "root_song": request.query,
        "params": {
            "distance_level": request.distance_level,
            "region": request.region,
            "era": request.era,
            "challenge_mode": request.challenge_mode,
            "mood_tags": request.mood_tags,
        },
        "model_used": model_used,
        "usage": usage.model_dump() if usage else None,
        "recommendations": [
            {
                "song_name": recommendation.title,
                "artist_name": recommendation.artist,
                "rarity_label": recommendation.rarity_label,
                "confidence": recommendation.confidence,
            }
            for recommendation in recommendations
        ],
        "created_at": datetime.now(UTC).isoformat(),
    }


def write_dig_history_record(record: dict[str, Any]) -> None:
    with _LOCK:
        _dig_history_path().parent.mkdir(parents=True, exist_ok=True)
        with _dig_history_path().open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_feedback_records() -> list[dict[str, Any]]:
    path = _feedback_path()
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with _LOCK:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _feedback_path() -> Path:
    return Path(get_settings().local_data_dir) / "feedback.jsonl"


def _dig_history_path() -> Path:
    return Path(get_settings().local_data_dir) / "dig_history.jsonl"


def _outbound_clicks_path() -> Path:
    return Path(get_settings().local_data_dir) / "outbound_clicks.jsonl"


def _track_key(artist: Any, song: Any) -> str:
    artist_text = str(artist or "").strip()
    song_text = str(song or "").strip()
    if not artist_text or not song_text:
        return ""
    return f"{artist_text} - {song_text}"


def _top_keys(counter: Counter[str], limit: int = 12) -> list[str]:
    return [item for item, _ in counter.most_common(limit)]

from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.main import app
from backend.app.middleware.rate_limit import InMemoryRateLimiter
from backend.app.schemas import CandidateTrack, DigResponse, TrackValidationResult, ValidateResponse
from backend.app.services.dig import _prepare_curation_candidates


client = TestClient(app)


def test_validate_returns_success(monkeypatch):
    async def fake_validate_track(query: str) -> ValidateResponse:
        return ValidateResponse(
            query=query,
            found=True,
            result=TrackValidationResult(
                source="deezer",
                title="Creep",
                artist="Radiohead",
                confidence=0.95,
            ),
            checked_sources=["deezer"],
        )

    monkeypatch.setattr("backend.app.routers.validate.validate_track", fake_validate_track)

    response = client.get("/validate", params={"query": "Radiohead Creep"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["found"] is True
    assert payload["result"]["title"] == "Creep"
    assert payload["checked_sources"] == ["deezer"]


def test_validate_rejects_short_query():
    response = client.get("/validate", params={"query": "x"})

    assert response.status_code == 422


def test_feedback_writes_local_fallback(tmp_path, monkeypatch):
    settings = get_settings()
    settings.local_data_dir = str(tmp_path)
    monkeypatch.setattr("backend.app.services.persistence.is_supabase_configured", lambda: False)

    response = client.post(
        "/feedback",
        json={
            "session_id": "test-session",
            "song_name": "Creep",
            "artist_name": "Radiohead",
            "vote": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["storage_backend"] == "local"
    assert (Path(tmp_path) / "feedback.jsonl").exists()


def test_dig_returns_recommendations(monkeypatch):
    async def fake_build_dig_response(request) -> DigResponse:
        return DigResponse(
            query=request.query,
            candidates=[],
            recommendations=[],
            next_step="ok",
        )

    monkeypatch.setattr("backend.app.routers.dig.build_dig_response", fake_build_dig_response)

    response = client.post("/dig", json={"query": "Radiohead Creep"})

    assert response.status_code == 200
    assert response.json()["query"] == "Radiohead Creep"


def test_dig_surfaces_service_errors(monkeypatch):
    async def fake_build_dig_response(request):
        raise HTTPException(status_code=503, detail="LASTFM_API_KEY is required.")

    monkeypatch.setattr("backend.app.routers.dig.build_dig_response", fake_build_dig_response)

    response = client.post("/dig", json={"query": "Radiohead Creep"})

    assert response.status_code == 503
    assert response.json()["detail"] == "LASTFM_API_KEY is required."


def test_in_memory_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter(window_seconds=60)

    assert limiter.allow("client:/dig", limit=2) == (True, 0)
    assert limiter.allow("client:/dig", limit=2) == (True, 0)

    allowed, retry_after = limiter.allow("client:/dig", limit=2)
    assert allowed is False
    assert retry_after > 0


def test_prepare_curation_candidates_filters_seed_and_root_artist_for_digging():
    candidates = [
        CandidateTrack(title="Creep", artist="Radiohead", source="test", rarity_score=0.1),
        CandidateTrack(title="No Surprises", artist="Radiohead", source="test", rarity_score=0.8),
        CandidateTrack(title="Song A", artist="Artist A", source="test", rarity_score=0.2),
        CandidateTrack(title="Song B", artist="Artist B", source="test", rarity_score=0.7),
        CandidateTrack(title="Song C", artist="Artist C", source="test", rarity_score=0.5),
        CandidateTrack(title="Song D", artist="Artist D", source="test", rarity_score=0.4),
        CandidateTrack(title="Song E", artist="Artist E", source="test", rarity_score=0.9),
        CandidateTrack(title="Song F", artist="Artist F", source="test", rarity_score=0.6),
        CandidateTrack(title="Song G", artist="Artist G", source="test", rarity_score=0.3),
        CandidateTrack(title="Song H", artist="Artist H", source="test", rarity_score=0.8),
    ]

    prepared = _prepare_curation_candidates(
        candidates,
        root_title="Creep",
        root_artist="Radiohead",
        distance_level=4,
        limit=8,
    )

    assert all(candidate.title != "Creep" for candidate in prepared)
    assert all(candidate.artist != "Radiohead" for candidate in prepared)
    assert prepared[0].rarity_score == 0.9

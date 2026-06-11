from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.main import app
from backend.app.middleware.rate_limit import InMemoryRateLimiter
from backend.app.schemas import DigResponse, TrackValidationResult, ValidateResponse


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

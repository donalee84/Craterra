from pathlib import Path

import anyio
from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx

from backend.app.clients.http import request_with_retries
from backend.app.config import get_settings
from backend.app.main import app
from backend.app.middleware.rate_limit import InMemoryRateLimiter
from backend.app.schemas import (
    CandidateTrack,
    DigRequest,
    DigResponse,
    OpenRouterUsage,
    TrackValidationResult,
    ValidateResponse,
)
from backend.app.clients.musicbrainz import _relationship_summary
from backend.app.services.local_store import build_dig_history_record
from backend.app.services.dig import (
    _artist_matches_root,
    _normalize_key,
    _prepare_curation_candidates,
    _text_close,
)


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
    assert payload["result"]["relationship_summary"] == []
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


def test_outbound_click_writes_local_fallback(tmp_path, monkeypatch):
    settings = get_settings()
    settings.local_data_dir = str(tmp_path)
    monkeypatch.setattr("backend.app.services.persistence.is_supabase_configured", lambda: False)

    response = client.post(
        "/outbound-click",
        json={
            "session_id": "test-session",
            "service": "bandcamp",
            "song_name": "Creep",
            "artist_name": "Radiohead",
            "url": "https://bandcamp.com/search?q=Radiohead+Creep",
        },
    )

    assert response.status_code == 200
    assert response.json()["storage_backend"] == "local"
    assert (Path(tmp_path) / "outbound_clicks.jsonl").exists()


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


def test_unhandled_errors_return_stable_payload(monkeypatch):
    error_client = TestClient(app, raise_server_exceptions=False)

    async def fake_build_dig_response(request):
        raise RuntimeError("upstream exploded")

    monkeypatch.setattr("backend.app.routers.dig.build_dig_response", fake_build_dig_response)

    response = error_client.post(
        "/dig",
        json={"query": "Radiohead Creep"},
        headers={"X-Request-ID": "test-request-id"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unexpected server error. Please try again shortly.",
        "request_id": "test-request-id",
    }
    assert response.headers["X-Request-ID"] == "test-request-id"


def test_successful_responses_include_request_id():
    response = client.get("/health", headers={"X-Request-ID": "health-request-id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "health-request-id"


def test_request_with_retries_retries_transient_status():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async def run_request() -> httpx.Response:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as test_client:
            return await request_with_retries(
                test_client,
                "GET",
                "https://example.test/resource",
                service="test",
                backoff_seconds=0,
            )

    response = anyio.run(run_request)

    assert response.status_code == 200
    assert attempts == 2


def test_dig_response_can_include_openrouter_usage(monkeypatch):
    async def fake_build_dig_response(request) -> DigResponse:
        return DigResponse(
            query=request.query,
            candidates=[],
            recommendations=[],
            model_used="test/model",
            usage=OpenRouterUsage(
                prompt_tokens=100,
                completion_tokens=20,
                total_tokens=120,
                cost=0.0012,
            ),
            next_step="ok",
        )

    monkeypatch.setattr("backend.app.routers.dig.build_dig_response", fake_build_dig_response)

    response = client.post("/dig", json={"query": "Radiohead Creep"})

    assert response.status_code == 200
    assert response.json()["usage"] == {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
        "cost": 0.0012,
    }


def test_dig_history_record_includes_usage():
    record = build_dig_history_record(
        DigRequest(query="Radiohead Creep", session_id="test-session"),
        recommendations=[],
        model_used="test/model",
        usage=OpenRouterUsage(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            cost=0.0012,
        ),
    )

    assert record["usage"] == {
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
        "cost": 0.0012,
    }


def test_musicbrainz_relationship_summary_formats_recording_and_work_relations():
    recording = {
        "relations": [
            {
                "type": "producer",
                "artist": {"name": "Nigel Godrich"},
            }
        ],
        "works": [
            {
                "title": "Creep",
                "relations": [
                    {
                        "type": "composer",
                        "artist": {"name": "Radiohead"},
                        "attributes": ["music"],
                    }
                ],
            }
        ],
    }

    assert _relationship_summary(recording) == [
        "producer: Nigel Godrich",
        "work: Creep",
        "composer: Radiohead (music)",
    ]


def test_in_memory_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter(window_seconds=60)

    assert limiter.allow("client:/dig", limit=2) == (True, 0)
    assert limiter.allow("client:/dig", limit=2) == (True, 0)

    allowed, retry_after = limiter.allow("client:/dig", limit=2)
    assert allowed is False
    assert retry_after > 0


def test_in_memory_rate_limiter_evicts_idle_clients():
    from time import monotonic

    limiter = InMemoryRateLimiter(window_seconds=60)

    limiter.allow("one:/dig", limit=5)
    limiter.allow("two:/dig", limit=5)
    assert len(limiter._requests) == 2

    # Make both clients look idle beyond the window and force the next call
    # past the sweep interval; idle buckets should be evicted so the map stays
    # bounded to the active client instead of growing once per unique IP.
    stale_time = monotonic() - 61
    limiter._requests["one:/dig"][0] = stale_time
    limiter._requests["two:/dig"][0] = stale_time
    limiter._last_sweep = stale_time

    limiter.allow("three:/dig", limit=5)
    assert set(limiter._requests) == {"three:/dig"}


def test_text_close_accepts_real_matches_and_rejects_loose_hits():
    # Accent/suffix/feat variations should still count as the same track.
    assert _text_close("L’indécis", "L'indecis")
    assert _text_close("The Less I Know the Better", "The Less I Know the Better - Remastered")
    assert _text_close("Tame Impala", "Tame Impala feat. Someone")
    # Loose keyword hits from validation search must be rejected.
    assert not _text_close("Zxqwv Nonexistent Track", "Keep The Fate")
    assert not _text_close("asdkjfh qweuriou", "Montechiari Project")


def test_artist_matches_root_handles_collabs_and_accents():
    # Deezer "L'indecis" (straight quote, no accent) must match Last.fm
    # "L'indécis" (curly quote, accent) and collaborations including it.
    root = _normalize_key("L'indecis")
    assert _artist_matches_root("L’indécis", root)
    assert _artist_matches_root("Ghostnaut & L’indécis", root)
    assert _artist_matches_root("Pandrezz, j'san & L’indécis feat. Epektase", root)
    assert not _artist_matches_root("Kreatev", root)
    assert not _artist_matches_root("El Train", root)


def test_prepare_curation_candidates_drops_filler_tracks():
    candidates = [
        CandidateTrack(title="Intro", artist="Artist A", source="test", rarity_score=0.9),
        CandidateTrack(title="Album Interlude", artist="Artist B", source="test", rarity_score=0.9),
        CandidateTrack(title="Skit", artist="Artist C", source="test", rarity_score=0.9),
        CandidateTrack(title="Introspection", artist="Artist D", source="test", rarity_score=0.9),
        *[
            CandidateTrack(title=f"Real Song {i}", artist=f"Band {i}", source="test", rarity_score=0.5)
            for i in range(8)
        ],
    ]

    prepared = _prepare_curation_candidates(
        candidates,
        root_title=None,
        root_artist=None,
        distance_level=1,
        limit=18,
    )

    titles = [candidate.title for candidate in prepared]
    assert "Intro" not in titles
    assert "Album Interlude" not in titles
    assert "Skit" not in titles
    assert "Introspection" in titles  # substring "intro" must not trigger the filter
    assert len(prepared) == 9


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

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from backend.app.clients.http import api_client
from backend.app.config import get_settings
from backend.app.schemas import CandidateTrack, CuratedPick, DigRequest, SessionTasteProfile

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterNotConfiguredError(RuntimeError):
    pass


class OpenRouterCurationError(RuntimeError):
    pass


class CurationPayload(BaseModel):
    picks: list[CuratedPick] = Field(min_length=1, max_length=5)


async def curate_candidates(
    request: DigRequest,
    candidates: list[CandidateTrack],
    session_profile: SessionTasteProfile | None = None,
) -> tuple[list[CuratedPick], str]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise OpenRouterNotConfiguredError("OPENROUTER_API_KEY is not configured.")

    errors: list[str] = []
    for model in (settings.openrouter_model, settings.openrouter_fallback_model):
        try:
            picks = await _request_curation(
                api_key=settings.openrouter_api_key,
                model=model,
                request=request,
                candidates=candidates,
                session_profile=session_profile,
            )
            return picks, model
        except OpenRouterCurationError as exc:
            errors.append(f"{model}: {exc}")

    raise OpenRouterCurationError("; ".join(errors) or "No model returned valid picks.")


async def _request_curation(
    api_key: str,
    model: str,
    request: DigRequest,
    candidates: list[CandidateTrack],
    session_profile: SessionTasteProfile | None,
) -> list[CuratedPick]:
    try:
        async with api_client() as client:
            response = await client.post(
                OPENROUTER_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-Title": "Craterra",
                },
                json=_build_payload(
                    model=model,
                    request=request,
                    candidates=candidates,
                    session_profile=session_profile,
                ),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpenRouterCurationError(str(exc)) from exc

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterCurationError("Unexpected OpenRouter response shape.") from exc

    try:
        payload = CurationPayload.model_validate_json(content)
    except ValidationError:
        try:
            payload = CurationPayload.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise OpenRouterCurationError("Model did not return valid curation JSON.") from exc

    valid_indexes = set(range(len(candidates)))
    picks = [pick for pick in payload.picks if pick.candidate_index in valid_indexes]
    if not picks:
        raise OpenRouterCurationError("Model returned no usable candidate indexes.")

    return picks[:5]


def _build_payload(
    model: str,
    request: DigRequest,
    candidates: list[CandidateTrack],
    session_profile: SessionTasteProfile | None,
) -> dict[str, Any]:
    curation_guidance = _curation_guidance(request)
    candidate_lines = "\n".join(
        (
            f"{index}. {candidate.artist} - {candidate.title} "
            f"(source={candidate.source}, match={candidate.match_score}, "
            f"listeners={candidate.listeners}, playcount={candidate.playcount}, "
            f"rarity_score={candidate.rarity_score}, rarity_label={candidate.rarity_label})"
        )
        for index, candidate in enumerate(candidates)
    )

    user_context = {
        "query": request.query,
        "distance_level": request.distance_level,
        "region": request.region,
        "era": request.era,
        "challenge_mode": request.challenge_mode,
        "mood_tags": request.mood_tags,
        "session_profile": (
            session_profile.model_dump(exclude={"session_id"}) if session_profile else None
        ),
    }

    return {
        "model": model,
        "temperature": 0.55,
        "max_tokens": 900,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "craterra_curation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "picks": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 5,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "candidate_index": {"type": "integer", "minimum": 0},
                                    "reason": {
                                        "type": "string",
                                        "minLength": 8,
                                        "maxLength": 500,
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
                                },
                                "required": ["candidate_index", "reason", "confidence"],
                            },
                        }
                    },
                    "required": ["picks"],
                },
            },
        },
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Craterra, a music digging curator. Select 3 to 5 tracks "
                    "only from the provided candidate list. Prefer less obvious tracks "
                    "with higher rarity_score when the musical bridge is still clear, "
                    "clear musical bridges, and concise reasons. Avoid disliked session "
                    "patterns and lean into liked session patterns when they are present. "
                    "Never invent songs. Do not mention internal scores or APIs."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User context JSON:\n{json.dumps(user_context, ensure_ascii=False)}\n\n"
                    f"Curation guidance:\n{curation_guidance}\n\n"
                    f"Candidate tracks:\n{candidate_lines}\n\n"
                    "Return JSON only."
                ),
            },
        ],
    }


def _curation_guidance(request: DigRequest) -> str:
    distance_notes = {
        1: "Stay close to the root song: same artist, scene, era, or immediately adjacent sound.",
        2: "Make a modest jump: similar mood or genre, but avoid the most obvious hit when possible.",
        3: "Balance familiarity and discovery: a clear bridge plus at least one less obvious pick.",
        4: "Prefer bolder bridges: adjacent genres, era jumps, regional parallels, or deeper catalog cuts.",
        5: "Make adventurous but defensible jumps: prioritize surprising links with strong reasons.",
    }
    notes = [distance_notes.get(request.distance_level, distance_notes[3])]

    if request.challenge_mode:
        notes.append(
            "Challenge mode is on: do not simply mirror the user's taste; choose tracks that stretch it."
        )
    if request.region:
        notes.append(f"Use the region preference when candidates allow it: {request.region}.")
    if request.era:
        notes.append(f"Use the era preference when candidates allow it: {request.era}.")
    if request.mood_tags:
        notes.append(f"Respect these mood tags: {', '.join(request.mood_tags)}.")

    return "\n".join(f"- {note}" for note in notes)

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


ValidationSource = Literal["deezer", "musicbrainz", "itunes"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: str


class TrackValidationResult(BaseModel):
    source: ValidationSource
    title: str
    artist: str
    album: str | None = None
    release_date: str | None = None
    artwork_url: HttpUrl | None = None
    preview_url: HttpUrl | None = None
    external_url: HttpUrl | None = None
    relationship_summary: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class ValidateResponse(BaseModel):
    query: str
    found: bool
    result: TrackValidationResult | None = None
    checked_sources: list[ValidationSource]


class DigRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    artist: str | None = Field(default=None, max_length=200)
    distance_level: int = Field(default=3, ge=1, le=5)
    region: str | None = Field(default=None, max_length=20)
    challenge_mode: bool = False
    mood_tags: list[str] = Field(default_factory=list, max_length=8)
    session_id: str | None = Field(default=None, max_length=120)


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    song_name: str = Field(min_length=1, max_length=200)
    artist_name: str = Field(min_length=1, max_length=200)
    vote: bool


class FeedbackResponse(BaseModel):
    saved: bool
    session_id: str
    storage_backend: Literal["local", "supabase"] = "local"


class OutboundClickRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    service: Literal["bandcamp", "apple_music", "youtube"]
    song_name: str = Field(min_length=1, max_length=200)
    artist_name: str = Field(min_length=1, max_length=200)
    url: HttpUrl


class OutboundClickResponse(BaseModel):
    saved: bool
    storage_backend: Literal["local", "supabase"] = "local"


class SessionTasteProfile(BaseModel):
    session_id: str
    liked_tracks: list[str] = Field(default_factory=list)
    disliked_tracks: list[str] = Field(default_factory=list)
    liked_artists: list[str] = Field(default_factory=list)
    disliked_artists: list[str] = Field(default_factory=list)


class CandidateTrack(BaseModel):
    title: str
    artist: str
    source: str
    match_score: float | None = Field(default=None, ge=0.0, le=1.0)
    listeners: int | None = Field(default=None, ge=0)
    playcount: int | None = Field(default=None, ge=0)
    rarity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rarity_label: str | None = None
    external_url: HttpUrl | None = None


class CuratedPick(BaseModel):
    candidate_index: int = Field(ge=0)
    reason: str = Field(min_length=8, max_length=500)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)


class OpenRouterUsage(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0.0)


class OutboundLink(BaseModel):
    service: Literal["bandcamp", "apple_music", "youtube"]
    label: str
    url: HttpUrl


class RecommendationCard(BaseModel):
    title: str
    artist: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    rarity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rarity_label: str | None = None
    candidate_source: str
    validation: TrackValidationResult | None = None
    checked_sources: list[ValidationSource] = Field(default_factory=list)
    outbound_links: list[OutboundLink] = Field(default_factory=list)


class DigResponse(BaseModel):
    query: str
    candidates: list[CandidateTrack]
    recommendations: list[RecommendationCard] = Field(default_factory=list)
    model_used: str | None = None
    usage: OpenRouterUsage | None = None
    next_step: str

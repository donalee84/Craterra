from fastapi import APIRouter, Query

from backend.app.schemas import ValidateResponse
from backend.app.services.validation import validate_track

router = APIRouter(tags=["validation"])


@router.get("/validate", response_model=ValidateResponse)
async def validate(query: str = Query(min_length=2, max_length=200)) -> ValidateResponse:
    return await validate_track(query)


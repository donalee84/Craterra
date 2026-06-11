from fastapi import APIRouter

from backend.app.schemas import DigRequest, DigResponse
from backend.app.services.dig import build_dig_response

router = APIRouter(tags=["dig"])


@router.post("/dig", response_model=DigResponse)
async def dig(request: DigRequest) -> DigResponse:
    return await build_dig_response(request)

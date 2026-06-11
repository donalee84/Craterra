from fastapi import APIRouter

from backend.app.schemas import FeedbackRequest, FeedbackResponse
from backend.app.services.persistence import save_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest) -> FeedbackResponse:
    return await save_feedback(request)

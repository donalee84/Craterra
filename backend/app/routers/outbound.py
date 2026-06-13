from fastapi import APIRouter

from backend.app.schemas import OutboundClickRequest, OutboundClickResponse
from backend.app.services.persistence import save_outbound_click

router = APIRouter(tags=["outbound"])


@router.post("/outbound-click", response_model=OutboundClickResponse)
async def outbound_click(request: OutboundClickRequest) -> OutboundClickResponse:
    return await save_outbound_click(request)

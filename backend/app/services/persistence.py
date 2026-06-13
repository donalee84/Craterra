from backend.app.clients.supabase import (
    SupabasePersistenceError,
    fetch_feedback,
    insert_dig_history,
    insert_feedback,
    insert_outbound_click,
    is_supabase_configured,
)
from backend.app.schemas import (
    DigRequest,
    FeedbackRequest,
    FeedbackResponse,
    OpenRouterUsage,
    OutboundClickRequest,
    OutboundClickResponse,
    RecommendationCard,
    SessionTasteProfile,
)
from backend.app.services import local_store


async def save_feedback(request: FeedbackRequest) -> FeedbackResponse:
    record = local_store.build_feedback_record(request)
    storage_backend = "local"

    if is_supabase_configured():
        try:
            await insert_feedback(record)
            storage_backend = "supabase"
        except SupabasePersistenceError:
            local_store.write_feedback_record(record)
    else:
        local_store.write_feedback_record(record)

    return FeedbackResponse(
        saved=True,
        session_id=request.session_id,
        storage_backend=storage_backend,
    )


async def get_session_profile(session_id: str | None) -> SessionTasteProfile | None:
    if not session_id:
        return None

    if is_supabase_configured():
        try:
            return local_store.build_session_profile(session_id, await fetch_feedback(session_id))
        except SupabasePersistenceError:
            pass

    return local_store.get_session_profile(session_id)


async def save_outbound_click(request: OutboundClickRequest) -> OutboundClickResponse:
    record = local_store.build_outbound_click_record(request)
    storage_backend = "local"

    if is_supabase_configured():
        try:
            await insert_outbound_click(record)
            storage_backend = "supabase"
        except SupabasePersistenceError:
            local_store.write_outbound_click_record(record)
    else:
        local_store.write_outbound_click_record(record)

    return OutboundClickResponse(saved=True, storage_backend=storage_backend)


async def save_dig_history(
    request: DigRequest,
    recommendations: list[RecommendationCard],
    model_used: str | None,
    usage: OpenRouterUsage | None = None,
) -> None:
    if not request.session_id:
        return

    record = local_store.build_dig_history_record(request, recommendations, model_used, usage)

    if is_supabase_configured():
        try:
            await insert_dig_history(record)
            return
        except SupabasePersistenceError:
            pass

    local_store.write_dig_history_record(record)

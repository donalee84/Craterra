from typing import Any

import httpx

from backend.app.config import get_settings


class SupabaseNotConfiguredError(RuntimeError):
    pass


class SupabasePersistenceError(RuntimeError):
    pass


def is_supabase_configured() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_service_role_key)


async def insert_feedback(record: dict[str, Any]) -> None:
    await _insert("feedback", record)


async def insert_dig_history(record: dict[str, Any]) -> None:
    await _insert("dig_history", record)


async def insert_outbound_click(record: dict[str, Any]) -> None:
    await _insert("outbound_clicks", record)


async def fetch_feedback(session_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = _table_url("feedback")
    params = {
        "session_id": f"eq.{session_id}",
        "select": "session_id,song_name,artist_name,vote,created_at",
        "order": "created_at.desc",
        "limit": "250",
    }

    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True) as client:
        response = await client.get(url, headers=_headers(), params=params)

    if response.status_code >= 400:
        raise SupabasePersistenceError(response.text)

    payload = response.json()
    if not isinstance(payload, list):
        raise SupabasePersistenceError("Unexpected Supabase feedback payload.")
    return payload


async def _insert(table: str, record: dict[str, Any]) -> None:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True) as client:
        response = await client.post(
            _table_url(table),
            headers={**_headers(), "Prefer": "return=minimal"},
            json=record,
        )

    if response.status_code >= 400:
        raise SupabasePersistenceError(response.text)


def _table_url(table: str) -> str:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SupabaseNotConfiguredError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}"


def _headers() -> dict[str, str]:
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise SupabaseNotConfiguredError("SUPABASE_SERVICE_ROLE_KEY is required.")
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }

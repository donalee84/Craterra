from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from backend.app.config import get_settings


@asynccontextmanager
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        yield client


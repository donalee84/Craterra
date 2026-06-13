from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import asyncio
import logging

import httpx

from backend.app.config import get_settings

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


@asynccontextmanager
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        yield client


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    service: str,
    max_attempts: int = 2,
    backoff_seconds: float = 0.25,
    **kwargs,
) -> httpx.Response:
    logger = logging.getLogger("craterra.external_api")

    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            if attempt >= max_attempts:
                logger.warning(
                    "external_api_failed",
                    extra={
                        "service": service,
                        "method": method.upper(),
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                raise

            logger.warning(
                "external_api_retry",
                extra={
                    "service": service,
                    "method": method.upper(),
                    "attempt": attempt,
                    "error": str(exc),
                    "backoff_seconds": backoff_seconds,
                },
            )
            await asyncio.sleep(backoff_seconds)
            continue

        if response.status_code in TRANSIENT_STATUS_CODES and attempt < max_attempts:
            logger.warning(
                "external_api_retry",
                extra={
                    "service": service,
                    "method": method.upper(),
                    "attempt": attempt,
                    "status_code": response.status_code,
                    "backoff_seconds": backoff_seconds,
                },
            )
            await asyncio.sleep(backoff_seconds)
            continue

        if response.status_code >= 400:
            logger.warning(
                "external_api_error",
                extra={
                    "service": service,
                    "method": method.upper(),
                    "attempt": attempt,
                    "status_code": response.status_code,
                },
            )

        return response

    raise RuntimeError("request retry loop ended unexpectedly")

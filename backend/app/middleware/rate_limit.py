from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from backend.app.config import get_settings


@dataclass(frozen=True)
class RateLimitRule:
    path: str
    limit: int


class InMemoryRateLimiter:
    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int) -> tuple[bool, int]:
        now = monotonic()
        with self._lock:
            bucket = self._requests[key]
            while bucket and now - bucket[0] >= self.window_seconds:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, round(self.window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.limiter = InMemoryRateLimiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        rule = _rule_for_path(request.url.path)
        if rule is None:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{rule.path}"
        allowed, retry_after = self.limiter.allow(key, rule.limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down and try again shortly.",
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


def _rule_for_path(path: str) -> RateLimitRule | None:
    settings = get_settings()
    rules = {
        "/validate": settings.validate_rate_limit_per_minute,
        "/feedback": settings.feedback_rate_limit_per_minute,
        "/dig": settings.dig_rate_limit_per_minute,
        "/outbound-click": settings.outbound_click_rate_limit_per_minute,
    }
    limit = rules.get(path)
    if limit is None or limit <= 0:
        return None
    return RateLimitRule(path=path, limit=limit)

import json
import logging
import sys
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.app.config import get_settings

LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": get_settings().app_env,
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in LOG_RECORD_FIELDS and not key.startswith("_")
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        root_logger.addHandler(handler)

    for handler in root_logger.handlers:
        handler.setFormatter(JsonFormatter())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logging.getLogger("craterra.request").info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code if response else 500,
                    "duration_ms": duration_ms,
                    "client_host": request.client.host if request.client else "unknown",
                },
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id

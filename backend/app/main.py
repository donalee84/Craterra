import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import get_settings
from backend.app.middleware.rate_limit import RateLimitMiddleware
from backend.app.observability import RequestLoggingMiddleware, configure_logging
from backend.app.routers.dig import router as dig_router
from backend.app.routers.feedback import router as feedback_router
from backend.app.routers.validate import router as validate_router
from backend.app.schemas import HealthResponse

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Music discovery backend for Craterra.",
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.app_env)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logging.getLogger("craterra.error").exception(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Unexpected server error. Please try again shortly.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )


app.include_router(validate_router)
app.include_router(dig_router)
app.include_router(feedback_router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")

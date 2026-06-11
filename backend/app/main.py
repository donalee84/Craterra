from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import get_settings
from backend.app.middleware.rate_limit import RateLimitMiddleware
from backend.app.routers.dig import router as dig_router
from backend.app.routers.feedback import router as feedback_router
from backend.app.routers.validate import router as validate_router
from backend.app.schemas import HealthResponse

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Music discovery backend for Craterra.",
)
app.add_middleware(RateLimitMiddleware)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.app_env)


app.include_router(validate_router)
app.include_router(dig_router)
app.include_router(feedback_router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")

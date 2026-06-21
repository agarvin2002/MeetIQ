from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from meetiq.api.middleware.correlation import CorrelationMiddleware
from meetiq.api.routers import auth, meetings
from meetiq.config.settings import settings
from meetiq.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    setup_logging(settings.log_level)
    logger.info("meetiq_startup", env=settings.log_level)
    yield
    logger.info("meetiq_shutdown")


app = FastAPI(
    title="MeetIQ API",
    description="Meeting Intelligence Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost runs first) ──────────────────────

# 1. Sessions: stores user tokens server-side, sends session cookie to browser
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="none",   # required for cross-origin cookies (Vercel → Render)
    https_only=True,    # SameSite=None requires Secure flag
)

# 2. CORS: allows the frontend (different port) to call our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,   # needed so session cookies are sent cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Correlation: generates trace_id per request, injects into all log lines
app.add_middleware(CorrelationMiddleware)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(meetings.router, prefix="/meetings", tags=["meetings"])


@app.get("/health")
async def health():
    """Health check endpoint — used by Render to verify the app is alive."""
    return {"status": "ok"}

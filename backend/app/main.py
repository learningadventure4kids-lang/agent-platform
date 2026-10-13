"""FastAPI application entrypoint.

CORS is deliberately split in two:

- The **admin dashboard** APIs (`/api/admin/*`) use a strict origin
  allow-list (`CORS_ALLOWED_ORIGINS`) via the standard CORSMiddleware --
  this is where `allow_origins=["*"]` would be a real problem, since these
  endpoints manage tenant configuration.
- The **public widget** APIs (`/api/chat`, `/api/session/*`) are meant to
  be called from arbitrary third-party websites (that's the whole point of
  an embeddable widget), so they echo back the request's Origin rather
  than using a fixed list. This is safe specifically because these
  endpoints authenticate via an explicit `agent_token` in the request body
  (not cookies/browser credentials), so there is no ambient-authority
  attack for a permissive Origin to enable. Domain restriction, where an
  agent wants it, is enforced separately and server-side by
  `app/security/domains.py`, which a permissive CORS header cannot bypass.
"""
from __future__ import annotations

import logging

from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import (
    admin_agents,
    admin_auth,
    admin_customers,
    admin_providers,
    admin_sessions,
    admin_tools,
    admin_users,
    builder,
    chat,
    knowledge,
    leads,
    sessions,
    user_auth,
)
from app.config import get_settings
from app.database.connection import check_db_connection, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_platform")

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

PUBLIC_WIDGET_PREFIXES = ("/api/chat", "/api/session")


class PublicWidgetCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        is_public_path = request.url.path.startswith(PUBLIC_WIDGET_PREFIXES)

        if request.method == "OPTIONS" and is_public_path:
            response = JSONResponse(content={})
        else:
            response = await call_next(request)

        if is_public_path and origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Vary"] = "Origin"
        return response


app.add_middleware(PublicWidgetCORSMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(admin_auth.router)
app.include_router(admin_agents.router)
app.include_router(admin_tools.router)
app.include_router(admin_providers.router)
app.include_router(admin_sessions.router)
app.include_router(admin_customers.router)
app.include_router(admin_users.router)
app.include_router(knowledge.router)
app.include_router(leads.router)
app.include_router(user_auth.router)
app.include_router(builder.router)

# Serves the pre-built embeddable widget bundle (`widget/dist/aria-widget.js`,
# copied in at `app/static/aria-widget.js`) so the self-serve builder's
# generated <script> tag (PUBLIC_WIDGET_SCRIPT_URL, default
# http://localhost:8000/static/aria-widget.js) resolves out of the box in
# local/dev environments. In production, point PUBLIC_WIDGET_SCRIPT_URL at a
# CDN copy instead (see README "Embedding the React widget") and this mount
# is unused -- it is not meant to be the production hosting path.
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database ready at %s", settings.DATABASE_URL)
    if settings.SEED_DEMO_DATA:
        from app.seed import seed_demo_data

        seed_demo_data()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our end. Please try again in a moment."},
    )


def _check_ollama() -> tuple[str, bool]:
    try:
        resp = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        resp.raise_for_status()
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        model_present = any(
            settings.OLLAMA_MODEL == m or m.startswith(settings.OLLAMA_MODEL.split(":")[0])
            for m in models
        )
        return ("connected" if model_present else "connected_model_missing"), model_present
    except Exception:
        return "unavailable", False


@app.get("/api/health")
def health():
    db_ok = check_db_connection()
    ollama_status, ollama_ok = _check_ollama()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "ollama": ollama_status,
        "ollama_available": ollama_ok,
        "model": settings.OLLAMA_MODEL,
    }


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "docs": "/docs", "health": "/api/health"}

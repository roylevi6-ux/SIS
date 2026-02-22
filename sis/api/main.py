"""FastAPI application entry point for SIS API."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import APIError, api_error_handler, value_error_handler

app = FastAPI(title="SIS API", version="2.0.0")

# ── Error handlers ────────────────────────────────────────────────────

app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(APIError, api_error_handler)

# ── CORS middleware ───────────────────────────────────────────────────

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────


@app.get("/api/health")
def health_check() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": "2.0.0"}


# ── Route registration ───────────────────────────────────────────────

from sis.api.routes import (  # noqa: E402
    accounts,
    analyses,
    dashboard,
    transcripts,
    feedback,
    calibration,
    admin,
    export,
    chat,
    sse,
)

app.include_router(accounts.router)
app.include_router(analyses.router)
app.include_router(dashboard.router)
app.include_router(transcripts.router)
app.include_router(feedback.router)
app.include_router(calibration.router)
app.include_router(admin.router)
app.include_router(export.router)
app.include_router(chat.router)
app.include_router(sse.router)

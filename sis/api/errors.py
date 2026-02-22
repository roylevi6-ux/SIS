"""Global error handlers for the SIS API."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Application-level error with HTTP status code."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Convert ValueError to 422 Unprocessable Entity."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Convert APIError to its declared status code."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

"""FastAPI dependency injection providers."""

from __future__ import annotations

from typing import Generator, Optional

from fastapi import Header
from sqlalchemy.orm import Session

from sis.db.session import get_session


def get_db() -> Generator[Session, None, None]:
    """Yield a transactional DB session, auto-closing on exit."""
    with get_session() as session:
        yield session


# ── Authentication dependencies ──────────────────────────────────────


def get_current_user(authorization: str = Header(...)) -> dict:
    """Extract and validate JWT from the Authorization header.

    Requires a valid ``Authorization: Bearer <token>`` header.
    Returns dict with keys ``sub`` (username) and ``role``.

    Raises:
        HTTPException 401 if header is missing, malformed, or token is invalid.
    """
    from fastapi import HTTPException

    from sis.api.auth import decode_token

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[len("Bearer "):]
    try:
        return decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """Optionally extract user from JWT if Authorization header is present.

    Returns user dict if a valid token is provided, None otherwise.
    Never raises — invalid/missing tokens silently return None.
    This is the default dependency for most routes so existing tests
    (which send no Authorization header) continue to pass.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        return None

    from sis.api.auth import decode_token

    token = authorization[len("Bearer "):]
    try:
        return decode_token(token)
    except ValueError:
        return None

"""FastAPI dependency injection providers."""

from __future__ import annotations

from typing import Generator, Optional

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from sis.db.session import get_session
from sis.db.models import User
from sis.services.scoping_service import get_visible_user_ids

# Role hierarchy for authorization checks (higher rank = more privileges)
_ROLE_RANK = {"ic": 0, "team_lead": 1, "vp": 2, "gm": 3, "admin": 4}


def require_role(user: dict, min_role: str) -> None:
    """Raise 403 if user's role is below the required minimum.

    Args:
        user: JWT payload dict with ``role`` key.
        min_role: Minimum role needed (e.g. "admin", "team_lead").
    """
    user_rank = _ROLE_RANK.get(user.get("role", ""), -1)
    required_rank = _ROLE_RANK.get(min_role, 99)
    if user_rank < required_rank:
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient permissions — requires {min_role} or above",
        )


def resolve_scoping(user: dict, db: Session) -> Optional[set[str]]:
    """Compute visible user IDs from JWT user dict. None = no restriction.

    Used by route handlers that need to scope queries to the requesting
    user's visibility (IC sees own deals, TL sees team, admin/GM see all).
    """
    user_id = user.get("user_id") if user else None
    if not user_id:
        return None
    db_user = db.query(User).filter_by(id=user_id).first()
    if not db_user or db_user.role in ("admin", "gm"):
        return None
    return get_visible_user_ids(db_user, db)


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

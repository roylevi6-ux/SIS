"""Authentication routes for SIS API.

POC login — accepts username + role, returns a JWT.
No password verification: this will be replaced by Salesforce SSO OAuth flow.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sis.api.auth import VALID_ROLES, create_token
from sis.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """POC login request — no password, SF SSO will replace this."""

    username: str = Field(..., min_length=1, max_length=100, description="User display name")
    role: str = Field(..., description="One of: admin, gm, vp, team_lead, ic")


class LoginResponse(BaseModel):
    """JWT token response."""

    token: str
    username: str
    role: str
    user_id: Optional[str] = None


class MeResponse(BaseModel):
    """Current user info extracted from JWT."""

    username: str
    role: str
    user_id: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    """Issue a JWT token for the given username and role.

    POC: No password check — will be replaced by SF SSO callback.
    """
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{body.role}'. Must be one of: {sorted(VALID_ROLES)}",
        )

    # For POC: find or create User record
    from sis.db.session import get_session
    from sis.db.models import User

    user_id = None
    try:
        with get_session() as session:
            user = session.query(User).filter_by(email=body.username).first()
            if not user:
                user = User(name=body.username, email=body.username, role=body.role)
                session.add(user)
                session.flush()
            user_id = user.id
    except Exception:
        # If DB is not available (e.g., in tests without mock), proceed without user_id
        pass

    token = create_token(body.username, body.role, user_id=user_id)
    return LoginResponse(token=token, username=body.username, role=body.role, user_id=user_id)


@router.get("/me", response_model=MeResponse)
def get_me(user: dict = Depends(get_current_user)) -> MeResponse:
    """Return current user info from JWT. Requires authentication."""
    return MeResponse(username=user["sub"], role=user["role"], user_id=user.get("user_id"))

"""Authentication routes for SIS API.

POC login — accepts username + role, returns a JWT.
No password verification: this will be replaced by Salesforce SSO OAuth flow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sis.api.auth import VALID_ROLES, create_token
from sis.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """POC login request — no password, SF SSO will replace this."""

    username: str = Field(..., min_length=1, max_length=100, description="User display name")
    role: str = Field(..., description="One of: admin, team_lead, ic")


class LoginResponse(BaseModel):
    """JWT token response."""

    token: str
    username: str
    role: str


class MeResponse(BaseModel):
    """Current user info extracted from JWT."""

    username: str
    role: str


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

    token = create_token(body.username, body.role)
    return LoginResponse(token=token, username=body.username, role=body.role)


@router.get("/me", response_model=MeResponse)
def get_me(user: dict = Depends(get_current_user)) -> MeResponse:
    """Return current user info from JWT. Requires authentication."""
    return MeResponse(username=user["sub"], role=user["role"])

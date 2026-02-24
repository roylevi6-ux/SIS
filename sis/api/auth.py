"""JWT authentication utilities for SIS API.

POC-grade auth layer — prepared for Salesforce SSO replacement.
Currently uses simple username/role tokens with no password verification.

When SF SSO is integrated, replace `create_token` with SF OAuth token exchange
and `decode_token` with SF token introspection or keep JWT as a session token
issued after SF OAuth callback.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError

# ── Configuration ────────────────────────────────────────────────────

_DEFAULT_SECRET = "sis-dev-secret-change-me"
JWT_SECRET: str = os.getenv("JWT_SECRET", _DEFAULT_SECRET)
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_HOURS: int = 24

# Block startup with the default secret in production
_environment = os.getenv("ENVIRONMENT", "development")
if JWT_SECRET == _DEFAULT_SECRET and _environment == "production":
    raise RuntimeError(
        "JWT_SECRET must be set to a secure random value in production. "
        "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

# Valid roles for POC (will map to SF permission sets later)
VALID_ROLES = {"admin", "gm", "vp", "team_lead", "ic"}


# ── Token helpers ────────────────────────────────────────────────────


def create_token(username: str, role: str, user_id: Optional[str] = None) -> str:
    """Create a signed JWT for the given user.

    Args:
        username: Display name / identifier (e.g. "AE One").
        role: One of "admin", "gm", "vp", "team_lead", "ic".
        user_id: Optional DB user ID to embed in the token.

    Returns:
        Encoded JWT string.

    Raises:
        ValueError: If role is not in VALID_ROLES.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "user_id": user_id,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: Encoded JWT string.

    Returns:
        Dict with keys "sub" (username) and "role".

    Raises:
        ValueError: If token is invalid, expired, or missing required claims.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc

    sub: Optional[str] = payload.get("sub")
    role: Optional[str] = payload.get("role")

    if not sub:
        raise ValueError("Token missing 'sub' claim")
    if not role or role not in VALID_ROLES:
        raise ValueError(f"Token has invalid role: {role}")

    return {"sub": sub, "role": role, "user_id": payload.get("user_id")}

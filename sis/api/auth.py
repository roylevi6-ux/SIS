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

from jose import JWTError, jwt

# ── Configuration ────────────────────────────────────────────────────

JWT_SECRET: str = os.getenv("JWT_SECRET", "sis-dev-secret-change-me")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_HOURS: int = 24

# Valid roles for POC (will map to SF permission sets later)
VALID_ROLES = {"admin", "team_lead", "ic"}


# ── Token helpers ────────────────────────────────────────────────────


def create_token(username: str, role: str) -> str:
    """Create a signed JWT for the given user.

    Args:
        username: Display name / identifier (e.g. "AE One").
        role: One of "admin", "team_lead", "ic".

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
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc

    sub: Optional[str] = payload.get("sub")
    role: Optional[str] = payload.get("role")

    if not sub:
        raise ValueError("Token missing 'sub' claim")
    if not role or role not in VALID_ROLES:
        raise ValueError(f"Token has invalid role: {role}")

    return {"sub": sub, "role": role}

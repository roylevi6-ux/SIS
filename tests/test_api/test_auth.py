"""Tests for the /api/auth endpoints and JWT utilities."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from sis.api.auth import JWT_SECRET, create_token, decode_token, VALID_ROLES


# ── Unit tests: token creation / decoding ────────────────────────────


class TestCreateToken:
    """Tests for create_token()."""

    def test_creates_valid_token(self):
        token = create_token("alice", "admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_roundtrip(self):
        token = create_token("bob", "team_lead")
        payload = decode_token(token)
        assert payload["sub"] == "bob"
        assert payload["role"] == "team_lead"

    def test_all_valid_roles(self):
        for role in VALID_ROLES:
            token = create_token("user", role)
            payload = decode_token(token)
            assert payload["role"] == role

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError, match="Invalid role"):
            create_token("alice", "superadmin")


class TestDecodeToken:
    """Tests for decode_token()."""

    def test_invalid_token_string(self):
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("not-a-real-token")

    def test_expired_token(self):
        from jose import jwt
        import datetime

        payload = {
            "sub": "alice",
            "role": "admin",
            "exp": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
            "iat": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
        }
        expired = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(expired)

    def test_missing_sub_claim(self):
        from jose import jwt
        import datetime

        payload = {
            "role": "admin",
            "exp": datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        with pytest.raises(ValueError, match="missing 'sub'"):
            decode_token(token)

    def test_invalid_role_in_token(self):
        from jose import jwt
        import datetime

        payload = {
            "sub": "alice",
            "role": "hacker",
            "exp": datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        with pytest.raises(ValueError, match="invalid role"):
            decode_token(token)

    def test_wrong_secret_fails(self):
        from jose import jwt

        payload = {"sub": "alice", "role": "admin", "exp": 9999999999}
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(token)


# ── Integration tests: /api/auth endpoints ───────────────────────────


class TestLoginEndpoint:
    """Tests for POST /api/auth/login."""

    def test_login_success(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "alice", "role": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["role"] == "admin"
        assert "token" in data
        # Verify the returned token is valid
        payload = decode_token(data["token"])
        assert payload["sub"] == "alice"

    def test_login_all_roles(self, client):
        for role in sorted(VALID_ROLES):
            resp = client.post(
                "/api/auth/login",
                json={"username": "user", "role": role},
            )
            assert resp.status_code == 200
            assert resp.json()["role"] == role

    def test_login_invalid_role(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "alice", "role": "superadmin"},
        )
        assert resp.status_code == 422

    def test_login_empty_username(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "", "role": "admin"},
        )
        assert resp.status_code == 422

    def test_login_missing_fields(self, client):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422


class TestMeEndpoint:
    """Tests for GET /api/auth/me."""

    def test_me_with_valid_token(self, client):
        # Login first
        login_resp = client.post(
            "/api/auth/login",
            json={"username": "alice", "role": "admin"},
        )
        token = login_resp.json()["token"]

        # Call /me with the token
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["role"] == "admin"

    def test_me_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 422  # Missing required header

    def test_me_with_invalid_token(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401

    def test_me_with_malformed_header(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer sometoken"},
        )
        assert resp.status_code == 401


class TestHealthStillUnauthenticated:
    """Verify that the health endpoint is not affected by auth."""

    def test_health_no_auth_required(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

"""Fixtures for API tests."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from sis.api.auth import create_token
from sis.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Provide a Starlette TestClient wired to the SIS FastAPI app."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return Authorization headers with a valid admin JWT."""
    token = create_token("test-admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tl_auth_headers() -> dict[str, str]:
    """Return Authorization headers with a valid team_lead JWT."""
    token = create_token("test-tl", "team_lead")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ic_auth_headers() -> dict[str, str]:
    """Return Authorization headers with a valid ic JWT."""
    token = create_token("test-ic", "ic")
    return {"Authorization": f"Bearer {token}"}

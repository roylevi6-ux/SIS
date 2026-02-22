"""Fixtures for API tests."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from sis.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Provide a Starlette TestClient wired to the SIS FastAPI app."""
    return TestClient(app)

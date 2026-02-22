"""Tests for global error handlers."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from sis.api.errors import APIError, api_error_handler, value_error_handler


def _make_app() -> FastAPI:
    """Build a minimal app with error handlers and trigger routes."""
    test_app = FastAPI()
    test_app.add_exception_handler(ValueError, value_error_handler)
    test_app.add_exception_handler(APIError, api_error_handler)

    @test_app.get("/raise-value-error")
    def _raise_value_error():
        raise ValueError("bad value")

    @test_app.get("/raise-api-error")
    def _raise_api_error():
        raise APIError(status_code=409, detail="conflict occurred")

    return test_app


_client = TestClient(_make_app())


def test_value_error_returns_422():
    resp = _client.get("/raise-value-error")
    assert resp.status_code == 422
    assert resp.json() == {"detail": "bad value"}


def test_api_error_returns_custom_status():
    resp = _client.get("/raise-api-error")
    assert resp.status_code == 409
    assert resp.json() == {"detail": "conflict occurred"}


def test_api_error_attributes():
    err = APIError(status_code=404, detail="not found")
    assert err.status_code == 404
    assert err.detail == "not found"

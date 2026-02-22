"""Tests for the /api/health endpoint."""

from __future__ import annotations


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_body(client):
    resp = client.get("/api/health")
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"

"""Tests for /api/deal-context endpoints."""

from unittest.mock import patch

import pytest


class TestDealContextAPI:
    @patch("sis.api.routes.deal_context.deal_context_service")
    def test_upsert_requires_tl_role(self, mock_svc, client, ic_auth_headers):
        resp = client.post(
            "/api/deal-context/",
            json={"account_id": "acc-1", "entries": [{"question_id": 2, "response_text": "CFO"}]},
            headers=ic_auth_headers,
        )
        assert resp.status_code == 403

    @patch("sis.api.routes.deal_context.deal_context_service")
    def test_upsert_succeeds_for_tl(self, mock_svc, client, tl_auth_headers):
        mock_svc.upsert_context.return_value = {
            "account_id": "acc-1",
            "entries": [{"id": "e-1", "question_id": 2, "response_text": "CFO", "created_at": "2026-03-03"}],
        }
        resp = client.post(
            "/api/deal-context/",
            json={"account_id": "acc-1", "entries": [{"question_id": 2, "response_text": "CFO"}]},
            headers=tl_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["entries"][0]["question_id"] == 2

    @patch("sis.api.routes.deal_context.deal_context_service")
    def test_get_context(self, mock_svc, client, auth_headers):
        mock_svc.get_current_context.return_value = {"current": {}, "history": []}
        resp = client.get("/api/deal-context/acc-1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["current"] == {}

    def test_get_questions(self, client, auth_headers):
        resp = client.get("/api/deal-context/questions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
        assert data["1"]["category"] == "change_event"

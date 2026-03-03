"""Tests for /api/chat endpoints."""

from __future__ import annotations

from unittest.mock import patch


# ── POST /api/chat/query ──────────────────────────────────────────────


class TestChatQuery:

    @patch("sis.api.routes.chat.resolve_scoping", return_value=None)
    @patch("sis.api.routes.chat.query_service")
    def test_query_returns_response(self, mock_svc, _mock_scope, client, auth_headers):
        mock_svc.query.return_value = "HealthyCorp has a health score of 82."
        resp = client.post(
            "/api/chat/query",
            json={"message": "How is HealthyCorp doing?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "HealthyCorp has a health score of 82."

    @patch("sis.api.routes.chat.resolve_scoping", return_value=None)
    @patch("sis.api.routes.chat.query_service")
    def test_query_passes_message_and_history(self, mock_svc, _mock_scope, client, auth_headers):
        mock_svc.query.return_value = "Answer"
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        client.post(
            "/api/chat/query",
            json={"message": "Follow-up question", "history": history},
            headers=auth_headers,
        )
        mock_svc.query.assert_called_once_with(
            "Follow-up question", history, visible_user_ids=None,
        )

    @patch("sis.api.routes.chat.resolve_scoping", return_value=None)
    @patch("sis.api.routes.chat.query_service")
    def test_query_no_history_passes_empty_list(self, mock_svc, _mock_scope, client, auth_headers):
        mock_svc.query.return_value = "Answer"
        client.post("/api/chat/query", json={"message": "Question"}, headers=auth_headers)
        mock_svc.query.assert_called_once_with("Question", [], visible_user_ids=None)

    @patch("sis.api.routes.chat.resolve_scoping", return_value=None)
    @patch("sis.api.routes.chat.query_service")
    def test_query_null_history_passes_empty_list(self, mock_svc, _mock_scope, client, auth_headers):
        mock_svc.query.return_value = "Answer"
        client.post(
            "/api/chat/query",
            json={"message": "Question", "history": None},
            headers=auth_headers,
        )
        mock_svc.query.assert_called_once_with("Question", [], visible_user_ids=None)

    def test_query_missing_message_returns_422(self, client, auth_headers):
        resp = client.post("/api/chat/query", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_query_empty_body_returns_422(self, client, auth_headers):
        resp = client.post("/api/chat/query", content=b"not json", headers=auth_headers)
        assert resp.status_code == 422

    @patch("sis.api.routes.chat.resolve_scoping", return_value=None)
    @patch("sis.api.routes.chat.query_service")
    def test_query_returns_no_data_message(self, mock_svc, _mock_scope, client, auth_headers):
        """Verify the route passes through the service's no-data response."""
        mock_svc.query.return_value = (
            "No pipeline data available yet. Upload transcripts and run analysis first."
        )
        resp = client.post(
            "/api/chat/query",
            json={"message": "What deals are at risk?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "No pipeline data" in resp.json()["response"]

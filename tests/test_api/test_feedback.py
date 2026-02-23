"""Tests for /api/feedback endpoints."""

from __future__ import annotations

from unittest.mock import patch


# ── POST /api/feedback/ ─────────────────────────────────────────────────


class TestSubmitFeedback:

    @patch("sis.api.routes.feedback.feedback_service")
    def test_submit_returns_result(self, mock_svc, client, auth_headers):
        mock_svc.submit_feedback.return_value = {
            "id": "fb-1",
            "account_id": "acct-1",
            "author": "TL One",
            "direction": "too_high",
            "reason": "off_channel",
            "health_score_at_time": 75,
        }
        resp = client.post("/api/feedback/", json={
            "account_id": "acct-1",
            "assessment_id": "assess-1",
            "author": "TL One",
            "direction": "too_high",
            "reason": "off_channel",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "fb-1"
        assert data["direction"] == "too_high"

    @patch("sis.api.routes.feedback.feedback_service")
    def test_submit_passes_all_params(self, mock_svc, client, auth_headers):
        mock_svc.submit_feedback.return_value = {"id": "fb-2"}
        client.post("/api/feedback/", json={
            "account_id": "acct-1",
            "assessment_id": "assess-1",
            "author": "TL One",
            "direction": "too_low",
            "reason": "stakeholder_context",
            "free_text": "Missing context from last meeting",
            "off_channel": True,
        }, headers=auth_headers)
        mock_svc.submit_feedback.assert_called_once_with(
            account_id="acct-1",
            assessment_id="assess-1",
            author="TL One",
            direction="too_low",
            reason="stakeholder_context",
            free_text="Missing context from last meeting",
            off_channel=True,
        )

    @patch("sis.api.routes.feedback.feedback_service")
    def test_submit_assessment_not_found_returns_404(self, mock_svc, client, auth_headers):
        mock_svc.submit_feedback.side_effect = ValueError("Assessment not found: bad-id")
        resp = client.post("/api/feedback/", json={
            "account_id": "acct-1",
            "assessment_id": "bad-id",
            "author": "TL One",
            "direction": "too_high",
            "reason": "off_channel",
        }, headers=auth_headers)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("sis.api.routes.feedback.feedback_service")
    def test_submit_invalid_direction_returns_422(self, mock_svc, client, auth_headers):
        mock_svc.submit_feedback.side_effect = ValueError(
            "direction must be one of {'too_high', 'too_low'}"
        )
        resp = client.post("/api/feedback/", json={
            "account_id": "acct-1",
            "assessment_id": "assess-1",
            "author": "TL One",
            "direction": "sideways",
            "reason": "off_channel",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_submit_missing_required_fields_returns_422(self, client, auth_headers):
        resp = client.post("/api/feedback/", json={"account_id": "acct-1"}, headers=auth_headers)
        assert resp.status_code == 422


# ── GET /api/feedback/ ──────────────────────────────────────────────────


class TestListFeedback:

    @patch("sis.api.routes.feedback.feedback_service")
    def test_list_returns_items(self, mock_svc, client, auth_headers):
        mock_svc.list_feedback.return_value = [
            {
                "id": "fb-1",
                "account_id": "acct-1",
                "account_name": "TestCorp",
                "deal_assessment_id": "assess-1",
                "author": "TL One",
                "direction": "too_high",
                "reason": "off_channel",
                "free_text": None,
                "health_score_at_time": 75,
                "off_channel": True,
                "resolution": None,
                "created_at": "2025-07-01T10:00:00",
            },
        ]
        resp = client.get("/api/feedback/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["account_name"] == "TestCorp"

    @patch("sis.api.routes.feedback.feedback_service")
    def test_list_passes_filters(self, mock_svc, client, auth_headers):
        mock_svc.list_feedback.return_value = []
        client.get("/api/feedback/?account_id=acct-1&author=TL+One&status=accepted", headers=auth_headers)
        mock_svc.list_feedback.assert_called_once_with(
            account_id="acct-1",
            author="TL One",
            status="accepted",
        )

    @patch("sis.api.routes.feedback.feedback_service")
    def test_list_default_params(self, mock_svc, client, auth_headers):
        mock_svc.list_feedback.return_value = []
        client.get("/api/feedback/", headers=auth_headers)
        mock_svc.list_feedback.assert_called_once_with(
            account_id=None,
            author=None,
            status=None,
        )

    @patch("sis.api.routes.feedback.feedback_service")
    def test_list_empty(self, mock_svc, client, auth_headers):
        mock_svc.list_feedback.return_value = []
        resp = client.get("/api/feedback/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ── PATCH /api/feedback/{feedback_id}/resolve ───────────────────────────


class TestResolveFeedback:

    @patch("sis.api.routes.feedback.feedback_service")
    def test_resolve_returns_result(self, mock_svc, client, auth_headers):
        mock_svc.resolve_feedback.return_value = {
            "id": "fb-1",
            "resolution": "accepted",
        }
        resp = client.patch("/api/feedback/fb-1/resolve", json={
            "resolution": "accepted",
            "notes": "Valid feedback",
            "resolved_by": "VP Sales",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolution"] == "accepted"

    @patch("sis.api.routes.feedback.feedback_service")
    def test_resolve_passes_params(self, mock_svc, client, auth_headers):
        mock_svc.resolve_feedback.return_value = {"id": "fb-1", "resolution": "rejected"}
        client.patch("/api/feedback/fb-1/resolve", json={
            "resolution": "rejected",
            "notes": "Not actionable",
            "resolved_by": "VP Sales",
        }, headers=auth_headers)
        mock_svc.resolve_feedback.assert_called_once_with(
            feedback_id="fb-1",
            resolution="rejected",
            notes="Not actionable",
            resolved_by="VP Sales",
        )

    @patch("sis.api.routes.feedback.feedback_service")
    def test_resolve_not_found_returns_404(self, mock_svc, client, auth_headers):
        mock_svc.resolve_feedback.side_effect = ValueError("Feedback not found: bad-id")
        resp = client.patch("/api/feedback/bad-id/resolve", json={
            "resolution": "accepted",
            "notes": "ok",
            "resolved_by": "VP Sales",
        }, headers=auth_headers)
        assert resp.status_code == 404

    @patch("sis.api.routes.feedback.feedback_service")
    def test_resolve_invalid_resolution_returns_422(self, mock_svc, client, auth_headers):
        mock_svc.resolve_feedback.side_effect = ValueError(
            "resolution must be 'accepted' or 'rejected'"
        )
        resp = client.patch("/api/feedback/fb-1/resolve", json={
            "resolution": "maybe",
            "notes": "unsure",
            "resolved_by": "VP Sales",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_resolve_missing_fields_returns_422(self, client, auth_headers):
        resp = client.patch("/api/feedback/fb-1/resolve", json={}, headers=auth_headers)
        assert resp.status_code == 422


# ── GET /api/feedback/summary ───────────────────────────────────────────


class TestFeedbackSummary:

    @patch("sis.api.routes.feedback.feedback_service")
    def test_summary_returns_aggregates(self, mock_svc, client, auth_headers):
        mock_svc.get_feedback_summary.return_value = {
            "total": 10,
            "by_direction": {"too_high": 6, "too_low": 4},
            "by_reason": {"off_channel": 3, "stakeholder_context": 7},
            "by_author": {"TL One": 5, "TL Two": 5},
            "by_resolution": {"accepted": 3, "rejected": 2, None: 5},
            "authors": ["TL One", "TL Two"],
        }
        resp = client.get("/api/feedback/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10
        assert len(data["authors"]) == 2

    @patch("sis.api.routes.feedback.feedback_service")
    def test_summary_empty(self, mock_svc, client, auth_headers):
        mock_svc.get_feedback_summary.return_value = {
            "total": 0,
            "by_direction": {},
            "by_reason": {},
            "by_author": {},
            "by_resolution": {},
            "authors": [],
        }
        resp = client.get("/api/feedback/summary", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

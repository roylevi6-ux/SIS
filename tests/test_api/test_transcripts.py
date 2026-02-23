"""Tests for /api/transcripts endpoints."""

from __future__ import annotations

from unittest.mock import patch, MagicMock


# ── Helpers ──────────────────────────────────────────────────────────


def _make_transcript_orm(
    id: str = "t-1",
    account_id: str = "acct-1",
    call_date: str = "2025-06-15",
    token_count: int = 500,
    is_active: int = 1,
    created_at: str = "2025-06-15T10:00:00+00:00",
):
    """Create a mock ORM Transcript object."""
    obj = MagicMock()
    obj.id = id
    obj.account_id = account_id
    obj.call_date = call_date
    obj.token_count = token_count
    obj.is_active = is_active
    obj.created_at = created_at
    return obj


# ── GET /api/transcripts/{account_id} ──────────────────────────────


class TestListTranscripts:

    @patch("sis.api.routes.transcripts.transcript_service")
    def test_list_transcripts_returns_200(self, mock_svc, client, auth_headers):
        mock_svc.list_transcripts.return_value = [
            {
                "id": "t-1",
                "call_date": "2025-06-15",
                "duration_minutes": 30,
                "token_count": 500,
                "is_active": True,
                "created_at": "2025-06-15T10:00:00+00:00",
                "preprocessed_text": "call content",
            },
        ]
        resp = client.get("/api/transcripts/acct-1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["call_date"] == "2025-06-15"

    @patch("sis.api.routes.transcripts.transcript_service")
    def test_list_transcripts_default_active_only(self, mock_svc, client, auth_headers):
        mock_svc.list_transcripts.return_value = []
        client.get("/api/transcripts/acct-1", headers=auth_headers)
        mock_svc.list_transcripts.assert_called_once_with("acct-1", active_only=True)

    @patch("sis.api.routes.transcripts.transcript_service")
    def test_list_transcripts_all(self, mock_svc, client, auth_headers):
        mock_svc.list_transcripts.return_value = []
        client.get("/api/transcripts/acct-1?active_only=false", headers=auth_headers)
        mock_svc.list_transcripts.assert_called_once_with("acct-1", active_only=False)

    @patch("sis.api.routes.transcripts.transcript_service")
    def test_list_transcripts_empty(self, mock_svc, client, auth_headers):
        mock_svc.list_transcripts.return_value = []
        resp = client.get("/api/transcripts/nonexistent", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ── POST /api/transcripts/ ─────────────────────────────────────────


class TestUploadTranscript:

    @patch("sis.api.routes.transcripts.transcript_service")
    def test_upload_transcript_returns_response(self, mock_svc, client, auth_headers):
        mock_svc.upload_transcript.return_value = _make_transcript_orm(
            id="t-new", account_id="acct-1", call_date="2025-07-01",
            token_count=750, is_active=1,
            created_at="2025-07-01T08:00:00+00:00",
        )
        resp = client.post("/api/transcripts/", json={
            "account_id": "acct-1",
            "raw_text": "Rep: Hello, thanks for joining...",
            "call_date": "2025-07-01",
            "participants": [{"name": "Rep", "role": "AE", "company": "Riskified"}],
            "duration_minutes": 45,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "t-new"
        assert data["account_id"] == "acct-1"
        assert data["call_date"] == "2025-07-01"
        assert data["token_count"] == 750
        assert data["is_active"] is True
        assert data["created_at"] == "2025-07-01T08:00:00+00:00"

    @patch("sis.api.routes.transcripts.transcript_service")
    def test_upload_transcript_passes_correct_params(self, mock_svc, client, auth_headers):
        mock_svc.upload_transcript.return_value = _make_transcript_orm()
        participants = [{"name": "Rep", "role": "AE", "company": "Riskified"}]
        client.post("/api/transcripts/", json={
            "account_id": "acct-1",
            "raw_text": "Call content here",
            "call_date": "2025-07-01",
            "participants": participants,
            "duration_minutes": 30,
        }, headers=auth_headers)
        mock_svc.upload_transcript.assert_called_once_with(
            account_id="acct-1",
            raw_text="Call content here",
            call_date="2025-07-01",
            participants=participants,
            duration_minutes=30,
        )

    @patch("sis.api.routes.transcripts.transcript_service")
    def test_upload_transcript_minimal_body(self, mock_svc, client, auth_headers):
        mock_svc.upload_transcript.return_value = _make_transcript_orm()
        resp = client.post("/api/transcripts/", json={
            "account_id": "acct-1",
            "raw_text": "Some transcript text.",
            "call_date": "2025-07-01",
        }, headers=auth_headers)
        assert resp.status_code == 200
        mock_svc.upload_transcript.assert_called_once_with(
            account_id="acct-1",
            raw_text="Some transcript text.",
            call_date="2025-07-01",
            participants=None,
            duration_minutes=None,
        )

    def test_upload_transcript_missing_required_fields(self, client, auth_headers):
        resp = client.post("/api/transcripts/", json={"account_id": "acct-1"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_upload_transcript_missing_account_id(self, client, auth_headers):
        resp = client.post("/api/transcripts/", json={
            "raw_text": "text",
            "call_date": "2025-07-01",
        }, headers=auth_headers)
        assert resp.status_code == 422

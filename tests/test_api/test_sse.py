"""Tests for /api/sse endpoints."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock


# ── GET /api/sse/analysis/{run_id} ──────────────────────────────────


class TestAnalysisProgress:

    @patch("sis.api.routes.sse._get_progress")
    def test_completed_run_emits_single_event(self, mock_progress, client):
        """A completed run should emit one SSE event and close the stream."""
        mock_progress.return_value = {
            "run_id": "run-1",
            "status": "completed",
            "started_at": "2025-06-15T10:00:00+00:00",
            "completed_at": "2025-06-15T10:05:00+00:00",
        }
        resp = client.get("/api/sse/analysis/run-1")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        # Parse SSE data lines
        lines = resp.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data: ")]
        assert len(data_lines) == 1
        payload = json.loads(data_lines[0].removeprefix("data: "))
        assert payload["run_id"] == "run-1"
        assert payload["status"] == "completed"

    @patch("sis.api.routes.sse._get_progress")
    def test_failed_run_emits_single_event(self, mock_progress, client):
        """A failed run should also close the stream immediately."""
        mock_progress.return_value = {
            "run_id": "run-2",
            "status": "failed",
            "started_at": "2025-06-15T10:00:00+00:00",
            "completed_at": None,
        }
        resp = client.get("/api/sse/analysis/run-2")
        assert resp.status_code == 200
        data_lines = [l for l in resp.text.strip().split("\n") if l.startswith("data: ")]
        assert len(data_lines) == 1
        payload = json.loads(data_lines[0].removeprefix("data: "))
        assert payload["status"] == "failed"

    @patch("sis.api.routes.sse._get_progress")
    def test_partial_run_emits_single_event(self, mock_progress, client):
        """A partial run (terminal status) closes the stream immediately."""
        mock_progress.return_value = {
            "run_id": "run-3",
            "status": "partial",
            "started_at": "2025-06-15T10:00:00+00:00",
            "completed_at": "2025-06-15T10:03:00+00:00",
        }
        resp = client.get("/api/sse/analysis/run-3")
        assert resp.status_code == 200
        data_lines = [l for l in resp.text.strip().split("\n") if l.startswith("data: ")]
        assert len(data_lines) == 1
        payload = json.loads(data_lines[0].removeprefix("data: "))
        assert payload["status"] == "partial"

    @patch("sis.api.routes.sse._get_progress")
    def test_running_then_completed_emits_two_events(self, mock_progress, client):
        """A running run transitions to completed after polling."""
        mock_progress.side_effect = [
            {
                "run_id": "run-4",
                "status": "running",
                "started_at": "2025-06-15T10:00:00+00:00",
                "completed_at": None,
            },
            {
                "run_id": "run-4",
                "status": "completed",
                "started_at": "2025-06-15T10:00:00+00:00",
                "completed_at": "2025-06-15T10:05:00+00:00",
            },
        ]
        resp = client.get("/api/sse/analysis/run-4")
        assert resp.status_code == 200
        data_lines = [l for l in resp.text.strip().split("\n") if l.startswith("data: ")]
        assert len(data_lines) == 2
        first = json.loads(data_lines[0].removeprefix("data: "))
        second = json.loads(data_lines[1].removeprefix("data: "))
        assert first["status"] == "running"
        assert second["status"] == "completed"

    @patch("sis.api.routes.sse._get_progress")
    def test_not_found_run_emits_not_found(self, mock_progress, client):
        """A missing run_id should emit a not_found status (non-terminal, but
        we test the shape). In practice the client should handle this."""
        mock_progress.side_effect = [
            {"run_id": "no-such-run", "status": "not_found"},
            # After not_found, if the run is later created, it could appear.
            # For safety, let's terminate the test by returning a terminal status.
            {"run_id": "no-such-run", "status": "failed"},
        ]
        resp = client.get("/api/sse/analysis/no-such-run")
        assert resp.status_code == 200
        data_lines = [l for l in resp.text.strip().split("\n") if l.startswith("data: ")]
        assert len(data_lines) >= 1
        first = json.loads(data_lines[0].removeprefix("data: "))
        assert first["status"] == "not_found"

    @patch("sis.api.routes.sse._get_progress")
    def test_sse_format_has_double_newline(self, mock_progress, client):
        """Each SSE data line must end with double newline (\\n\\n)."""
        mock_progress.return_value = {
            "run_id": "run-fmt",
            "status": "completed",
            "started_at": "2025-06-15T10:00:00+00:00",
            "completed_at": "2025-06-15T10:05:00+00:00",
        }
        resp = client.get("/api/sse/analysis/run-fmt")
        # The raw text should contain "data: {...}\n\n"
        assert "data: " in resp.text
        assert resp.text.endswith("\n\n")

"""Tests for /api/analyses endpoints."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock

import pytest


# ── POST /api/analyses/ ──────────────────────────────────────────────


class TestRunAnalysis:

    @patch("sis.api.routes.analyses.analysis_service")
    @patch("sis.api.routes.analyses.asyncio")
    @patch("sis.services.transcript_service.get_active_transcript_texts")
    def test_run_analysis_returns_started(self, mock_texts, mock_asyncio, mock_svc, client):
        mock_texts.return_value = ["transcript one", "transcript two"]
        mock_svc.create_analysis_run.return_value = "run-123"
        mock_loop = mock_asyncio.get_event_loop.return_value
        resp = client.post("/api/analyses/", json={"account_id": "acct-1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["account_id"] == "acct-1"
        assert data["run_id"] == "run-123"
        mock_loop.run_in_executor.assert_called_once()

    @patch("sis.services.transcript_service.get_active_transcript_texts")
    def test_run_analysis_no_transcripts_returns_422(self, mock_texts, client):
        mock_texts.return_value = []
        resp = client.post("/api/analyses/", json={"account_id": "acct-1"})
        assert resp.status_code == 422
        assert "No active transcripts" in resp.json()["detail"]

    @patch("sis.services.transcript_service.get_active_transcript_texts")
    def test_run_analysis_account_not_found_returns_404(self, mock_texts, client):
        mock_texts.side_effect = ValueError("Account not found: bad-id")
        resp = client.post("/api/analyses/", json={"account_id": "bad-id"})
        assert resp.status_code == 404
        assert "Account not found" in resp.json()["detail"]

    def test_run_analysis_missing_account_id_returns_422(self, client):
        resp = client.post("/api/analyses/", json={})
        assert resp.status_code == 422


# ── GET /api/analyses/history/{account_id} ────────────────────────────


class TestGetHistory:

    @patch("sis.api.routes.analyses.analysis_service")
    def test_get_history_returns_list(self, mock_svc, client):
        mock_svc.get_analysis_history.return_value = [
            {
                "run_id": "run-1",
                "started_at": "2025-06-15T10:00:00+00:00",
                "completed_at": "2025-06-15T10:05:00+00:00",
                "status": "completed",
                "total_cost_usd": 0.05,
                "total_input_tokens": 5000,
                "total_output_tokens": 2000,
            },
        ]
        resp = client.get("/api/analyses/history/acct-1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["run_id"] == "run-1"
        assert data[0]["status"] == "completed"

    @patch("sis.api.routes.analyses.analysis_service")
    def test_get_history_empty(self, mock_svc, client):
        mock_svc.get_analysis_history.return_value = []
        resp = client.get("/api/analyses/history/acct-1")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("sis.api.routes.analyses.analysis_service")
    def test_get_history_passes_account_id(self, mock_svc, client):
        mock_svc.get_analysis_history.return_value = []
        client.get("/api/analyses/history/acct-42")
        mock_svc.get_analysis_history.assert_called_once_with("acct-42")


# ── GET /api/analyses/{run_id}/agents ────────────────────────────────


class TestGetAgents:

    @patch("sis.api.routes.analyses.analysis_service")
    def test_get_agents_returns_list(self, mock_svc, client):
        mock_svc.get_agent_analyses.return_value = [
            {
                "agent_id": "agent_1",
                "agent_name": "Stage & Progress",
                "narrative": "The deal is at stage 3.",
                "findings": {"inferred_stage": 3},
                "evidence": [],
                "confidence_overall": 0.85,
                "confidence_rationale": "Strong signals",
                "data_gaps": [],
                "sparse_data_flag": False,
                "model_used": "gemini-2.0-flash",
                "input_tokens": 1000,
                "output_tokens": 500,
                "status": "completed",
            },
        ]
        resp = client.get("/api/analyses/run-1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["agent_id"] == "agent_1"
        assert data[0]["status"] == "completed"

    @patch("sis.api.routes.analyses.analysis_service")
    def test_get_agents_empty(self, mock_svc, client):
        mock_svc.get_agent_analyses.return_value = []
        resp = client.get("/api/analyses/run-1/agents")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("sis.api.routes.analyses.analysis_service")
    def test_get_agents_passes_run_id(self, mock_svc, client):
        mock_svc.get_agent_analyses.return_value = []
        client.get("/api/analyses/run-99/agents")
        mock_svc.get_agent_analyses.assert_called_once_with("run-99")


# ── POST /api/analyses/{run_id}/rerun/{agent_id} ─────────────────────


class TestRerunAgent:

    @patch("sis.api.routes.analyses.analysis_service")
    def test_rerun_agent_returns_result(self, mock_svc, client):
        mock_svc.rerun_agent.return_value = {
            "agent_id": "agent_3",
            "status": "completed",
            "warnings": [],
            "input_tokens": 800,
            "output_tokens": 400,
        }
        resp = client.post("/api/analyses/run-1/rerun/agent_3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "agent_3"
        assert data["status"] == "completed"

    @patch("sis.api.routes.analyses.analysis_service")
    def test_rerun_agent_not_found_returns_404(self, mock_svc, client):
        mock_svc.rerun_agent.side_effect = ValueError("Analysis run not found: bad-run")
        resp = client.post("/api/analyses/bad-run/rerun/agent_1")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("sis.api.routes.analyses.analysis_service")
    def test_rerun_agent_invalid_agent_returns_422(self, mock_svc, client):
        mock_svc.rerun_agent.side_effect = ValueError(
            "Cannot rerun agent_10. Only agents 1-8 can be individually rerun."
        )
        resp = client.post("/api/analyses/run-1/rerun/agent_10")
        assert resp.status_code == 422


# ── POST /api/analyses/{run_id}/resynthesize ──────────────────────────


class TestResynthesize:

    @patch("sis.api.routes.analyses.analysis_service")
    def test_resynthesize_returns_result(self, mock_svc, client):
        mock_svc.resynthesize.return_value = {
            "status": "completed",
            "health_score": 72,
            "forecast_category": "Commit",
            "input_tokens": 3000,
            "output_tokens": 1500,
        }
        resp = client.post("/api/analyses/run-1/resynthesize")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["health_score"] == 72
        assert data["forecast_category"] == "Commit"

    @patch("sis.api.routes.analyses.analysis_service")
    def test_resynthesize_run_not_found_returns_404(self, mock_svc, client):
        mock_svc.resynthesize.side_effect = ValueError("Analysis run not found: bad-run")
        resp = client.post("/api/analyses/bad-run/resynthesize")
        assert resp.status_code == 404

    @patch("sis.api.routes.analyses.analysis_service")
    def test_resynthesize_missing_agent1_returns_422(self, mock_svc, client):
        mock_svc.resynthesize.side_effect = ValueError(
            "Agent 1 output missing — cannot resynthesize"
        )
        resp = client.post("/api/analyses/run-1/resynthesize")
        assert resp.status_code == 422

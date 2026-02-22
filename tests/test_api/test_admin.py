"""Tests for admin endpoints: calibration, usage tracking, action logs,
coaching, prompt versions, rep scorecard, forecast data, and export.
"""

from __future__ import annotations

from unittest.mock import patch


# ═══════════════════════════════════════════════════════════════════════
# Calibration — /api/calibration/*
# ═══════════════════════════════════════════════════════════════════════


class TestCalibrationCurrent:

    @patch("sis.api.routes.calibration.calibration_service")
    def test_current_returns_config(self, mock_svc, client):
        mock_svc.get_current_calibration.return_value = {
            "version": "1.2",
            "weights": {"agent_2": 0.15},
        }
        resp = client.get("/api/calibration/current")
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.2"

    @patch("sis.api.routes.calibration.calibration_service")
    def test_current_returns_empty_when_no_config(self, mock_svc, client):
        mock_svc.get_current_calibration.return_value = {}
        resp = client.get("/api/calibration/current")
        assert resp.status_code == 200
        assert resp.json() == {}


class TestCalibrationPatterns:

    @patch("sis.api.routes.calibration.calibration_service")
    def test_patterns_returns_analysis(self, mock_svc, client):
        mock_svc.get_feedback_patterns.return_value = {
            "total_feedback": 15,
            "by_reason": {"off_channel": 5},
            "by_direction": {"too_high": 10, "too_low": 5},
            "by_agent": {"agent_2": 8},
            "direction_per_agent": {"agent_2": {"too_high": 5, "too_low": 3}},
            "top_flagged_reasons": [("off_channel", 5)],
        }
        resp = client.get("/api/calibration/patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_feedback"] == 15


class TestCalibrationCreate:

    @patch("sis.api.routes.calibration.calibration_service")
    def test_create_returns_log(self, mock_svc, client):
        mock_svc.create_calibration_log.return_value = {
            "id": "cal-1",
            "config_version": "1.3",
            "calibration_date": "2025-07-01",
            "approved_by": "VP Sales",
        }
        resp = client.post("/api/calibration/", json={
            "config_version": "1.3",
            "previous_version": "1.2",
            "changes": "Adjusted agent_2 weight",
            "feedback_items_reviewed": 15,
            "approved_by": "VP Sales",
        })
        assert resp.status_code == 200
        assert resp.json()["config_version"] == "1.3"

    @patch("sis.api.routes.calibration.calibration_service")
    def test_create_passes_params(self, mock_svc, client):
        mock_svc.create_calibration_log.return_value = {"id": "cal-1"}
        client.post("/api/calibration/", json={
            "config_version": "1.3",
            "feedback_items_reviewed": 10,
        })
        mock_svc.create_calibration_log.assert_called_once_with(
            config_version="1.3",
            previous_version=None,
            changes=None,
            feedback_items_reviewed=10,
            approved_by=None,
        )

    def test_create_missing_required_returns_422(self, client):
        resp = client.post("/api/calibration/", json={})
        assert resp.status_code == 422


class TestCalibrationHistory:

    @patch("sis.api.routes.calibration.calibration_service")
    def test_history_returns_list(self, mock_svc, client):
        mock_svc.list_calibration_history.return_value = [
            {
                "id": "cal-1",
                "calibration_date": "2025-07-01",
                "config_version": "1.3",
                "config_previous_version": "1.2",
                "feedback_items_reviewed": 15,
                "config_changes": "Weight adjustment",
                "approved_by": "VP Sales",
                "created_at": "2025-07-01T10:00:00",
            },
        ]
        resp = client.get("/api/calibration/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["config_version"] == "1.3"

    @patch("sis.api.routes.calibration.calibration_service")
    def test_history_empty(self, mock_svc, client):
        mock_svc.list_calibration_history.return_value = []
        resp = client.get("/api/calibration/history")
        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════
# Usage Tracking — /api/tracking/*
# ═══════════════════════════════════════════════════════════════════════


class TestUsageSummary:

    @patch("sis.api.routes.admin.usage_tracking_service")
    def test_summary_returns_data(self, mock_svc, client):
        mock_svc.get_usage_summary.return_value = {
            "total_events": 100,
            "days": 30,
            "by_type": {"page_view": 60, "chat_query": 40},
            "by_day": {"2025-07-01": 10},
            "by_user": {"TL One": 50},
            "by_page": {"Pipeline": 30},
        }
        resp = client.get("/api/tracking/summary")
        assert resp.status_code == 200
        assert resp.json()["total_events"] == 100

    @patch("sis.api.routes.admin.usage_tracking_service")
    def test_summary_passes_days(self, mock_svc, client):
        mock_svc.get_usage_summary.return_value = {"total_events": 0, "days": 7}
        client.get("/api/tracking/summary?days=7")
        mock_svc.get_usage_summary.assert_called_once_with(days=7)

    @patch("sis.api.routes.admin.usage_tracking_service")
    def test_summary_default_days(self, mock_svc, client):
        mock_svc.get_usage_summary.return_value = {"total_events": 0, "days": 30}
        client.get("/api/tracking/summary")
        mock_svc.get_usage_summary.assert_called_once_with(days=30)


class TestCROMetrics:

    @patch("sis.api.routes.admin.usage_tracking_service")
    def test_cro_returns_list(self, mock_svc, client):
        mock_svc.get_cro_metrics.return_value = [
            {
                "metric": "Deal Coverage",
                "description": "Accounts with assessment < 14 days old",
                "target": "80%",
                "actual": "85%",
                "value": 85.0,
                "passed": True,
            },
        ]
        resp = client.get("/api/tracking/cro-metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["passed"] is True


class TestTrackEvent:

    @patch("sis.api.routes.admin.usage_tracking_service")
    def test_track_returns_ok(self, mock_svc, client):
        mock_svc.track_event.return_value = None
        resp = client.post("/api/tracking/event", json={
            "event_type": "page_view",
            "user_name": "TL One",
            "page_name": "Pipeline",
        })
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @patch("sis.api.routes.admin.usage_tracking_service")
    def test_track_passes_params(self, mock_svc, client):
        mock_svc.track_event.return_value = None
        client.post("/api/tracking/event", json={
            "event_type": "chat_query",
            "user_name": "TL One",
            "account_id": "acct-1",
            "page_name": "Chat",
            "metadata": {"query": "show risks"},
        })
        mock_svc.track_event.assert_called_once_with(
            event_type="chat_query",
            user_name="TL One",
            account_id="acct-1",
            page_name="Chat",
            metadata={"query": "show risks"},
        )


# ═══════════════════════════════════════════════════════════════════════
# Action Logs — /api/logs/actions*
# ═══════════════════════════════════════════════════════════════════════


class TestGetActionLogs:

    @patch("sis.api.routes.admin.user_action_log_service")
    def test_logs_returns_list(self, mock_svc, client):
        mock_svc.get_action_logs.return_value = [
            {
                "id": "log-1",
                "user_name": "TL One",
                "action_type": "page_view",
                "action_detail": "Viewed pipeline",
                "account_name": "",
                "page_name": "Pipeline",
                "created_at": "2025-07-01T10:00:00",
                "metadata": {},
            },
        ]
        resp = client.get("/api/logs/actions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("sis.api.routes.admin.user_action_log_service")
    def test_logs_passes_filters(self, mock_svc, client):
        mock_svc.get_action_logs.return_value = []
        client.get(
            "/api/logs/actions?days=7&action_type=page_view"
            "&user_name=TL+One&account_id=acct-1&limit=100"
        )
        mock_svc.get_action_logs.assert_called_once_with(
            days=7,
            action_type="page_view",
            user_name="TL One",
            account_id="acct-1",
            limit=100,
        )

    @patch("sis.api.routes.admin.user_action_log_service")
    def test_logs_default_params(self, mock_svc, client):
        mock_svc.get_action_logs.return_value = []
        client.get("/api/logs/actions")
        mock_svc.get_action_logs.assert_called_once_with(
            days=30,
            action_type=None,
            user_name=None,
            account_id=None,
            limit=500,
        )


class TestGetActionSummary:

    @patch("sis.api.routes.admin.user_action_log_service")
    def test_summary_returns_data(self, mock_svc, client):
        mock_svc.get_action_summary.return_value = {
            "total": 50,
            "days": 30,
            "by_type": {"page_view": 30},
            "by_user": {"TL One": 50},
            "by_day": {"2025-07-01": 10},
        }
        resp = client.get("/api/logs/actions/summary")
        assert resp.status_code == 200
        assert resp.json()["total"] == 50

    @patch("sis.api.routes.admin.user_action_log_service")
    def test_summary_passes_days(self, mock_svc, client):
        mock_svc.get_action_summary.return_value = {"total": 0, "days": 7}
        client.get("/api/logs/actions/summary?days=7")
        mock_svc.get_action_summary.assert_called_once_with(days=7)


class TestLogAction:

    @patch("sis.api.routes.admin.user_action_log_service")
    def test_log_returns_ok(self, mock_svc, client):
        mock_svc.log_action.return_value = None
        resp = client.post("/api/logs/actions", json={
            "action_type": "page_view",
            "user_name": "TL One",
            "page_name": "Pipeline",
        })
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @patch("sis.api.routes.admin.user_action_log_service")
    def test_log_passes_all_params(self, mock_svc, client):
        mock_svc.log_action.return_value = None
        client.post("/api/logs/actions", json={
            "action_type": "ic_forecast_set",
            "action_detail": "Set to Commit",
            "user_name": "TL One",
            "account_id": "acct-1",
            "account_name": "TestCorp",
            "page_name": "Account Detail",
            "session_id": "sess-123",
            "metadata": {"old_value": "Pipeline"},
        })
        mock_svc.log_action.assert_called_once_with(
            action_type="ic_forecast_set",
            action_detail="Set to Commit",
            user_name="TL One",
            account_id="acct-1",
            account_name="TestCorp",
            page_name="Account Detail",
            session_id="sess-123",
            metadata={"old_value": "Pipeline"},
        )


# ═══════════════════════════════════════════════════════════════════════
# Coaching — /api/coaching/*
# ═══════════════════════════════════════════════════════════════════════


class TestSubmitCoaching:

    @patch("sis.api.routes.admin.coaching_service")
    def test_submit_returns_result(self, mock_svc, client):
        mock_svc.submit_coaching.return_value = {
            "id": "coach-1",
            "account_id": "acct-1",
            "rep_name": "AE One",
            "dimension": "Stakeholder Engagement",
            "dimension_score_at_time": 65,
            "health_score_at_time": 70,
        }
        resp = client.post("/api/coaching/", json={
            "account_id": "acct-1",
            "rep_name": "AE One",
            "coach_name": "TL One",
            "dimension": "Stakeholder Engagement",
            "feedback_text": "Needs more exec engagement",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "coach-1"
        assert data["dimension"] == "Stakeholder Engagement"

    @patch("sis.api.routes.admin.coaching_service")
    def test_submit_passes_params(self, mock_svc, client):
        mock_svc.submit_coaching.return_value = {"id": "coach-1"}
        client.post("/api/coaching/", json={
            "account_id": "acct-1",
            "rep_name": "AE One",
            "coach_name": "TL One",
            "dimension": "Objection Handling",
            "feedback_text": "Better risk acknowledgment needed",
        })
        mock_svc.submit_coaching.assert_called_once_with(
            account_id="acct-1",
            rep_name="AE One",
            coach_name="TL One",
            dimension="Objection Handling",
            feedback_text="Better risk acknowledgment needed",
        )

    @patch("sis.api.routes.admin.coaching_service")
    def test_submit_account_not_found_returns_404(self, mock_svc, client):
        mock_svc.submit_coaching.side_effect = ValueError("Account not found: bad-id")
        resp = client.post("/api/coaching/", json={
            "account_id": "bad-id",
            "rep_name": "AE One",
            "coach_name": "TL One",
            "dimension": "Stakeholder Engagement",
            "feedback_text": "Test",
        })
        assert resp.status_code == 404

    @patch("sis.api.routes.admin.coaching_service")
    def test_submit_invalid_dimension_returns_422(self, mock_svc, client):
        mock_svc.submit_coaching.side_effect = ValueError(
            "dimension must be one of ['Stakeholder Engagement', ...]"
        )
        resp = client.post("/api/coaching/", json={
            "account_id": "acct-1",
            "rep_name": "AE One",
            "coach_name": "TL One",
            "dimension": "Nonexistent",
            "feedback_text": "Test",
        })
        assert resp.status_code == 422

    def test_submit_missing_required_returns_422(self, client):
        resp = client.post("/api/coaching/", json={"account_id": "acct-1"})
        assert resp.status_code == 422


class TestListCoaching:

    @patch("sis.api.routes.admin.coaching_service")
    def test_list_returns_items(self, mock_svc, client):
        mock_svc.list_coaching.return_value = [
            {
                "id": "coach-1",
                "account_id": "acct-1",
                "account_name": "TestCorp",
                "rep_name": "AE One",
                "coach_name": "TL One",
                "dimension": "Stakeholder Engagement",
                "coaching_date": "2025-07-01",
                "feedback_text": "More exec meetings needed",
                "dimension_score_at_time": 65,
                "health_score_at_time": 70,
                "incorporated": False,
                "incorporated_at": None,
                "incorporated_notes": None,
                "created_at": "2025-07-01T10:00:00",
            },
        ]
        resp = client.get("/api/coaching/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("sis.api.routes.admin.coaching_service")
    def test_list_passes_filters(self, mock_svc, client):
        mock_svc.list_coaching.return_value = []
        client.get(
            "/api/coaching/?rep_name=AE+One&account_id=acct-1"
            "&dimension=Objection+Handling&incorporated=true"
        )
        mock_svc.list_coaching.assert_called_once_with(
            rep_name="AE One",
            account_id="acct-1",
            dimension="Objection Handling",
            incorporated=True,
        )

    @patch("sis.api.routes.admin.coaching_service")
    def test_list_default_params(self, mock_svc, client):
        mock_svc.list_coaching.return_value = []
        client.get("/api/coaching/")
        mock_svc.list_coaching.assert_called_once_with(
            rep_name=None,
            account_id=None,
            dimension=None,
            incorporated=None,
        )


class TestMarkIncorporated:

    @patch("sis.api.routes.admin.coaching_service")
    def test_mark_returns_result(self, mock_svc, client):
        mock_svc.mark_incorporated.return_value = {
            "id": "coach-1",
            "incorporated": True,
        }
        resp = client.patch("/api/coaching/coach-1/incorporate?notes=Score+improved")
        assert resp.status_code == 200
        assert resp.json()["incorporated"] is True

    @patch("sis.api.routes.admin.coaching_service")
    def test_mark_passes_params(self, mock_svc, client):
        mock_svc.mark_incorporated.return_value = {"id": "coach-1", "incorporated": True}
        client.patch("/api/coaching/coach-1/incorporate?notes=Verified")
        mock_svc.mark_incorporated.assert_called_once_with(
            entry_id="coach-1",
            notes="Verified",
        )

    @patch("sis.api.routes.admin.coaching_service")
    def test_mark_not_found_returns_404(self, mock_svc, client):
        mock_svc.mark_incorporated.side_effect = ValueError(
            "Coaching entry not found: bad-id"
        )
        resp = client.patch("/api/coaching/bad-id/incorporate")
        assert resp.status_code == 404


class TestCoachingSummary:

    @patch("sis.api.routes.admin.coaching_service")
    def test_summary_returns_data(self, mock_svc, client):
        mock_svc.get_coaching_summary.return_value = {
            "total": 10,
            "incorporated": 3,
            "incorporation_rate": 30.0,
            "by_dimension": {
                "Stakeholder Engagement": {"total": 4, "incorporated": 2, "rate": 50.0},
            },
            "coaches": ["TL One"],
        }
        resp = client.get("/api/coaching/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10
        assert data["incorporation_rate"] == 30.0

    @patch("sis.api.routes.admin.coaching_service")
    def test_summary_passes_rep_name(self, mock_svc, client):
        mock_svc.get_coaching_summary.return_value = {"total": 0}
        client.get("/api/coaching/summary?rep_name=AE+One")
        mock_svc.get_coaching_summary.assert_called_once_with(rep_name="AE One")


class TestCheckIncorporation:

    @patch("sis.api.routes.admin.coaching_service")
    def test_check_returns_suggestions(self, mock_svc, client):
        mock_svc.check_incorporation.return_value = [
            {
                "entry_id": "coach-1",
                "account_name": "TestCorp",
                "dimension": "Stakeholder Engagement",
                "score_at_time": 55,
                "current_score": 72,
                "delta": 17,
                "feedback_text": "More exec meetings",
            },
        ]
        resp = client.get("/api/coaching/check?rep_name=AE+One")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["delta"] == 17

    @patch("sis.api.routes.admin.coaching_service")
    def test_check_empty(self, mock_svc, client):
        mock_svc.check_incorporation.return_value = []
        resp = client.get("/api/coaching/check?rep_name=AE+One")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_check_requires_rep_name(self, client):
        """rep_name is required — missing it returns 422."""
        resp = client.get("/api/coaching/check")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════
# Prompt Versions — /api/prompts/versions*
# ═══════════════════════════════════════════════════════════════════════


class TestListVersions:

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_list_returns_items(self, mock_svc, client):
        mock_svc.list_versions.return_value = [
            {
                "id": "pv-1",
                "agent_id": "agent_2",
                "version": "1.0",
                "prompt_template": "Analyze stakeholders...",
                "calibration_config_version": None,
                "change_notes": "Initial",
                "is_active": True,
                "created_at": "2025-07-01T10:00:00",
            },
        ]
        resp = client.get("/api/prompts/versions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_list_passes_agent_filter(self, mock_svc, client):
        mock_svc.list_versions.return_value = []
        client.get("/api/prompts/versions?agent_id=agent_2")
        mock_svc.list_versions.assert_called_once_with(agent_id="agent_2")

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_list_default_params(self, mock_svc, client):
        mock_svc.list_versions.return_value = []
        client.get("/api/prompts/versions")
        mock_svc.list_versions.assert_called_once_with(agent_id=None)


class TestGetActiveVersion:

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_active_returns_version(self, mock_svc, client):
        mock_svc.get_active_version.return_value = {
            "id": "pv-1",
            "agent_id": "agent_2",
            "version": "1.0",
            "prompt_template": "Analyze...",
            "is_active": True,
            "created_at": "2025-07-01T10:00:00",
        }
        resp = client.get("/api/prompts/versions/active/agent_2")
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == "agent_2"

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_active_not_found_returns_404(self, mock_svc, client):
        mock_svc.get_active_version.return_value = None
        resp = client.get("/api/prompts/versions/active/agent_99")
        assert resp.status_code == 404


class TestCreateVersion:

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_create_returns_result(self, mock_svc, client):
        mock_svc.create_version.return_value = {
            "id": "pv-2",
            "agent_id": "agent_2",
            "version": "1.1",
            "is_active": True,
            "created_at": "2025-07-01T12:00:00",
        }
        resp = client.post("/api/prompts/versions", json={
            "agent_id": "agent_2",
            "version": "1.1",
            "prompt_template": "Updated analysis prompt...",
            "change_notes": "Refined scoring criteria",
        })
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.1"

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_create_passes_params(self, mock_svc, client):
        mock_svc.create_version.return_value = {"id": "pv-2"}
        client.post("/api/prompts/versions", json={
            "agent_id": "agent_3",
            "version": "2.0",
            "prompt_template": "Risk analysis prompt...",
            "change_notes": "Major rewrite",
            "calibration_config_version": "1.3",
        })
        mock_svc.create_version.assert_called_once_with(
            agent_id="agent_3",
            version="2.0",
            prompt_template="Risk analysis prompt...",
            change_notes="Major rewrite",
            calibration_config_version="1.3",
        )

    def test_create_missing_required_returns_422(self, client):
        resp = client.post("/api/prompts/versions", json={"agent_id": "agent_2"})
        assert resp.status_code == 422


class TestRollbackVersion:

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_rollback_returns_result(self, mock_svc, client):
        mock_svc.rollback_version.return_value = {
            "id": "pv-1",
            "agent_id": "agent_2",
            "version": "1.0",
            "is_active": True,
        }
        resp = client.post("/api/prompts/versions/rollback", json={
            "agent_id": "agent_2",
            "version_id": "pv-1",
        })
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_rollback_not_found_returns_404(self, mock_svc, client):
        mock_svc.rollback_version.side_effect = ValueError("Version not found: bad-id")
        resp = client.post("/api/prompts/versions/rollback", json={
            "agent_id": "agent_2",
            "version_id": "bad-id",
        })
        assert resp.status_code == 404

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_rollback_wrong_agent_returns_422(self, mock_svc, client):
        mock_svc.rollback_version.side_effect = ValueError(
            "Version pv-1 does not belong to agent agent_3"
        )
        resp = client.post("/api/prompts/versions/rollback", json={
            "agent_id": "agent_3",
            "version_id": "pv-1",
        })
        assert resp.status_code == 422


class TestDiffVersions:

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_diff_returns_text(self, mock_svc, client):
        mock_svc.diff_versions.return_value = (
            "--- agent_2 v1.0\n+++ agent_2 v1.1\n@@ -1 +1 @@\n-old\n+new\n"
        )
        resp = client.get("/api/prompts/versions/diff?version_id_a=pv-1&version_id_b=pv-2")
        assert resp.status_code == 200
        data = resp.json()
        assert "diff" in data
        assert "agent_2 v1.0" in data["diff"]

    @patch("sis.api.routes.admin.prompt_version_service")
    def test_diff_not_found_returns_404(self, mock_svc, client):
        mock_svc.diff_versions.side_effect = ValueError("Version A not found: bad-id")
        resp = client.get("/api/prompts/versions/diff?version_id_a=bad-id&version_id_b=pv-2")
        assert resp.status_code == 404

    def test_diff_missing_params_returns_422(self, client):
        resp = client.get("/api/prompts/versions/diff")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════
# Rep Scorecard — /api/scorecard/reps
# ═══════════════════════════════════════════════════════════════════════


class TestRepScorecard:

    @patch("sis.api.routes.admin.rep_scorecard_service")
    def test_scorecard_returns_list(self, mock_svc, client):
        mock_svc.get_rep_scorecard.return_value = [
            {
                "rep_name": "AE One",
                "total_accounts": 3,
                "scored_accounts": 2,
                "dimensions": {
                    "Stakeholder Engagement": 72.5,
                    "Objection Handling": 65.0,
                    "Commercial Progression": 55.0,
                    "Next-Step Setting": 80.0,
                },
                "overall_score": 68.1,
                "accounts": [],
            },
        ]
        resp = client.get("/api/scorecard/reps")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["rep_name"] == "AE One"
        assert data[0]["overall_score"] == 68.1

    @patch("sis.api.routes.admin.rep_scorecard_service")
    def test_scorecard_passes_filter(self, mock_svc, client):
        mock_svc.get_rep_scorecard.return_value = []
        client.get("/api/scorecard/reps?ae_owner=AE+One")
        mock_svc.get_rep_scorecard.assert_called_once_with(ae_owner="AE One")

    @patch("sis.api.routes.admin.rep_scorecard_service")
    def test_scorecard_default_params(self, mock_svc, client):
        mock_svc.get_rep_scorecard.return_value = []
        client.get("/api/scorecard/reps")
        mock_svc.get_rep_scorecard.assert_called_once_with(ae_owner=None)


# ═══════════════════════════════════════════════════════════════════════
# Forecast Data — /api/forecast/*
# ═══════════════════════════════════════════════════════════════════════


class TestForecastData:

    @patch("sis.api.routes.admin.forecast_data_service")
    def test_data_returns_list(self, mock_svc, client):
        mock_svc.load_forecast_data.return_value = [
            {
                "account_id": "acct-1",
                "account_name": "TestCorp",
                "mrr": 50000,
                "team_name": "Team Alpha",
                "ae_owner": "AE One",
                "ai_forecast": "Commit",
                "ic_forecast": "Best Case",
                "health_score": 80,
                "momentum": "Improving",
                "divergence": True,
            },
        ]
        resp = client.get("/api/forecast/data")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["divergence"] is True

    @patch("sis.api.routes.admin.forecast_data_service")
    def test_data_passes_team(self, mock_svc, client):
        mock_svc.load_forecast_data.return_value = []
        client.get("/api/forecast/data?team=Team+Alpha")
        mock_svc.load_forecast_data.assert_called_once_with(team="Team Alpha")

    @patch("sis.api.routes.admin.forecast_data_service")
    def test_data_default_params(self, mock_svc, client):
        mock_svc.load_forecast_data.return_value = []
        client.get("/api/forecast/data")
        mock_svc.load_forecast_data.assert_called_once_with(team=None)


class TestTeamNames:

    @patch("sis.api.routes.admin.forecast_data_service")
    def test_teams_returns_list(self, mock_svc, client):
        mock_svc.get_team_names.return_value = ["Team Alpha", "Team Beta"]
        resp = client.get("/api/forecast/teams")
        assert resp.status_code == 200
        assert resp.json() == ["Team Alpha", "Team Beta"]

    @patch("sis.api.routes.admin.forecast_data_service")
    def test_teams_empty(self, mock_svc, client):
        mock_svc.get_team_names.return_value = []
        resp = client.get("/api/forecast/teams")
        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════
# Export — /api/export/*
# ═══════════════════════════════════════════════════════════════════════


class TestExportDealBrief:

    @patch("sis.api.routes.export.export_service")
    def test_brief_returns_content(self, mock_svc, client):
        mock_svc.export_deal_brief.return_value = "# Deal Brief: TestCorp\n..."
        resp = client.get("/api/export/brief/acct-1")
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert "TestCorp" in data["content"]

    @patch("sis.api.routes.export.export_service")
    def test_brief_passes_params(self, mock_svc, client):
        mock_svc.export_deal_brief.return_value = "content"
        client.get("/api/export/brief/acct-1?format=narrative")
        mock_svc.export_deal_brief.assert_called_once_with(
            account_id="acct-1",
            format="narrative",
        )

    @patch("sis.api.routes.export.export_service")
    def test_brief_default_format(self, mock_svc, client):
        mock_svc.export_deal_brief.return_value = "content"
        client.get("/api/export/brief/acct-1")
        mock_svc.export_deal_brief.assert_called_once_with(
            account_id="acct-1",
            format="markdown",
        )


class TestExportForecast:

    @patch("sis.api.routes.export.export_service")
    def test_forecast_returns_content(self, mock_svc, client):
        mock_svc.export_forecast_report.return_value = "# Forecast Comparison\n..."
        resp = client.get("/api/export/forecast")
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert "Forecast" in data["content"]

    @patch("sis.api.routes.export.export_service")
    def test_forecast_passes_params(self, mock_svc, client):
        mock_svc.export_forecast_report.return_value = "content"
        client.get("/api/export/forecast?team=Team+Alpha&format=markdown")
        mock_svc.export_forecast_report.assert_called_once_with(
            team="Team Alpha",
            format="markdown",
        )

    @patch("sis.api.routes.export.export_service")
    def test_forecast_default_params(self, mock_svc, client):
        mock_svc.export_forecast_report.return_value = "content"
        client.get("/api/export/forecast")
        mock_svc.export_forecast_report.assert_called_once_with(
            team=None,
            format="markdown",
        )

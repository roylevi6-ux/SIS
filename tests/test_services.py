"""Test service layer — CRUD operations with seeded data."""

import json
import pytest

from sis.db.models import Account, DealAssessment, Transcript, ScoreFeedback


class TestAccountService:
    def test_list_accounts(self, seeded_db, mock_get_session):
        from sis.services.account_service import list_accounts
        accounts = list_accounts()
        assert len(accounts) == 3
        names = {a["account_name"] for a in accounts}
        assert "HealthyCorp" in names
        assert "AtRiskCo" in names
        assert "CriticalInc" in names

    def test_list_accounts_by_team(self, seeded_db, mock_get_session):
        from sis.services.account_service import list_accounts
        accounts = list_accounts(team="Team Alpha")
        assert len(accounts) == 2

    def test_get_account_detail(self, seeded_db, mock_get_session):
        from sis.services.account_service import get_account_detail
        detail = get_account_detail(seeded_db["healthy_id"])
        assert detail["account_name"] == "HealthyCorp"
        assert detail["assessment"] is not None
        assert detail["assessment"]["health_score"] == 82
        assert len(detail["transcripts"]) == 2

    def test_get_account_detail_not_found(self, seeded_db, mock_get_session):
        from sis.services.account_service import get_account_detail
        with pytest.raises(ValueError, match="Account not found"):
            get_account_detail("nonexistent-id")

    def test_set_ic_forecast_no_divergence(self, seeded_db, mock_get_session):
        from sis.services.account_service import set_ic_forecast
        result = set_ic_forecast(seeded_db["healthy_id"], "Commit")
        assert result["divergence_flag"] is False

    def test_set_ic_forecast_with_divergence(self, seeded_db, mock_get_session):
        from sis.services.account_service import set_ic_forecast
        result = set_ic_forecast(seeded_db["healthy_id"], "At Risk")
        assert result["divergence_flag"] is True
        assert "AI forecasts" in result["explanation"]

    def test_set_ic_forecast_invalid_category(self, seeded_db, mock_get_session):
        from sis.services.account_service import set_ic_forecast
        with pytest.raises(ValueError, match="Invalid category"):
            set_ic_forecast(seeded_db["healthy_id"], "InvalidCategory")

    def test_update_account(self, seeded_db, mock_get_session):
        from sis.services.account_service import update_account
        updated = update_account(seeded_db["healthy_id"], account_name="NewName")
        assert updated.account_name == "NewName"


class TestTranscriptService:
    def test_list_transcripts(self, seeded_db, mock_get_session):
        from sis.services.transcript_service import list_transcripts
        transcripts = list_transcripts(seeded_db["healthy_id"])
        assert len(transcripts) == 2

    def test_get_active_transcript_texts(self, seeded_db, mock_get_session):
        from sis.services.transcript_service import get_active_transcript_texts
        texts = get_active_transcript_texts(seeded_db["healthy_id"])
        assert len(texts) == 2
        assert "healthy" in texts[0].lower()


class TestFeedbackService:
    def test_submit_feedback(self, seeded_db, mock_get_session):
        from sis.services.feedback_service import submit_feedback
        result = submit_feedback(
            account_id=seeded_db["at_risk_id"],
            assessment_id=seeded_db["assessment_ids"][seeded_db["at_risk_id"]],
            author="AE Two",
            direction="too_low",
            reason="recent_change",
            free_text="New development",
        )
        assert result["direction"] == "too_low"
        assert result["author"] == "AE Two"

    def test_submit_feedback_invalid_direction(self, seeded_db, mock_get_session):
        from sis.services.feedback_service import submit_feedback
        with pytest.raises(ValueError, match="direction must be"):
            submit_feedback(
                account_id=seeded_db["healthy_id"],
                assessment_id=seeded_db["assessment_ids"][seeded_db["healthy_id"]],
                author="AE One", direction="invalid", reason="other",
            )

    def test_list_feedback(self, seeded_db, mock_get_session):
        from sis.services.feedback_service import list_feedback
        feedback = list_feedback()
        assert len(feedback) >= 2

    def test_resolve_feedback(self, seeded_db, mock_get_session):
        from sis.services.feedback_service import resolve_feedback
        result = resolve_feedback(
            feedback_id=seeded_db["feedback_ids"][0],
            resolution="accepted",
            notes="Verified off-channel activity",
            resolved_by="TL One",
        )
        assert result["resolution"] == "accepted"


class TestAnalysisService:
    def test_get_analysis_history(self, seeded_db, mock_get_session):
        from sis.services.analysis_service import get_analysis_history
        history = get_analysis_history(seeded_db["healthy_id"])
        assert len(history) == 1
        assert history[0]["status"] == "completed"

    def test_get_agent_analyses(self, seeded_db, mock_get_session):
        from sis.services.analysis_service import get_agent_analyses
        run_id = seeded_db["run_ids"][seeded_db["healthy_id"]]
        analyses = get_agent_analyses(run_id)
        assert len(analyses) == 9
        agent_ids = {a["agent_id"] for a in analyses}
        assert "agent_1" in agent_ids
        assert "agent_9" in agent_ids

    def test_get_latest_run_id(self, seeded_db, mock_get_session):
        from sis.services.analysis_service import get_latest_run_id
        run_id = get_latest_run_id(seeded_db["healthy_id"])
        assert run_id == seeded_db["run_ids"][seeded_db["healthy_id"]]


class TestDashboardService:
    def test_get_pipeline_overview(self, seeded_db, mock_get_session):
        from sis.services.dashboard_service import get_pipeline_overview
        overview = get_pipeline_overview()
        assert overview["total_deals"] == 3
        # 82 is healthy (>=70), 55 is at_risk (45-70), 35 is critical (<45)
        assert overview["summary"]["healthy_count"] == 1
        assert overview["summary"]["at_risk_count"] == 1
        assert overview["summary"]["critical_count"] == 1

    def test_get_pipeline_overview_by_team(self, seeded_db, mock_get_session):
        from sis.services.dashboard_service import get_pipeline_overview
        overview = get_pipeline_overview(team="Team Alpha")
        assert overview["total_deals"] == 2

    def test_get_team_rollup(self, seeded_db, mock_get_session):
        from sis.services.dashboard_service import get_team_rollup
        rollup = get_team_rollup()
        assert len(rollup) == 2
        team_names = {r["team_name"] for r in rollup}
        assert "Team Alpha" in team_names
        assert "Team Beta" in team_names

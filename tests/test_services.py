"""Test service layer — CRUD operations with seeded data."""

import json
import pytest

from sis.db.models import Account, DealAssessment, Transcript


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

    def test_get_team_rollup_hierarchy(self, seeded_db, mock_get_session):
        """Hierarchy rollup returns nested Team → Rep → Deals, sorted by critical count."""
        from sis.services.dashboard_service import get_team_rollup_hierarchy
        hierarchy = get_team_rollup_hierarchy()
        assert len(hierarchy) == 2

        # Verify structure: each team has reps, each rep has deals
        for team_entry in hierarchy:
            assert "reps" in team_entry
            assert "team_name" in team_entry
            for rep in team_entry["reps"]:
                assert "deals" in rep
                assert "rep_name" in rep

        # Risk-first sort: Team Beta (critical_count=1) should come before Team Alpha (critical_count=0)
        team_names = [t["team_name"] for t in hierarchy]
        assert team_names[0] == "Team Beta"
        assert team_names[1] == "Team Alpha"

        # Verify aggregates
        alpha = next(t for t in hierarchy if t["team_name"] == "Team Alpha")
        assert alpha["total_deals"] == 2
        assert alpha["healthy_count"] == 1
        assert alpha["at_risk_count"] == 1
        assert alpha["critical_count"] == 0

        beta = next(t for t in hierarchy if t["team_name"] == "Team Beta")
        assert beta["total_deals"] == 1
        assert beta["critical_count"] == 1

    def test_get_team_rollup_hierarchy_with_team_filter(self, seeded_db, mock_get_session):
        """Team filter narrows to one team."""
        from sis.services.dashboard_service import get_team_rollup_hierarchy
        hierarchy = get_team_rollup_hierarchy(team_id=seeded_db["team_alpha_id"])
        assert len(hierarchy) == 1
        assert hierarchy[0]["team_name"] == "Team Alpha"


class TestAccountServiceOwnerHierarchy:
    def test_create_account_with_owner_id_resolves_hierarchy(self, seeded_db, mock_get_session):
        """When owner_id is provided, ae_owner/team_lead/team_name auto-resolve."""
        from sis.services.account_service import create_account
        acct = create_account(
            name="NewDealCorp",
            owner_id=seeded_db["user_ids"]["ae1"],
        )
        assert acct.ae_owner == "AE One"
        assert acct.team_name == "Team Alpha"
        assert acct.team_lead == "TL One"
        assert acct.owner_id == seeded_db["user_ids"]["ae1"]

    def test_create_account_without_owner_id_no_auto_resolve(self, seeded_db, mock_get_session):
        """Without owner_id, hierarchy fields stay None."""
        from sis.services.account_service import create_account
        acct = create_account(name="ManualDeal")
        assert acct.ae_owner is None
        assert acct.team_name is None
        assert acct.team_lead is None
        assert acct.owner_id is None


class TestTeamServiceICs:
    def test_list_ics_with_hierarchy(self, seeded_db, mock_get_session):
        """Returns IC users with resolved team name and team lead."""
        from sis.services.team_service import list_ics_with_hierarchy
        ics = list_ics_with_hierarchy()
        assert len(ics) == 3  # 3 IC users in seed data
        names = {ic["name"] for ic in ics}
        assert "AE One" in names

        ae1 = next(ic for ic in ics if ic["name"] == "AE One")
        assert ae1["team_name"] == "Team Alpha"
        assert ae1["team_lead"] == "TL One"

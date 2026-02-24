"""Tests for /api/dashboard endpoints."""

from __future__ import annotations

from unittest.mock import patch


# ── GET /api/dashboard/pipeline ──────────────────────────────────────


class TestPipelineOverview:

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_pipeline_returns_overview(self, mock_svc, client, auth_headers):
        mock_svc.get_pipeline_overview.return_value = {
            "total_deals": 3,
            "healthy": [{"account_id": "a1", "account_name": "HealthyCo"}],
            "at_risk": [{"account_id": "a2", "account_name": "RiskyCo"}],
            "critical": [],
            "unscored": [{"account_id": "a3", "account_name": "NewCo"}],
            "summary": {
                "healthy_count": 1,
                "at_risk_count": 1,
                "critical_count": 0,
                "unscored_count": 1,
                "total_mrr_healthy": 50000,
                "total_mrr_at_risk": 30000,
                "total_mrr_critical": 0,
            },
        }
        resp = client.get("/api/dashboard/pipeline", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_deals"] == 3
        assert len(data["healthy"]) == 1
        assert data["summary"]["healthy_count"] == 1

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_pipeline_passes_team_filter(self, mock_svc, client, auth_headers):
        mock_svc.get_pipeline_overview.return_value = {"total_deals": 0}
        client.get("/api/dashboard/pipeline?team=Team+Alpha", headers=auth_headers)
        mock_svc.get_pipeline_overview.assert_called_once_with(team="Team Alpha", visible_user_ids=None)

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_pipeline_no_team_passes_none(self, mock_svc, client, auth_headers):
        mock_svc.get_pipeline_overview.return_value = {"total_deals": 0}
        client.get("/api/dashboard/pipeline", headers=auth_headers)
        mock_svc.get_pipeline_overview.assert_called_once_with(team=None, visible_user_ids=None)


# ── GET /api/dashboard/divergence ─────────────────────────────────────


class TestDivergenceReport:

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_divergence_returns_list(self, mock_svc, client, auth_headers):
        mock_svc.get_divergence_report.return_value = [
            {
                "account_id": "a1",
                "account_name": "DivergentCo",
                "mrr_estimate": 80000,
                "team_lead": "TL One",
                "ai_forecast_category": "Commit",
                "ic_forecast_category": "At Risk",
                "health_score": 65,
                "divergence_explanation": "AI sees stronger signals",
                "forecast_rationale": "Multiple positive indicators",
            },
        ]
        resp = client.get("/api/dashboard/divergence", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["account_name"] == "DivergentCo"

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_divergence_passes_team_filter(self, mock_svc, client, auth_headers):
        mock_svc.get_divergence_report.return_value = []
        client.get("/api/dashboard/divergence?team=Team+Beta", headers=auth_headers)
        mock_svc.get_divergence_report.assert_called_once_with(team="Team Beta", visible_user_ids=None)

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_divergence_empty(self, mock_svc, client, auth_headers):
        mock_svc.get_divergence_report.return_value = []
        resp = client.get("/api/dashboard/divergence", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ── GET /api/dashboard/team-rollup ────────────────────────────────────


class TestTeamRollup:

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_team_rollup_returns_list(self, mock_svc, client, auth_headers):
        mock_svc.get_team_rollup.return_value = [
            {
                "team_name": "Team Alpha",
                "total_deals": 5,
                "scored_deals": 4,
                "avg_health_score": 68.5,
                "healthy_count": 2,
                "at_risk_count": 1,
                "critical_count": 1,
                "total_mrr": 200000,
                "divergent_count": 1,
            },
        ]
        resp = client.get("/api/dashboard/team-rollup", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["team_name"] == "Team Alpha"
        assert data[0]["avg_health_score"] == 68.5

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_team_rollup_passes_team_filter(self, mock_svc, client, auth_headers):
        mock_svc.get_team_rollup.return_value = []
        client.get("/api/dashboard/team-rollup?team=Team+Alpha", headers=auth_headers)
        mock_svc.get_team_rollup.assert_called_once_with(team="Team Alpha", visible_user_ids=None)


# ── GET /api/dashboard/insights ───────────────────────────────────────


class TestPipelineInsights:

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_insights_returns_grouped(self, mock_svc, client, auth_headers):
        mock_svc.get_pipeline_insights.return_value = {
            "stuck": [{"account_id": "a1", "description": "Stuck deal"}],
            "improving": [],
            "declining": [{"account_id": "a2", "description": "Health dropped"}],
            "new_risks": [],
            "stale": [],
            "forecast_flips": [],
        }
        resp = client.get("/api/dashboard/insights", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["stuck"]) == 1
        assert len(data["declining"]) == 1
        assert data["improving"] == []

    @patch("sis.api.routes.dashboard.dashboard_service")
    def test_insights_all_empty(self, mock_svc, client, auth_headers):
        mock_svc.get_pipeline_insights.return_value = {
            "stuck": [],
            "improving": [],
            "declining": [],
            "new_risks": [],
            "stale": [],
            "forecast_flips": [],
        }
        resp = client.get("/api/dashboard/insights", headers=auth_headers)
        assert resp.status_code == 200
        for key in ("stuck", "improving", "declining", "new_risks", "stale", "forecast_flips"):
            assert resp.json()[key] == []


# ── GET /api/dashboard/trends/deals ───────────────────────────────────


class TestDealTrends:

    @patch("sis.api.routes.dashboard.trend_service")
    def test_deal_trends_returns_list(self, mock_svc, client, auth_headers):
        mock_svc.get_deal_trends.return_value = [
            {
                "account_id": "a1",
                "account_name": "TrendCo",
                "team_name": "Team Alpha",
                "ae_owner": "AE One",
                "data_points": [
                    {"date": "2025-06-01", "health_score": 60, "momentum": "Improving", "forecast": "Realistic"},
                    {"date": "2025-06-15", "health_score": 75, "momentum": "Improving", "forecast": "Commit"},
                ],
                "first_score": 60,
                "last_score": 75,
                "delta": 15,
                "trend_direction": "Improving",
            },
        ]
        resp = client.get("/api/dashboard/trends/deals", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["delta"] == 15
        assert data[0]["trend_direction"] == "Improving"

    @patch("sis.api.routes.dashboard.trend_service")
    def test_deal_trends_passes_params(self, mock_svc, client, auth_headers):
        mock_svc.get_deal_trends.return_value = []
        client.get("/api/dashboard/trends/deals?account_id=acct-5&weeks=8", headers=auth_headers)
        mock_svc.get_deal_trends.assert_called_once_with(account_id="acct-5", weeks=8)

    @patch("sis.api.routes.dashboard.trend_service")
    def test_deal_trends_default_params(self, mock_svc, client, auth_headers):
        mock_svc.get_deal_trends.return_value = []
        client.get("/api/dashboard/trends/deals", headers=auth_headers)
        mock_svc.get_deal_trends.assert_called_once_with(account_id=None, weeks=4)


# ── GET /api/dashboard/trends/teams ───────────────────────────────────


class TestTeamTrends:

    @patch("sis.api.routes.dashboard.trend_service")
    def test_team_trends_returns_list(self, mock_svc, client, auth_headers):
        deal_data = [
            {
                "account_id": "a1",
                "team_name": "Team Alpha",
                "last_score": 70,
                "delta": 5,
                "trend_direction": "Stable",
            },
        ]
        mock_svc.get_deal_trends.return_value = deal_data
        mock_svc.get_team_trends.return_value = [
            {
                "team_name": "Team Alpha",
                "deal_count": 1,
                "avg_health": 70.0,
                "avg_delta": 5.0,
                "improving_count": 0,
                "declining_count": 0,
                "stable_count": 1,
                "team_direction": "Stable",
            },
        ]
        resp = client.get("/api/dashboard/trends/teams", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["team_name"] == "Team Alpha"

    @patch("sis.api.routes.dashboard.trend_service")
    def test_team_trends_composes_deal_data(self, mock_svc, client, auth_headers):
        """Verifies that deal_trends data is fetched and passed to get_team_trends."""
        sentinel_deals = [{"account_id": "a1", "delta": 10}]
        mock_svc.get_deal_trends.return_value = sentinel_deals
        mock_svc.get_team_trends.return_value = []
        client.get("/api/dashboard/trends/teams?weeks=8", headers=auth_headers)
        mock_svc.get_deal_trends.assert_called_once_with(weeks=8)
        mock_svc.get_team_trends.assert_called_once_with(
            weeks=8, deal_trends=sentinel_deals
        )


# ── GET /api/dashboard/trends/portfolio ───────────────────────────────


class TestPortfolioSummary:

    @patch("sis.api.routes.dashboard.trend_service")
    def test_portfolio_returns_summary(self, mock_svc, client, auth_headers):
        mock_svc.get_deal_trends.return_value = [
            {"delta": 15, "trend_direction": "Improving"},
            {"delta": -5, "trend_direction": "Stable"},
        ]
        mock_svc.get_portfolio_summary.return_value = {
            "total_deals": 2,
            "improving": 1,
            "stable": 1,
            "declining": 0,
            "avg_delta": 5.0,
            "portfolio_direction": "Stable",
            "biggest_improver": {"account_name": "ImproverCo", "delta": 15, "last_score": 80},
            "biggest_decliner": None,
        }
        resp = client.get("/api/dashboard/trends/portfolio", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_deals"] == 2
        assert data["portfolio_direction"] == "Stable"
        assert data["biggest_improver"]["account_name"] == "ImproverCo"

    @patch("sis.api.routes.dashboard.trend_service")
    def test_portfolio_composes_deal_data(self, mock_svc, client, auth_headers):
        """Verifies that deal_trends data is fetched and passed to get_portfolio_summary."""
        sentinel_deals = [{"account_id": "a1", "delta": 10}]
        mock_svc.get_deal_trends.return_value = sentinel_deals
        mock_svc.get_portfolio_summary.return_value = {"total_deals": 0}
        client.get("/api/dashboard/trends/portfolio?weeks=12", headers=auth_headers)
        mock_svc.get_deal_trends.assert_called_once_with(weeks=12)
        mock_svc.get_portfolio_summary.assert_called_once_with(
            weeks=12, deal_trends=sentinel_deals
        )

    @patch("sis.api.routes.dashboard.trend_service")
    def test_portfolio_default_weeks(self, mock_svc, client, auth_headers):
        mock_svc.get_deal_trends.return_value = []
        mock_svc.get_portfolio_summary.return_value = {"total_deals": 0}
        client.get("/api/dashboard/trends/portfolio", headers=auth_headers)
        mock_svc.get_deal_trends.assert_called_once_with(weeks=4)
        mock_svc.get_portfolio_summary.assert_called_once_with(
            weeks=4, deal_trends=[]
        )

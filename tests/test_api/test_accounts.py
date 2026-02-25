"""Tests for /api/accounts endpoints."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


# ── Helpers ──────────────────────────────────────────────────────────


def _make_account_orm(
    id: str = "acct-1",
    account_name: str = "TestCorp",
    cp_estimate: float = 50000.0,
    team_lead: str = "TL One",
    ae_owner: str = "AE One",
    team_name: str = "Team Alpha",
):
    """Create a mock ORM Account object."""
    obj = MagicMock()
    obj.id = id
    obj.account_name = account_name
    obj.cp_estimate = cp_estimate
    obj.team_lead = team_lead
    obj.ae_owner = ae_owner
    obj.team_name = team_name
    return obj


# ── GET /api/accounts/ ──────────────────────────────────────────────


class TestListAccounts:

    @patch("sis.api.routes.accounts.account_service")
    def test_list_accounts_returns_200(self, mock_svc, client, auth_headers):
        mock_svc.list_accounts.return_value = [
            {"id": "1", "account_name": "Acme", "cp_estimate": 10000},
        ]
        resp = client.get("/api/accounts/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["account_name"] == "Acme"

    @patch("sis.api.routes.accounts.account_service")
    def test_list_accounts_passes_params(self, mock_svc, client, auth_headers):
        mock_svc.list_accounts.return_value = []
        client.get("/api/accounts/?sort_by=cp_estimate&team=Team+Alpha", headers=auth_headers)
        mock_svc.list_accounts.assert_called_once_with(
            team="Team Alpha", sort_by="cp_estimate", visible_user_ids=None
        )

    @patch("sis.api.routes.accounts.account_service")
    def test_list_accounts_default_params(self, mock_svc, client, auth_headers):
        mock_svc.list_accounts.return_value = []
        client.get("/api/accounts/", headers=auth_headers)
        mock_svc.list_accounts.assert_called_once_with(
            team=None, sort_by="account_name", visible_user_ids=None
        )


# ── GET /api/accounts/{account_id} ─────────────────────────────────


class TestGetAccount:

    @patch("sis.api.routes.accounts.account_service")
    def test_get_account_returns_detail(self, mock_svc, client, auth_headers):
        mock_svc.get_account_detail.return_value = {
            "id": "acct-1",
            "account_name": "TestCorp",
            "assessment": None,
            "transcripts": [],
        }
        resp = client.get("/api/accounts/acct-1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["account_name"] == "TestCorp"

    @patch("sis.api.routes.accounts.account_service")
    def test_get_account_not_found_returns_404(self, mock_svc, client, auth_headers):
        mock_svc.get_account_detail.side_effect = ValueError("Account not found: bad-id")
        resp = client.get("/api/accounts/bad-id", headers=auth_headers)
        assert resp.status_code == 404
        assert "Account not found" in resp.json()["detail"]


# ── POST /api/accounts/ ────────────────────────────────────────────


class TestCreateAccount:

    @patch("sis.api.routes.accounts.account_service")
    def test_create_account_returns_id(self, mock_svc, client, auth_headers):
        mock_svc.create_account.return_value = _make_account_orm(
            id="new-1", account_name="NewCo"
        )
        resp = client.post("/api/accounts/", json={
            "name": "NewCo",
            "cp_estimate": 25000.0,
            "team_lead": "TL One",
            "ae_owner": "AE One",
            "team_name": "Team Alpha",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "new-1"
        assert data["account_name"] == "NewCo"

    @patch("sis.api.routes.accounts.account_service")
    def test_create_account_passes_correct_params(self, mock_svc, client, auth_headers):
        mock_svc.create_account.return_value = _make_account_orm()
        client.post("/api/accounts/", json={
            "name": "TestCorp",
            "cp_estimate": 50000.0,
            "team_lead": "TL One",
            "ae_owner": "AE One",
            "team_name": "Team Alpha",
        }, headers=auth_headers)
        mock_svc.create_account.assert_called_once_with(
            name="TestCorp",
            cp_estimate=50000.0,
            team_lead="TL One",
            ae_owner="AE One",
            team="Team Alpha",
            owner_id=None,
            sf_stage=None,
            sf_forecast_category=None,
            sf_close_quarter=None,
        )

    @patch("sis.api.routes.accounts.account_service")
    def test_create_account_minimal_body(self, mock_svc, client, auth_headers):
        mock_svc.create_account.return_value = _make_account_orm(
            id="min-1", account_name="Minimal"
        )
        resp = client.post("/api/accounts/", json={"name": "Minimal"}, headers=auth_headers)
        assert resp.status_code == 200
        mock_svc.create_account.assert_called_once_with(
            name="Minimal", cp_estimate=None, team_lead=None, ae_owner=None, team=None, owner_id=None,
            sf_stage=None, sf_forecast_category=None, sf_close_quarter=None,
        )

    def test_create_account_missing_name_returns_422(self, client, auth_headers):
        resp = client.post("/api/accounts/", json={}, headers=auth_headers)
        assert resp.status_code == 422


# ── PUT /api/accounts/{account_id} ─────────────────────────────────


class TestUpdateAccount:

    @patch("sis.api.routes.accounts.account_service")
    def test_update_account_returns_updated(self, mock_svc, client, auth_headers):
        mock_svc.update_account.return_value = _make_account_orm(
            id="acct-1", account_name="UpdatedName"
        )
        resp = client.put("/api/accounts/acct-1", json={"name": "UpdatedName"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "acct-1"
        assert data["account_name"] == "UpdatedName"

    @patch("sis.api.routes.accounts.account_service")
    def test_update_account_maps_name_to_account_name(self, mock_svc, client, auth_headers):
        mock_svc.update_account.return_value = _make_account_orm()
        client.put("/api/accounts/acct-1", json={"name": "NewName", "cp_estimate": 99999}, headers=auth_headers)
        mock_svc.update_account.assert_called_once_with(
            "acct-1", account_name="NewName", cp_estimate=99999,
        )

    @patch("sis.api.routes.accounts.account_service")
    def test_update_account_not_found_returns_404(self, mock_svc, client, auth_headers):
        mock_svc.update_account.side_effect = ValueError("Account not found: bad-id")
        resp = client.put("/api/accounts/bad-id", json={"name": "X"}, headers=auth_headers)
        assert resp.status_code == 404

    @patch("sis.api.routes.accounts.account_service")
    def test_update_account_excludes_none_fields(self, mock_svc, client, auth_headers):
        mock_svc.update_account.return_value = _make_account_orm()
        client.put("/api/accounts/acct-1", json={"cp_estimate": 75000}, headers=auth_headers)
        mock_svc.update_account.assert_called_once_with("acct-1", cp_estimate=75000)


# ── POST /api/accounts/{account_id}/ic-forecast ────────────────────


class TestICForecast:

    @patch("sis.api.routes.accounts.account_service")
    def test_set_ic_forecast_returns_result(self, mock_svc, client, auth_headers):
        mock_svc.set_ic_forecast.return_value = {
            "divergence_flag": True,
            "explanation": "AI forecasts 'Commit' but IC forecasts 'At Risk'.",
        }
        resp = client.post(
            "/api/accounts/acct-1/ic-forecast",
            json={"category": "At Risk"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["divergence_flag"] is True
        assert "AI forecasts" in data["explanation"]

    @patch("sis.api.routes.accounts.account_service")
    def test_set_ic_forecast_not_found_returns_404(self, mock_svc, client, auth_headers):
        mock_svc.set_ic_forecast.side_effect = ValueError("Account not found: bad-id")
        resp = client.post(
            "/api/accounts/bad-id/ic-forecast",
            json={"category": "Commit"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @patch("sis.api.routes.accounts.account_service")
    def test_set_ic_forecast_invalid_category_returns_422(self, mock_svc, client, auth_headers):
        """Invalid category caught by Pydantic schema validator before hitting service."""
        resp = client.post(
            "/api/accounts/acct-1/ic-forecast",
            json={"category": "InvalidCat"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @patch("sis.api.routes.accounts.account_service")
    def test_set_ic_forecast_no_divergence(self, mock_svc, client, auth_headers):
        mock_svc.set_ic_forecast.return_value = {
            "divergence_flag": False,
            "explanation": None,
        }
        resp = client.post(
            "/api/accounts/acct-1/ic-forecast",
            json={"category": "Commit"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["divergence_flag"] is False

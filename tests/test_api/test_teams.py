"""Tests for team and user management API endpoints."""
from __future__ import annotations

from unittest.mock import patch


class TestTeamEndpoints:

    @patch("sis.api.routes.teams.team_service")
    def test_create_team(self, mock_svc, client, auth_headers):
        """Admin can create a team."""
        mock_svc.create_team.return_value = {"id": "t-1", "name": "Enterprise", "level": "team", "parent_id": None}
        res = client.post("/api/teams/", json={"name": "Enterprise", "level": "team"}, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Enterprise"
        assert "id" in data

    @patch("sis.api.routes.teams.team_service")
    def test_list_teams(self, mock_svc, client, auth_headers):
        """Admin can list teams."""
        mock_svc.list_teams.return_value = [
            {"id": "t-1", "name": "Root Org", "level": "org", "parent_id": None, "leader_id": None}
        ]
        res = client.get("/api/teams/", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @patch("sis.api.routes.teams.team_service")
    def test_create_user(self, mock_svc, client, auth_headers):
        """Admin can create a user."""
        mock_svc.create_user.return_value = {
            "id": "u-1", "name": "Alice", "email": "alice@new.com", "role": "ic", "team_id": None
        }
        res = client.post("/api/users/", json={"name": "Alice", "email": "alice@new.com", "role": "ic"}, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Alice"
        assert data["role"] == "ic"

    @patch("sis.api.routes.teams.team_service")
    def test_list_users(self, mock_svc, client, auth_headers):
        """Admin can list users."""
        mock_svc.list_users.return_value = [
            {"id": "u-1", "name": "Bob", "email": "bob@new.com", "role": "ic", "team_id": None}
        ]
        res = client.get("/api/users/", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_non_admin_cannot_create_team(self, client, ic_auth_headers):
        """IC role should be denied team creation."""
        res = client.post("/api/teams/", json={"name": "Rogue Team", "level": "team"}, headers=ic_auth_headers)
        assert res.status_code == 403


class TestICListing:

    @patch("sis.api.routes.teams.team_service")
    def test_list_ics_returns_data(self, mock_svc, client, auth_headers):
        mock_svc.list_ics_with_hierarchy.return_value = [
            {
                "id": "u1",
                "name": "AE One",
                "email": "ae1@co.com",
                "team_id": "t1",
                "team_name": "Team Alpha",
                "team_lead": "TL One",
            },
        ]
        resp = client.get("/api/users/ics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "AE One"
        assert data[0]["team_name"] == "Team Alpha"

    @patch("sis.api.routes.teams.team_service")
    def test_list_ics_non_admin_allowed(self, mock_svc, client, ic_auth_headers):
        """IC users (non-admin) should also be able to list ICs."""
        mock_svc.list_ics_with_hierarchy.return_value = []
        resp = client.get("/api/users/ics", headers=ic_auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

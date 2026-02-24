"""Integration test: scoping filters account lists by role."""
from __future__ import annotations

import uuid
from sis.db.models import User, Team, Account


def _uuid():
    return str(uuid.uuid4())


def test_ic_only_sees_own_accounts(mock_get_session):
    """IC's list_accounts should only return accounts they own."""
    session = mock_get_session

    # Create team structure
    team = Team(id=_uuid(), name="Team A", level="team")
    session.add(team)
    session.flush()

    ic1 = User(id=_uuid(), name="Alice", email="alice@t.com", role="ic", team_id=team.id)
    ic2 = User(id=_uuid(), name="Bob", email="bob@t.com", role="ic", team_id=team.id)
    session.add_all([ic1, ic2])
    session.flush()

    # Two accounts, one per IC
    acct1 = Account(id=_uuid(), account_name="Alice Corp", ae_owner="Alice", owner_id=ic1.id)
    acct2 = Account(id=_uuid(), account_name="Bob Inc", ae_owner="Bob", owner_id=ic2.id)
    session.add_all([acct1, acct2])
    session.flush()

    from sis.services.account_service import list_accounts
    result = list_accounts(visible_user_ids={ic1.id})
    names = [r["account_name"] for r in result]
    assert "Alice Corp" in names
    assert "Bob Inc" not in names


def test_tl_sees_team_accounts(mock_get_session):
    """TL should see all accounts owned by their team's ICs."""
    session = mock_get_session

    team = Team(id=_uuid(), name="Team A", level="team")
    session.add(team)
    session.flush()

    tl = User(id=_uuid(), name="Dan", email="dan@t.com", role="team_lead", team_id=team.id)
    ic1 = User(id=_uuid(), name="Alice", email="alice2@t.com", role="ic", team_id=team.id)
    ic2 = User(id=_uuid(), name="Bob", email="bob2@t.com", role="ic", team_id=team.id)
    session.add_all([tl, ic1, ic2])
    session.flush()

    acct1 = Account(id=_uuid(), account_name="Alice Corp 2", ae_owner="Alice", owner_id=ic1.id)
    acct2 = Account(id=_uuid(), account_name="Bob Inc 2", ae_owner="Bob", owner_id=ic2.id)
    session.add_all([acct1, acct2])
    session.flush()

    from sis.services.account_service import list_accounts
    result = list_accounts(visible_user_ids={tl.id, ic1.id, ic2.id})
    names = [r["account_name"] for r in result]
    assert "Alice Corp 2" in names
    assert "Bob Inc 2" in names


def test_no_scoping_returns_all(mock_get_session):
    """When visible_user_ids is None (admin/gm), return all accounts."""
    session = mock_get_session

    acct = Account(id=_uuid(), account_name="Unscoped Corp", ae_owner="Someone")
    session.add(acct)
    session.flush()

    from sis.services.account_service import list_accounts
    result = list_accounts(visible_user_ids=None)
    names = [r["account_name"] for r in result]
    assert "Unscoped Corp" in names

"""Test that dashboard endpoints respect scoping."""
from __future__ import annotations

import uuid
from sis.db.models import User, Team, Account


def _uuid():
    return str(uuid.uuid4())


def test_pipeline_overview_scoped(mock_get_session):
    """Pipeline overview should only show accounts visible to the user."""
    session = mock_get_session

    team = Team(id=_uuid(), name="Team A", level="team")
    session.add(team)
    session.flush()

    ic1 = User(id=_uuid(), name="Alice", email="alice_dash@t.com", role="ic", team_id=team.id)
    ic2 = User(id=_uuid(), name="Bob", email="bob_dash@t.com", role="ic", team_id=team.id)
    session.add_all([ic1, ic2])
    session.flush()

    acct1 = Account(id=_uuid(), account_name="Alice Deal", owner_id=ic1.id)
    acct2 = Account(id=_uuid(), account_name="Bob Deal", owner_id=ic2.id)
    session.add_all([acct1, acct2])
    session.flush()

    from sis.services.dashboard_service import get_pipeline_overview
    result = get_pipeline_overview(visible_user_ids={ic1.id})
    assert result["total_deals"] == 1
    assert result["unscored"][0]["account_name"] == "Alice Deal"


def test_pipeline_overview_unscoped(mock_get_session):
    """Pipeline overview with no scoping returns all deals."""
    session = mock_get_session

    acct1 = Account(id=_uuid(), account_name="Deal A")
    acct2 = Account(id=_uuid(), account_name="Deal B")
    session.add_all([acct1, acct2])
    session.flush()

    from sis.services.dashboard_service import get_pipeline_overview
    result = get_pipeline_overview(visible_user_ids=None)
    assert result["total_deals"] >= 2


def test_team_rollup_scoped(mock_get_session):
    """Team rollup should only show accounts visible to the user."""
    session = mock_get_session

    team = Team(id=_uuid(), name="Rollup Team", level="team")
    session.add(team)
    session.flush()

    ic1 = User(id=_uuid(), name="Rollup Alice", email="rallice@t.com", role="ic", team_id=team.id)
    session.add(ic1)
    session.flush()

    acct1 = Account(id=_uuid(), account_name="Rollup Deal", team_lead="TL X", owner_id=ic1.id)
    session.add(acct1)
    session.flush()

    from sis.services.dashboard_service import get_team_rollup
    result = get_team_rollup(visible_user_ids={ic1.id})
    total_deals = sum(r["total_deals"] for r in result)
    assert total_deals == 1

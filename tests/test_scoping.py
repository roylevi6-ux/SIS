"""Tests for role-based data scoping via get_visible_user_ids."""
from __future__ import annotations

import uuid
from sis.db.models import User, Team


def _uuid():
    return str(uuid.uuid4())


def _seed_org(session):
    """Seed a 3-level org: GM -> VP -> TL -> ICs.

    Returns dict of all user objects keyed by name.
    """
    # Root org
    root = Team(id=_uuid(), name="Sales Org", level="org")
    session.add(root)
    session.flush()

    # GM
    gm = User(id=_uuid(), name="Roy", email="roy@test.com", role="admin")
    session.add(gm)
    session.flush()
    root.leader_id = gm.id
    session.flush()

    # Division East
    div_east = Team(id=_uuid(), name="Sales East", parent_id=root.id, level="division")
    session.add(div_east)
    session.flush()

    vp_east = User(id=_uuid(), name="Sarah", email="sarah@test.com", role="vp", team_id=div_east.id)
    session.add(vp_east)
    session.flush()
    div_east.leader_id = vp_east.id
    session.flush()

    # Team Enterprise under East
    team_ent = Team(id=_uuid(), name="Enterprise", parent_id=div_east.id, level="team")
    session.add(team_ent)
    session.flush()

    tl_dan = User(id=_uuid(), name="Dan", email="dan@test.com", role="team_lead", team_id=team_ent.id)
    session.add(tl_dan)
    session.flush()
    team_ent.leader_id = tl_dan.id

    ic_alice = User(id=_uuid(), name="Alice", email="alice@test.com", role="ic", team_id=team_ent.id)
    ic_bob = User(id=_uuid(), name="Bob", email="bob@test.com", role="ic", team_id=team_ent.id)
    session.add_all([ic_alice, ic_bob])
    session.flush()

    # Team Mid-Market under East
    team_mm = Team(id=_uuid(), name="Mid-Market", parent_id=div_east.id, level="team")
    session.add(team_mm)
    session.flush()

    tl_maya = User(id=_uuid(), name="Maya", email="maya@test.com", role="team_lead", team_id=team_mm.id)
    session.add(tl_maya)
    session.flush()
    team_mm.leader_id = tl_maya.id

    ic_charlie = User(id=_uuid(), name="Charlie", email="charlie@test.com", role="ic", team_id=team_mm.id)
    session.add(ic_charlie)
    session.flush()

    # Division West (separate VP)
    div_west = Team(id=_uuid(), name="Sales West", parent_id=root.id, level="division")
    session.add(div_west)
    session.flush()

    vp_west = User(id=_uuid(), name="Jake", email="jake@test.com", role="vp", team_id=div_west.id)
    session.add(vp_west)
    session.flush()
    div_west.leader_id = vp_west.id

    team_smb = Team(id=_uuid(), name="SMB", parent_id=div_west.id, level="team")
    session.add(team_smb)
    session.flush()

    tl_west = User(id=_uuid(), name="Liam", email="liam@test.com", role="team_lead", team_id=team_smb.id)
    session.add(tl_west)
    session.flush()
    team_smb.leader_id = tl_west.id

    ic_west = User(id=_uuid(), name="Eve", email="eve@test.com", role="ic", team_id=team_smb.id)
    session.add(ic_west)
    session.flush()

    return {
        "gm": gm, "vp_east": vp_east, "vp_west": vp_west,
        "tl_dan": tl_dan, "tl_maya": tl_maya, "tl_west": tl_west,
        "ic_alice": ic_alice, "ic_bob": ic_bob, "ic_charlie": ic_charlie, "ic_west": ic_west,
    }


def test_ic_sees_only_self(mock_get_session):
    """IC should only see their own user ID."""
    session = mock_get_session
    users = _seed_org(session)

    from sis.services.scoping_service import get_visible_user_ids
    visible = get_visible_user_ids(users["ic_alice"], session)
    assert visible == {users["ic_alice"].id}


def test_tl_sees_own_team(mock_get_session):
    """TL should see all ICs on their team plus themselves."""
    session = mock_get_session
    users = _seed_org(session)

    from sis.services.scoping_service import get_visible_user_ids
    visible = get_visible_user_ids(users["tl_dan"], session)
    expected = {users["tl_dan"].id, users["ic_alice"].id, users["ic_bob"].id}
    assert visible == expected


def test_vp_sees_all_teams_in_division(mock_get_session):
    """VP should see all users across all teams under their division."""
    session = mock_get_session
    users = _seed_org(session)

    from sis.services.scoping_service import get_visible_user_ids
    visible = get_visible_user_ids(users["vp_east"], session)
    expected = {
        users["vp_east"].id,
        users["tl_dan"].id, users["ic_alice"].id, users["ic_bob"].id,
        users["tl_maya"].id, users["ic_charlie"].id,
    }
    assert visible == expected


def test_vp_does_not_see_other_vps_teams(mock_get_session):
    """VP East should NOT see VP West's users."""
    session = mock_get_session
    users = _seed_org(session)

    from sis.services.scoping_service import get_visible_user_ids
    visible = get_visible_user_ids(users["vp_east"], session)
    assert users["ic_west"].id not in visible
    assert users["tl_west"].id not in visible


def test_gm_sees_everything(mock_get_session):
    """GM (admin) should see all users."""
    session = mock_get_session
    users = _seed_org(session)

    from sis.services.scoping_service import get_visible_user_ids
    visible = get_visible_user_ids(users["gm"], session)
    all_ids = {u.id for u in users.values()}
    assert visible == all_ids

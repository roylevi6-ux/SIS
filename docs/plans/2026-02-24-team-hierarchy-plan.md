# Team Hierarchy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add User & Team tables with a parent_id tree to support IC → TL → VP → GM → Admin hierarchy with role-based data scoping.

**Architecture:** Two new SQLAlchemy models (User, Team) with a self-referencing tree on Team. A `get_visible_user_ids()` helper walks the tree to determine data scoping. Existing service-layer functions accept a `visible_ids` param instead of the old `team` string. Frontend login gets 5 roles, sidebar gets role-based filtering, and dashboard gets VP/GM roll-up cards.

**Tech Stack:** SQLAlchemy 2.0, SQLite (WAL), FastAPI, Pydantic, pytest, Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4

---

## Task 1: Add User and Team SQLAlchemy Models

**Files:**
- Modify: `sis/db/models.py` (add User and Team classes after Base, before Account)
- Test: `tests/test_models.py` (add model creation tests)

**Step 1: Write the failing test**

Add to `tests/test_models.py`:

```python
def test_user_and_team_models(session):
    """User and Team models can be created with tree relationships."""
    from sis.db.models import User, Team

    # Create root team
    root = Team(name="Sales Org", level="org")
    session.add(root)
    session.flush()

    # Create GM user
    gm = User(name="Roy", email="roy@sis.com", role="admin")
    session.add(gm)
    session.flush()

    # Set leader
    root.leader_id = gm.id
    session.flush()

    # Create division under root
    division = Team(name="Sales East", parent_id=root.id, level="division")
    session.add(division)
    session.flush()

    # Create VP user on division
    vp = User(name="Sarah", email="sarah@sis.com", role="vp", team_id=division.id)
    session.add(vp)
    session.flush()
    division.leader_id = vp.id
    session.flush()

    # Create team under division
    team = Team(name="Enterprise", parent_id=division.id, level="team")
    session.add(team)
    session.flush()

    # Create TL and IC
    tl = User(name="Dan", email="dan@sis.com", role="team_lead", team_id=team.id)
    session.add(tl)
    session.flush()
    team.leader_id = tl.id

    ic = User(name="Alice", email="alice@sis.com", role="ic", team_id=team.id)
    session.add(ic)
    session.flush()

    assert gm.role == "admin"
    assert vp.team_id == division.id
    assert team.parent_id == division.id
    assert division.parent_id == root.id
    assert ic.team_id == team.id
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_models.py::test_user_and_team_models -v`
Expected: FAIL with ImportError (User and Team don't exist yet)

**Step 3: Write minimal implementation**

Add to `sis/db/models.py` — after the `Base` class and before the `Account` class:

```python
# ─── users ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Text, primary_key=True, default=_uuid)
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=False, unique=True)
    role = Column(Text, nullable=False)  # admin | gm | vp | team_lead | ic
    team_id = Column(Text, ForeignKey("teams.id"), nullable=True)
    is_active = Column(Integer, default=1)  # boolean
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    team = relationship("Team", foreign_keys=[team_id], back_populates="members")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )


# ─── teams ─────────────────────────────────────────────────────────────

class Team(Base):
    __tablename__ = "teams"

    id = Column(Text, primary_key=True, default=_uuid)
    name = Column(Text, nullable=False)
    parent_id = Column(Text, ForeignKey("teams.id"), nullable=True)
    leader_id = Column(Text, ForeignKey("users.id", use_alter=True), nullable=True)
    level = Column(Text, nullable=False)  # org | division | team
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    parent = relationship("Team", remote_side=[id], backref="children")
    leader = relationship("User", foreign_keys=[leader_id])
    members = relationship("User", foreign_keys=[User.team_id], back_populates="team")

    __table_args__ = (
        Index("ix_teams_parent", "parent_id"),
        Index("ix_teams_level", "level"),
    )
```

Also add `owner_id` column to the `Account` class:

```python
    owner_id = Column(Text, ForeignKey("users.id"), nullable=True)
```

And add the relationship:

```python
    owner = relationship("User", foreign_keys=[owner_id])
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_models.py::test_user_and_team_models -v`
Expected: PASS

**Step 5: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add sis/db/models.py tests/test_models.py
git commit -m "feat: add User and Team models with tree hierarchy"
```

---

## Task 2: Add `get_visible_user_ids()` Scoping Helper

**Files:**
- Create: `sis/services/scoping_service.py`
- Test: `tests/test_scoping.py`

**Step 1: Write the failing test**

Create `tests/test_scoping.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_scoping.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Write minimal implementation**

Create `sis/services/scoping_service.py`:

```python
"""Role-based data scoping — determines which user IDs a given user can see."""

from __future__ import annotations

from sqlalchemy.orm import Session

from sis.db.models import User, Team


def get_visible_user_ids(current_user: User, session: Session) -> set[str]:
    """Return the set of user IDs that current_user is allowed to see.

    Scoping rules:
    - IC: only their own ID
    - team_lead: all members of their team (including themselves)
    - vp: all members of all teams under their division (including themselves)
    - gm / admin: all active users
    """
    role = current_user.role

    if role in ("admin", "gm"):
        # See everything
        return {u.id for u in session.query(User.id).filter(User.is_active == 1).all()}

    if role == "ic":
        return {current_user.id}

    if role == "team_lead":
        # All users on the same team
        if not current_user.team_id:
            return {current_user.id}
        members = (
            session.query(User.id)
            .filter(User.team_id == current_user.team_id, User.is_active == 1)
            .all()
        )
        return {m.id for m in members}

    if role == "vp":
        # Find the division this VP leads
        division = (
            session.query(Team)
            .filter(Team.leader_id == current_user.id, Team.level == "division")
            .first()
        )
        if not division:
            # VP not leading a division — fall back to team membership
            if current_user.team_id:
                return _get_team_subtree_user_ids(current_user.team_id, session) | {current_user.id}
            return {current_user.id}

        # Get all teams under this division (recursive)
        return _get_team_subtree_user_ids(division.id, session) | {current_user.id}

    # Unknown role — minimal access
    return {current_user.id}


def _get_team_subtree_user_ids(team_id: str, session: Session) -> set[str]:
    """Recursively collect all user IDs in a team and its sub-teams."""
    result = set()

    # Users directly on this team
    members = (
        session.query(User.id)
        .filter(User.team_id == team_id, User.is_active == 1)
        .all()
    )
    result.update(m.id for m in members)

    # Child teams
    children = session.query(Team.id).filter(Team.parent_id == team_id).all()
    for child in children:
        result.update(_get_team_subtree_user_ids(child.id, session))

    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_scoping.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add sis/services/scoping_service.py tests/test_scoping.py
git commit -m "feat: add get_visible_user_ids scoping service with tree traversal"
```

---

## Task 3: Update Auth — Add VP and GM Roles

**Files:**
- Modify: `sis/api/auth.py:36` — add `"vp"` and `"gm"` to `VALID_ROLES`
- Modify: `sis/api/auth.py:42` — add `user_id` to JWT payload
- Modify: `sis/api/deps.py:22-43` — `get_current_user` looks up User from DB
- Modify: `sis/api/routes/auth.py:47-59` — login creates/finds User, returns `user_id`
- Test: `tests/test_api/test_auth.py` — add tests for new roles

**Step 1: Write the failing test**

Add to `tests/test_api/test_auth.py`:

```python
def test_login_vp_role(client):
    """VP role should be accepted at login."""
    res = client.post("/api/auth/login", json={"username": "VP Test", "role": "vp"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "vp"
    assert "token" in data
    assert "user_id" in data


def test_login_gm_role(client):
    """GM role should be accepted at login."""
    res = client.post("/api/auth/login", json={"username": "GM Test", "role": "gm"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "gm"
    assert "user_id" in data
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_api/test_auth.py::test_login_vp_role tests/test_api/test_auth.py::test_login_gm_role -v`
Expected: FAIL (422 invalid role for vp/gm, no user_id in response)

**Step 3: Write minimal implementation**

In `sis/api/auth.py:36`, change:
```python
VALID_ROLES = {"admin", "gm", "vp", "team_lead", "ic"}
```

In `sis/api/auth.py`, update `create_token` to accept optional `user_id`:
```python
def create_token(username: str, role: str, user_id: str | None = None) -> str:
    ...
    payload = {
        "sub": username,
        "role": role,
        "user_id": user_id,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": now,
    }
    ...
```

In `sis/api/auth.py`, update `decode_token` to return `user_id`:
```python
    return {"sub": sub, "role": role, "user_id": payload.get("user_id")}
```

In `sis/api/routes/auth.py`, update `LoginResponse` and `login`:
```python
class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    user_id: str | None = None


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{body.role}'. Must be one of: {sorted(VALID_ROLES)}",
        )
    # For POC: find or create User record
    from sis.db.session import get_session
    from sis.db.models import User

    with get_session() as session:
        user = session.query(User).filter_by(email=body.username).first()
        if not user:
            user = User(name=body.username, email=body.username, role=body.role)
            session.add(user)
            session.flush()
        user_id = user.id

    token = create_token(body.username, body.role, user_id=user_id)
    return LoginResponse(token=token, username=body.username, role=body.role, user_id=user_id)
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_api/test_auth.py -v`
Expected: All auth tests PASS

**Step 5: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add sis/api/auth.py sis/api/deps.py sis/api/routes/auth.py tests/test_api/test_auth.py
git commit -m "feat: add vp and gm roles to auth, include user_id in JWT"
```

---

## Task 4: Wire Data Scoping into Account Service

**Files:**
- Modify: `sis/services/account_service.py:116-174` — `list_accounts` accepts `visible_user_ids`
- Modify: `sis/api/routes/accounts.py:20-27` — inject scoping
- Test: `tests/test_scoping_integration.py`

**Step 1: Write the failing test**

Create `tests/test_scoping_integration.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_scoping_integration.py -v`
Expected: FAIL (list_accounts doesn't accept visible_user_ids)

**Step 3: Write minimal implementation**

In `sis/services/account_service.py`, update `list_accounts`:

```python
def list_accounts(
    team: Optional[str] = None,
    sort_by: str = "account_name",
    visible_user_ids: Optional[set[str]] = None,
) -> list[dict]:
    """List accounts with latest assessment summary.

    Args:
        team: Legacy team name filter (optional, backward compat)
        sort_by: Sort column
        visible_user_ids: If provided, only return accounts where owner_id is in this set.
                          None means no scoping (admin/gm sees all).
    """
    with get_session() as session:
        query = session.query(Account)
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        elif team:
            query = query.filter_by(team_name=team)
        ...  # rest unchanged
```

In `sis/api/routes/accounts.py`, update `list_accounts` endpoint to compute scoping:

```python
from sis.services.scoping_service import get_visible_user_ids
from sis.db.models import User

@router.get("/")
def list_accounts(
    sort_by: str = "account_name",
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List accounts scoped to the current user's role."""
    visible_ids = None
    if user.get("user_id"):
        db_user = db.query(User).filter_by(id=user["user_id"]).first()
        if db_user and db_user.role not in ("admin", "gm"):
            visible_ids = get_visible_user_ids(db_user, db)
    return account_service.list_accounts(team=team, sort_by=sort_by, visible_user_ids=visible_ids)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_scoping_integration.py -v`
Expected: All 3 tests PASS

**Step 5: Run full test suite for regressions**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short`
Expected: All existing tests still pass (list_accounts with no visible_user_ids defaults to unscoped)

**Step 6: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add sis/services/account_service.py sis/api/routes/accounts.py tests/test_scoping_integration.py
git commit -m "feat: wire data scoping into account service and API route"
```

---

## Task 5: Wire Data Scoping into Dashboard Service

**Files:**
- Modify: `sis/services/dashboard_service.py` — add `visible_user_ids` to `get_pipeline_overview`, `get_divergence_report`, `get_team_rollup`
- Modify: `sis/api/routes/dashboard.py` — inject scoping into all endpoints
- Test: `tests/test_dashboard_scoping.py`

**Step 1: Write the failing test**

Create `tests/test_dashboard_scoping.py`:

```python
"""Test that dashboard endpoints respect scoping."""
from __future__ import annotations

import uuid
from sis.db.models import User, Team, Account, DealAssessment, AnalysisRun
import json


def _uuid():
    return str(uuid.uuid4())


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_dashboard_scoping.py -v`
Expected: FAIL (get_pipeline_overview doesn't accept visible_user_ids)

**Step 3: Write minimal implementation**

Update each function in `sis/services/dashboard_service.py` to accept `visible_user_ids: Optional[set[str]] = None`. For `get_pipeline_overview`:

```python
def get_pipeline_overview(team: Optional[str] = None, visible_user_ids: Optional[set[str]] = None) -> dict:
    with get_session() as session:
        query = session.query(Account)
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        elif team:
            query = query.filter_by(team_name=team)
        accounts = query.all()
        ...  # rest unchanged
```

Apply the same pattern to `get_divergence_report` and `get_team_rollup`.

Update `sis/api/routes/dashboard.py` — add scoping to each endpoint:

```python
from sqlalchemy.orm import Session
from sis.api.deps import get_db
from sis.services.scoping_service import get_visible_user_ids
from sis.db.models import User

def _resolve_scoping(user: dict, db: Session) -> set[str] | None:
    """Compute visible user IDs from JWT user dict. None = no restriction."""
    user_id = user.get("user_id")
    if not user_id:
        return None
    db_user = db.query(User).filter_by(id=user_id).first()
    if not db_user or db_user.role in ("admin", "gm"):
        return None
    return get_visible_user_ids(db_user, db)
```

Then use `_resolve_scoping(user, db)` in each endpoint.

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_dashboard_scoping.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short`
Expected: All existing tests pass

**Step 6: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add sis/services/dashboard_service.py sis/api/routes/dashboard.py tests/test_dashboard_scoping.py
git commit -m "feat: wire data scoping into dashboard service and API routes"
```

---

## Task 6: Add User & Team CRUD API Endpoints

**Files:**
- Create: `sis/services/team_service.py`
- Create: `sis/api/routes/teams.py`
- Create: `sis/api/schemas/teams.py`
- Modify: `sis/api/main.py` — register new router
- Test: `tests/test_api/test_teams.py`

**Step 1: Write the failing test**

Create `tests/test_api/test_teams.py`:

```python
"""Tests for team and user management API endpoints."""

def test_create_team(client, auth_headers, mock_get_session):
    """Admin can create a team."""
    res = client.post("/api/teams/", json={"name": "Enterprise", "level": "team"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Enterprise"
    assert "id" in data


def test_list_teams(client, auth_headers, mock_get_session):
    """Admin can list teams as tree."""
    # Create a team first
    client.post("/api/teams/", json={"name": "Root Org", "level": "org"}, headers=auth_headers)
    res = client.get("/api/teams/", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_create_user(client, auth_headers, mock_get_session):
    """Admin can create a user."""
    res = client.post("/api/users/", json={"name": "Alice", "email": "alice@new.com", "role": "ic"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Alice"
    assert data["role"] == "ic"


def test_list_users(client, auth_headers, mock_get_session):
    """Admin can list users."""
    client.post("/api/users/", json={"name": "Bob", "email": "bob@new.com", "role": "ic"}, headers=auth_headers)
    res = client.get("/api/users/", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_non_admin_cannot_create_team(client, ic_auth_headers, mock_get_session):
    """IC role should be denied team creation."""
    res = client.post("/api/teams/", json={"name": "Rogue Team", "level": "team"}, headers=ic_auth_headers)
    assert res.status_code == 403
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_api/test_teams.py -v`
Expected: FAIL (404 — routes don't exist)

**Step 3: Write minimal implementation**

Create `sis/api/schemas/teams.py`:

```python
"""Pydantic schemas for team & user management."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[str] = None
    level: str = Field(..., pattern="^(org|division|team)$")
    leader_id: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    leader_id: Optional[str] = None


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., pattern="^(admin|gm|vp|team_lead|ic)$")
    team_id: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    team_id: Optional[str] = None
    is_active: Optional[bool] = None
```

Create `sis/services/team_service.py`:

```python
"""Team & User CRUD service."""
from __future__ import annotations
from typing import Optional
from sis.db.session import get_session
from sis.db.models import User, Team


def create_team(name: str, level: str, parent_id: Optional[str] = None, leader_id: Optional[str] = None) -> dict:
    with get_session() as session:
        team = Team(name=name, level=level, parent_id=parent_id, leader_id=leader_id)
        session.add(team)
        session.flush()
        return {"id": team.id, "name": team.name, "level": team.level, "parent_id": team.parent_id}


def list_teams() -> list[dict]:
    with get_session() as session:
        teams = session.query(Team).order_by(Team.name).all()
        return [
            {
                "id": t.id, "name": t.name, "level": t.level,
                "parent_id": t.parent_id, "leader_id": t.leader_id,
            }
            for t in teams
        ]


def update_team(team_id: str, **fields) -> dict:
    with get_session() as session:
        team = session.query(Team).filter_by(id=team_id).one_or_none()
        if not team:
            raise ValueError(f"Team not found: {team_id}")
        for key, value in fields.items():
            if hasattr(team, key):
                setattr(team, key, value)
        session.flush()
        return {"id": team.id, "name": team.name, "level": team.level, "parent_id": team.parent_id}


def get_team_members(team_id: str) -> list[dict]:
    with get_session() as session:
        members = session.query(User).filter_by(team_id=team_id, is_active=1).all()
        return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role} for u in members]


def create_user(name: str, email: str, role: str, team_id: Optional[str] = None) -> dict:
    with get_session() as session:
        user = User(name=name, email=email, role=role, team_id=team_id)
        session.add(user)
        session.flush()
        return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "team_id": user.team_id}


def list_users() -> list[dict]:
    with get_session() as session:
        users = session.query(User).filter(User.is_active == 1).order_by(User.name).all()
        return [
            {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "team_id": u.team_id}
            for u in users
        ]


def update_user(user_id: str, **fields) -> dict:
    with get_session() as session:
        user = session.query(User).filter_by(id=user_id).one_or_none()
        if not user:
            raise ValueError(f"User not found: {user_id}")
        for key, value in fields.items():
            if hasattr(user, key) and key != "id":
                setattr(user, key, value)
        session.flush()
        return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "team_id": user.team_id}
```

Create `sis/api/routes/teams.py`:

```python
"""Team & User management API routes — admin only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sis.api.deps import get_current_user, get_db
from sis.services import team_service
from sis.api.schemas.teams import TeamCreate, TeamUpdate, UserCreate, UserUpdate

router = APIRouter(tags=["teams"])


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Team endpoints ───────────────────────────────────────────────────

@router.get("/api/teams/")
def list_teams(user: dict = Depends(get_current_user)):
    return team_service.list_teams()


@router.post("/api/teams/")
def create_team(body: TeamCreate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    return team_service.create_team(name=body.name, level=body.level, parent_id=body.parent_id, leader_id=body.leader_id)


@router.put("/api/teams/{team_id}")
def update_team(team_id: str, body: TeamUpdate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    fields = body.model_dump(exclude_none=True)
    try:
        return team_service.update_team(team_id, **fields)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/teams/{team_id}/members")
def get_team_members(team_id: str, user: dict = Depends(get_current_user)):
    return team_service.get_team_members(team_id)


# ── User endpoints ───────────────────────────────────────────────────

@router.get("/api/users/")
def list_users(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return team_service.list_users()


@router.post("/api/users/")
def create_user(body: UserCreate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    return team_service.create_user(name=body.name, email=body.email, role=body.role, team_id=body.team_id)


@router.put("/api/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    fields = body.model_dump(exclude_none=True)
    try:
        return team_service.update_user(user_id, **fields)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

Register in `sis/api/main.py` — add:
```python
from sis.api.routes.teams import router as teams_router
app.include_router(teams_router)
```

Also add `"sis.services.team_service.get_session"` to the patch targets in `tests/conftest.py`.

**Step 4: Run tests**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_api/test_teams.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add sis/api/schemas/teams.py sis/services/team_service.py sis/api/routes/teams.py sis/api/main.py tests/test_api/test_teams.py tests/conftest.py
git commit -m "feat: add team and user CRUD API endpoints (admin only)"
```

---

## Task 7: Update Frontend — Auth Types + Login Page

**Files:**
- Modify: `frontend/src/lib/auth.tsx:14-17` — add VP, GM to AuthUser role union
- Modify: `frontend/src/app/login/page.tsx:23-27` — add VP, GM, Admin to role dropdown
- Modify: `frontend/src/lib/auth.tsx:74-79` — store user_id from login response

**Step 1: Update AuthUser type**

In `frontend/src/lib/auth.tsx`, change:

```typescript
export interface AuthUser {
  username: string;
  role: 'admin' | 'gm' | 'vp' | 'team_lead' | 'ic';
  userId?: string;
}
```

Update `login` callback to store `userId`:
```typescript
const authUser: AuthUser = { username: data.username, role: data.role, userId: data.user_id };
```

**Step 2: Update login page**

In `frontend/src/app/login/page.tsx`, change `ROLES`:

```typescript
const ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'gm', label: 'General Manager' },
  { value: 'vp', label: 'VP Sales' },
  { value: 'team_lead', label: 'Team Lead' },
  { value: 'ic', label: 'Individual Contributor' },
] as const;
```

**Step 3: Update sidebar role labels**

In `frontend/src/components/sidebar.tsx`, update `SidebarUserFooter`:

```typescript
const roleLabels: Record<string, string> = {
  admin: 'Admin',
  gm: 'General Manager',
  vp: 'VP Sales',
  team_lead: 'Team Lead',
  ic: 'IC',
};
const roleLabel = roleLabels[user.role] || user.role;
```

**Step 4: Verify frontend compiles**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npx next build`
Expected: Build succeeds with no type errors

**Step 5: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/lib/auth.tsx frontend/src/app/login/page.tsx frontend/src/components/sidebar.tsx
git commit -m "feat: add VP, GM, Admin roles to frontend login and sidebar"
```

---

## Task 8: Add `usePermissions` Hook + Role-Based Sidebar

**Files:**
- Create: `frontend/src/lib/permissions.ts`
- Modify: `frontend/src/components/sidebar.tsx` — filter nav groups by role

**Step 1: Create permissions hook**

Create `frontend/src/lib/permissions.ts`:

```typescript
import { useAuth } from './auth';

type Role = 'admin' | 'gm' | 'vp' | 'team_lead' | 'ic';

const ROLE_RANK: Record<Role, number> = {
  ic: 0,
  team_lead: 1,
  vp: 2,
  gm: 3,
  admin: 4,
};

export function usePermissions() {
  const { user } = useAuth();
  const role = (user?.role ?? 'ic') as Role;

  return {
    role,
    isAdmin: role === 'admin',
    isGmOrAbove: ROLE_RANK[role] >= ROLE_RANK.gm,
    isVpOrAbove: ROLE_RANK[role] >= ROLE_RANK.vp,
    isTlOrAbove: ROLE_RANK[role] >= ROLE_RANK.team_lead,
    canManageTeams: role === 'admin',
    canSeeAllDeals: role === 'admin' || role === 'gm',
    canSeeRollup: ROLE_RANK[role] >= ROLE_RANK.vp,
  };
}
```

**Step 2: Filter sidebar by role**

In `frontend/src/components/sidebar.tsx`, update `NAV_GROUPS` items to include a `minRole` field and filter them in the render:

```typescript
interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  minRole?: 'ic' | 'team_lead' | 'vp' | 'gm' | 'admin';
}
```

Add `minRole` to admin-only items:
```typescript
// In the Admin group items:
{ label: 'Team Management', href: '/settings/teams', icon: Users, minRole: 'admin' },
```

Filter items in `NavGroupSection` based on current user role using `usePermissions`.

**Step 3: Verify frontend compiles**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npx next build`
Expected: Build succeeds

**Step 4: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/lib/permissions.ts frontend/src/components/sidebar.tsx
git commit -m "feat: add usePermissions hook and role-based sidebar filtering"
```

---

## Task 9: Add VP/GM Roll-Up Cards to Dashboard

**Files:**
- Create: `frontend/src/components/team-rollup-cards.tsx`
- Create: `frontend/src/components/team-selector.tsx`
- Modify: `frontend/src/app/pipeline/page.tsx` — add roll-up cards for VP/GM

**Step 1: Create TeamSelector component**

A filter bar showing team names as chips. Visible only for VP/GM/Admin roles.

```typescript
// frontend/src/components/team-selector.tsx
'use client';

interface TeamSelectorProps {
  teams: { id: string; name: string }[];
  selected: string | null;  // null = "All Teams"
  onSelect: (teamId: string | null) => void;
}

export function TeamSelector({ teams, selected, onSelect }: TeamSelectorProps) {
  // Render "All Teams" chip + one chip per team
  // Active chip gets primary style, others get outline
}
```

**Step 2: Create TeamRollupCards component**

Summary cards showing per-team: total pipeline, avg health, # at-risk deals.

```typescript
// frontend/src/components/team-rollup-cards.tsx
'use client';

interface TeamRollupCardsProps {
  rollup: Array<{
    team_name: string;
    total_deals: number;
    avg_health_score: number | null;
    healthy_count: number;
    at_risk_count: number;
    critical_count: number;
    total_mrr: number;
  }>;
  onTeamClick?: (teamName: string) => void;
}

export function TeamRollupCards({ rollup, onTeamClick }: TeamRollupCardsProps) {
  // Grid of cards, one per team
  // Click to drill down
}
```

**Step 3: Wire into pipeline page**

In the pipeline page, check `usePermissions().canSeeRollup` and conditionally render the roll-up cards and team selector above the existing pipeline table.

**Step 4: Verify frontend compiles**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npx next build`
Expected: Build succeeds

**Step 5: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/team-rollup-cards.tsx frontend/src/components/team-selector.tsx frontend/src/app/pipeline/page.tsx
git commit -m "feat: add VP/GM roll-up cards and team selector to pipeline dashboard"
```

---

## Task 10: Add Team Management Admin Page

**Files:**
- Create: `frontend/src/app/settings/teams/page.tsx`
- Modify: `frontend/src/lib/api.ts` — add team/user API functions

**Step 1: Add API functions**

In `frontend/src/lib/api.ts`, add:

```typescript
export async function fetchTeams(): Promise<any[]> {
  return apiFetch('/api/teams/');
}

export async function createTeam(data: { name: string; level: string; parent_id?: string }): Promise<any> {
  return apiFetch('/api/teams/', { method: 'POST', body: JSON.stringify(data) });
}

export async function fetchUsers(): Promise<any[]> {
  return apiFetch('/api/users/');
}

export async function createUser(data: { name: string; email: string; role: string; team_id?: string }): Promise<any> {
  return apiFetch('/api/users/', { method: 'POST', body: JSON.stringify(data) });
}
```

**Step 2: Create admin page**

Create `frontend/src/app/settings/teams/page.tsx`:
- Protected by `usePermissions().isAdmin` — redirect non-admins
- Shows a table of teams with parent/level/leader
- Shows a table of users with role/team assignment
- "Add Team" and "Add User" modals
- Drag-to-reassign users between teams (stretch — can use simple dropdown for v1)

**Step 3: Verify frontend compiles**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npx next build`
Expected: Build succeeds

**Step 4: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/settings/teams/page.tsx frontend/src/lib/api.ts
git commit -m "feat: add team management admin page at /settings/teams"
```

---

## Task 11: Update Test Fixtures + conftest for New Models

**Files:**
- Modify: `tests/conftest.py` — add User and Team to imports, update `seeded_db` fixture

**Step 1: Update conftest imports**

Add `User, Team` to the imports from `sis.db.models`.

**Step 2: Update seeded_db to create matching User records**

In `seeded_db`, after creating accounts, also create User records for the existing AE owners and set `owner_id` on each account:

```python
# Create users matching the account owners
user_ae1 = User(id=_uuid(), name="AE One", email="ae_one@sis.com", role="ic")
user_ae2 = User(id=_uuid(), name="AE Two", email="ae_two@sis.com", role="ic")
user_ae3 = User(id=_uuid(), name="AE Three", email="ae_three@sis.com", role="ic")
session.add_all([user_ae1, user_ae2, user_ae3])
session.flush()

# Set owner_id on accounts
accounts[0].owner_id = user_ae1.id  # HealthyCorp
accounts[1].owner_id = user_ae2.id  # AtRiskCo
accounts[2].owner_id = user_ae3.id  # CriticalInc
session.flush()
```

Add `"sis.services.scoping_service.get_session"` to the `_patch_targets` list.

**Step 3: Run full test suite**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 4: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add tests/conftest.py
git commit -m "chore: update test fixtures to include User/Team models and owner_id"
```

---

## Task 12: DB Migration Script for Existing Data

**Files:**
- Create: `scripts/migrate_hierarchy.py`

**Step 1: Write migration script**

The script seeds the **real org tree** plus backfills `owner_id` from existing account data.

**Real Org Tree to Seed:**

```
Aviram Ganor (GM)
├── Gili Gertzberg (VP Sales)
│   ├── Bar Barda (Director, Sales) — Team Lead
│   │   ├── Dror Peter Gross (AE / IC)
│   │   ├── Uriel Ross (AE / IC)
│   │   └── Yos Jacobs (AE / IC)
│   └── Ying Wang (Director of Sales) — Team Lead
│       ├── Lei Bao (Strategic AE / IC)
│       ├── ZhenYu Qiao (Strategic AE / IC)
│       └── Wenze Li (AE / IC)
└── Roy Levi Erez (Admin + VP Sales)
    ├── Lachlan Taylor (Sr. Director, ANZ & Japan Sales) — Team Lead
    │   ├── David Nathan Chester (BDM / IC)
    │   ├── Lonnie Lee (BDM / IC)
    │   ├── Takuya Hasegawa (Sr. BDM / IC)
    │   ├── Keiko Navon (AE / IC)
    │   └── Nicholas Kirtley (Country Manager / IC)
    └── Lisa Lachkar (Director, Sales) — Team Lead
        ├── Nadine Barchechath (AE / IC)
        ├── Stefania Fanari (AE / IC)
        └── Omer Snir (AE / IC)
```

```python
"""Seed the real org hierarchy + backfill accounts.owner_id.

Run: python -m scripts.migrate_hierarchy

Idempotent — safe to run multiple times (get_or_create pattern).
"""

from __future__ import annotations
import logging
from sis.db.session import get_session
from sis.db.models import Base, User, Team, Account
from sis.db.engine import get_engine

logger = logging.getLogger(__name__)


def _get_or_create_user(session, *, name, email, role, team_id=None):
    user = session.query(User).filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, role=role, team_id=team_id)
        session.add(user)
        session.flush()
        logger.info("Created user: %s (%s)", name, role)
    return user


def _get_or_create_team(session, *, name, level, parent_id=None):
    team = session.query(Team).filter_by(name=name).first()
    if not team:
        team = Team(name=name, level=level, parent_id=parent_id)
        session.add(team)
        session.flush()
        logger.info("Created team: %s (%s)", name, level)
    return team


def seed_org_tree():
    """Create the full org hierarchy."""
    # Ensure tables exist
    Base.metadata.create_all(get_engine())

    with get_session() as s:
        # ── Root org ──
        root = _get_or_create_team(s, name="Sales Org", level="org")

        # ── GM ──
        aviram = _get_or_create_user(s, name="Aviram Ganor", email="aviram.ganor@riskified.com", role="gm")
        root.leader_id = aviram.id

        # ── VP: Gili ──
        div_gili = _get_or_create_team(s, name="Gili Gertzberg Division", level="division", parent_id=root.id)
        gili = _get_or_create_user(s, name="Gili Gertzberg", email="gili.gertzberg@riskified.com", role="vp", team_id=div_gili.id)
        div_gili.leader_id = gili.id

        #   TL: Bar Barda
        team_bar = _get_or_create_team(s, name="Bar Barda Team", level="team", parent_id=div_gili.id)
        bar = _get_or_create_user(s, name="Bar Barda", email="bar.barda@riskified.com", role="team_lead", team_id=team_bar.id)
        team_bar.leader_id = bar.id
        _get_or_create_user(s, name="Dror Peter Gross", email="dror.gross@riskified.com", role="ic", team_id=team_bar.id)
        _get_or_create_user(s, name="Uriel Ross", email="uriel.ross@riskified.com", role="ic", team_id=team_bar.id)
        _get_or_create_user(s, name="Yos Jacobs", email="yos.jacobs@riskified.com", role="ic", team_id=team_bar.id)

        #   TL: Ying Wang
        team_ying = _get_or_create_team(s, name="Ying Wang Team", level="team", parent_id=div_gili.id)
        ying = _get_or_create_user(s, name="Ying Wang", email="ying.wang@riskified.com", role="team_lead", team_id=team_ying.id)
        team_ying.leader_id = ying.id
        _get_or_create_user(s, name="Lei Bao", email="lei.bao@riskified.com", role="ic", team_id=team_ying.id)
        _get_or_create_user(s, name="ZhenYu Qiao", email="zhenyu.qiao@riskified.com", role="ic", team_id=team_ying.id)
        _get_or_create_user(s, name="Wenze Li", email="wenze.li@riskified.com", role="ic", team_id=team_ying.id)

        # ── VP: Roy (also Admin) ──
        div_roy = _get_or_create_team(s, name="Roy Levi Erez Division", level="division", parent_id=root.id)
        roy = _get_or_create_user(s, name="Roy Levi Erez", email="roy.levierez@riskified.com", role="admin", team_id=div_roy.id)
        div_roy.leader_id = roy.id

        #   TL: Lachlan Taylor
        team_lachlan = _get_or_create_team(s, name="Lachlan Taylor Team", level="team", parent_id=div_roy.id)
        lachlan = _get_or_create_user(s, name="Lachlan Taylor", email="lachlan.taylor@riskified.com", role="team_lead", team_id=team_lachlan.id)
        team_lachlan.leader_id = lachlan.id
        _get_or_create_user(s, name="David Nathan Chester", email="david.chester@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Lonnie Lee", email="lonnie.lee@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Takuya Hasegawa", email="takuya.hasegawa@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Keiko Navon", email="keiko.navon@riskified.com", role="ic", team_id=team_lachlan.id)
        _get_or_create_user(s, name="Nicholas Kirtley", email="nicholas.kirtley@riskified.com", role="ic", team_id=team_lachlan.id)

        #   TL: Lisa Lachkar
        team_lisa = _get_or_create_team(s, name="Lisa Lachkar Team", level="team", parent_id=div_roy.id)
        lisa = _get_or_create_user(s, name="Lisa Lachkar", email="lisa.lachkar@riskified.com", role="team_lead", team_id=team_lisa.id)
        team_lisa.leader_id = lisa.id
        _get_or_create_user(s, name="Nadine Barchechath", email="nadine.barchechath@riskified.com", role="ic", team_id=team_lisa.id)
        _get_or_create_user(s, name="Stefania Fanari", email="stefania.fanari@riskified.com", role="ic", team_id=team_lisa.id)
        _get_or_create_user(s, name="Omer Snir", email="omer.snir@riskified.com", role="ic", team_id=team_lisa.id)

        s.flush()
        logger.info("Org tree seeded: %d users, %d teams",
                     s.query(User).count(), s.query(Team).count())


def backfill_owner_ids():
    """Match existing accounts.ae_owner to User records and set owner_id."""
    with get_session() as s:
        accounts = s.query(Account).filter(Account.owner_id.is_(None)).all()
        matched = 0
        for acct in accounts:
            if not acct.ae_owner:
                continue
            user = s.query(User).filter(User.name == acct.ae_owner).first()
            if user:
                acct.owner_id = user.id
                matched += 1
        s.flush()
        logger.info("Backfilled owner_id on %d / %d accounts", matched, len(accounts))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_org_tree()
    backfill_owner_ids()
    print("Migration complete.")
```

**Step 2: Test with a copy of the production DB**

Run: `cp /Users/roylevierez/Documents/Sales/SIS/data/sis.db /Users/roylevierez/Documents/Sales/SIS/data/sis_backup.db`
Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m scripts.migrate_hierarchy`
Expected: Script runs without errors, creates 21 users and 7 teams, backfills owner_id

**Step 3: Verify migration**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.db.session import get_session; from sis.db.models import User, Team; s = get_session().__enter__(); print(f'Users: {s.query(User).count()}, Teams: {s.query(Team).count()}')"`
Expected: Users: 21, Teams: 7

**Step 4: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add scripts/migrate_hierarchy.py
git commit -m "chore: add one-time migration script for hierarchy data backfill"
```

---

## Task 13: Full Integration Verification

**Step 1: Run full backend test suite**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short`
Expected: All tests pass, no regressions

**Step 2: Run frontend build**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npx next build`
Expected: No type errors, clean build

**Step 3: Manual smoke test**

1. Start backend: `cd /Users/roylevierez/Documents/Sales/SIS && python -m uvicorn sis.api.main:app --reload`
2. Start frontend: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run dev`
3. Login as Admin — verify all pages visible
4. Login as VP — verify roll-up cards visible, only division deals shown
5. Login as IC — verify only own deals shown
6. Visit `/settings/teams` as admin — verify team management page loads

**Step 4: Final commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add -A
git commit -m "feat: complete team hierarchy with VP, GM, Admin roles and data scoping"
```

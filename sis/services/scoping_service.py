"""Role-based data scoping -- determines which user IDs a given user can see."""

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
            # VP not leading a division -- fall back to team membership
            if current_user.team_id:
                return _get_team_subtree_user_ids(current_user.team_id, session) | {current_user.id}
            return {current_user.id}

        # Get all teams under this division (recursive)
        return _get_team_subtree_user_ids(division.id, session) | {current_user.id}

    # Unknown role -- minimal access
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

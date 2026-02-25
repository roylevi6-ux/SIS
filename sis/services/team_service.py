"""Team & User CRUD service."""
from __future__ import annotations
from typing import Optional
from sis.db.session import get_session
from sis.db.models import User, Team


def create_team(
    name: str,
    level: str,
    parent_id: Optional[str] = None,
    leader_id: Optional[str] = None,
) -> dict:
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


def create_user(
    name: str,
    email: str,
    role: str,
    team_id: Optional[str] = None,
) -> dict:
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


def list_ics_with_hierarchy() -> list[dict]:
    """List all active IC users with their team name and team lead resolved from the hierarchy."""
    with get_session() as session:
        ics = (
            session.query(User)
            .filter(User.role == "ic", User.is_active == 1)
            .order_by(User.name)
            .all()
        )
        result = []
        for ic in ics:
            team_name = None
            team_lead = None
            if ic.team_id:
                team = session.query(Team).filter_by(id=ic.team_id).first()
                if team:
                    team_name = team.name
                    if team.leader_id:
                        leader = session.query(User).filter_by(id=team.leader_id).first()
                        if leader:
                            team_lead = leader.name
            result.append({
                "id": ic.id,
                "name": ic.name,
                "email": ic.email,
                "team_id": ic.team_id,
                "team_name": team_name,
                "team_lead": team_lead,
            })
        return result


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

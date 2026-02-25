"""Quota business logic — recursive rollup and upsert."""
from __future__ import annotations

from sqlalchemy.orm import Session

from sis.db.models import Quota, Team, User

_MAX_DEPTH = 10


def rollup_quota(db: Session, user_id: str, period: str, _depth: int = 0) -> float:
    """Compute quota for a user: own quota if IC, sum of subordinates otherwise."""
    if _depth > _MAX_DEPTH:
        return 0.0

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 0.0

    own = db.query(Quota).filter(
        Quota.user_id == user_id, Quota.period == period
    ).first()

    if user.role == "ic":
        return own.amount if own else 0.0

    led_teams = db.query(Team).filter(Team.leader_id == user_id).all()
    total = 0.0
    for team in led_teams:
        members = db.query(User).filter(User.team_id == team.id).all()
        for member in members:
            total += rollup_quota(db, member.id, period, _depth + 1)
    return total


def upsert_quota(db: Session, user_id: str, period: str, amount: float) -> None:
    """Create or update a quota row."""
    existing = db.query(Quota).filter(
        Quota.user_id == user_id, Quota.period == period
    ).first()
    if existing:
        existing.amount = amount
    else:
        db.add(Quota(user_id=user_id, period=period, amount=amount))
    db.commit()

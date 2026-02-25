"""Quota endpoints — read quotas, admin create/update."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sis.api.deps import get_current_user, get_db
from sis.db.models import Quota, Team, User

router = APIRouter(prefix="/api/quotas", tags=["quotas"])


class QuotaResponse(BaseModel):
    user_id: str
    user_name: str
    period: str
    amount: float


class QuotaCreate(BaseModel):
    user_id: str
    period: str
    amount: float


def _rollup_quota(db: Session, user_id: str, period: str) -> float:
    """Compute quota for a user: own quota if IC, sum of subordinates otherwise."""
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
            total += _rollup_quota(db, member.id, period)
    return total


@router.get("/{user_id}")
def get_quota(
    user_id: str,
    period: str = "2026",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> QuotaResponse:
    amount = _rollup_quota(db, user_id, period)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return QuotaResponse(user_id=user_id, user_name=user.name, period=period, amount=amount)


@router.get("/team/{team_id}")
def get_team_quota(
    team_id: str,
    period: str = "2026",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = db.query(User).filter(User.team_id == team_id).all()
    total = sum(_rollup_quota(db, m.id, period) for m in members)
    return {"team_id": team_id, "team_name": team.name, "period": period, "amount": total}


@router.post("/")
def upsert_quota(
    data: QuotaCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    existing = db.query(Quota).filter(
        Quota.user_id == data.user_id, Quota.period == data.period
    ).first()
    if existing:
        existing.amount = data.amount
    else:
        db.add(Quota(user_id=data.user_id, period=data.period, amount=data.amount))
    db.commit()
    return {"ok": True}

"""Quota endpoints — read quotas, admin create/update."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sis.api.deps import get_current_user, get_db
from sis.db.models import Team, User
from sis.services.quota_service import rollup_quota, upsert_quota

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


@router.get("/{user_id}")
def get_quota(
    user_id: str,
    period: str = "2026",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> QuotaResponse:
    amount = rollup_quota(db, user_id, period)
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
    total = sum(rollup_quota(db, m.id, period) for m in members)
    return {"team_id": team_id, "team_name": team.name, "period": period, "amount": total}


@router.post("/")
def upsert_quota_endpoint(
    data: QuotaCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    upsert_quota(db, data.user_id, data.period, data.amount)
    return {"ok": True}

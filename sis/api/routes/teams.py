"""Team & User management API routes -- admin only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_current_user
from sis.services import team_service
from sis.api.schemas.teams import TeamCreate, TeamUpdate, UserCreate, UserUpdate

router = APIRouter(tags=["teams"])


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# -- IC listing (non-admin) ---------------------------------------------------

@router.get("/api/users/ics")
def list_ics(user: dict = Depends(get_current_user)):
    """List all active IC users with team hierarchy info. Any authenticated user can call."""
    return team_service.list_ics_with_hierarchy()


# -- Team endpoints -----------------------------------------------------------

@router.get("/api/teams/")
def list_teams(user: dict = Depends(get_current_user)):
    return team_service.list_teams()


@router.post("/api/teams/")
def create_team(body: TeamCreate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    return team_service.create_team(
        name=body.name, level=body.level,
        parent_id=body.parent_id, leader_id=body.leader_id,
    )


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


# -- User endpoints -----------------------------------------------------------

@router.get("/api/users/")
def list_users(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return team_service.list_users()


@router.post("/api/users/")
def create_user(body: UserCreate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    return team_service.create_user(
        name=body.name, email=body.email,
        role=body.role, team_id=body.team_id,
    )


@router.put("/api/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    fields = body.model_dump(exclude_none=True)
    try:
        return team_service.update_user(user_id, **fields)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

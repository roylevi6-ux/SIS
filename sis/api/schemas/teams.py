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

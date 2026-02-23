"""Account API routes — CRUD + IC forecast."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_current_user
from sis.services import account_service
from sis.api.schemas.accounts import (
    AccountCreate,
    AccountUpdate,
    ICForecastUpdate,
)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/")
def list_accounts(
    sort_by: str = "account_name",
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List all accounts with latest assessment summary."""
    return account_service.list_accounts(team=team, sort_by=sort_by)


@router.get("/{account_id}")
def get_account(account_id: str, user: dict = Depends(get_current_user)):
    """Get full account detail with assessment and transcripts."""
    try:
        return account_service.get_account_detail(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/")
def create_account(body: AccountCreate, user: dict = Depends(get_current_user)):
    """Create a new account."""
    account = account_service.create_account(
        name=body.name,
        mrr=body.mrr_estimate,
        team_lead=body.team_lead,
        ae_owner=body.ae_owner,
        team=body.team_name,
    )
    return {"id": account.id, "account_name": account.account_name}


@router.put("/{account_id}")
def update_account(account_id: str, body: AccountUpdate, user: dict = Depends(get_current_user)):
    """Update an existing account's fields."""
    fields = body.model_dump(exclude_none=True)
    # Map schema field 'name' to service field 'account_name'
    if "name" in fields:
        fields["account_name"] = fields.pop("name")
    try:
        account = account_service.update_account(account_id, **fields)
        return {"id": account.id, "account_name": account.account_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{account_id}")
def delete_account(account_id: str, user: dict = Depends(get_current_user)):
    """Delete an account and all associated data (cascade)."""
    try:
        return account_service.delete_account(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{account_id}/ic-forecast")
def set_ic_forecast(account_id: str, body: ICForecastUpdate, user: dict = Depends(get_current_user)):
    """Set the IC forecast category and compute divergence."""
    try:
        return account_service.set_ic_forecast(account_id, body.category)
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 422,
            detail=str(e),
        )

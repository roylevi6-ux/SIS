"""Watchlist API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from sis.api.deps import get_current_user
from sis.services import watchlist_service

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    account_ids: list[str]
    sf_account_names: Optional[dict[str, str]] = None


class SFNameUpdateRequest(BaseModel):
    sf_account_name: str


@router.get("")
def list_watchlist(user: dict = Depends(get_current_user)):
    return watchlist_service.list_watched_accounts()


@router.post("")
def add_to_watchlist(body: WatchlistAddRequest, user: dict = Depends(get_current_user)):
    return watchlist_service.add_to_watchlist(
        body.account_ids, body.sf_account_names, added_by=user.get("user_id")
    )


@router.delete("/{account_id}")
def remove_from_watchlist(account_id: str, user: dict = Depends(get_current_user)):
    removed = watchlist_service.remove_from_watchlist(account_id)
    if not removed:
        raise HTTPException(404, "Account not on watchlist")
    return {"ok": True}


@router.put("/{account_id}/sf-name")
def update_sf_name(account_id: str, body: SFNameUpdateRequest, user: dict = Depends(get_current_user)):
    return watchlist_service.update_sf_name(account_id, body.sf_account_name)


@router.post("/add-all")
def add_all_accounts(user: dict = Depends(get_current_user)):
    return watchlist_service.add_all_accounts_to_watchlist(added_by=user.get("user_id"))


@router.post("/import-csv")
async def import_csv(file: UploadFile, user: dict = Depends(get_current_user)):
    content = await file.read()
    return watchlist_service.import_watchlist_csv(content)


@router.post("/tam-list")
async def upload_tam_list(file: UploadFile, user: dict = Depends(get_current_user)):
    content = await file.read()
    return watchlist_service.upload_tam_list(content)


@router.get("/suggest-sf-names")
def suggest_sf_names(user: dict = Depends(get_current_user)):
    """Return closest TAM suggestions for all watchlist accounts without exact TAM matches."""
    return watchlist_service.get_sf_name_suggestions()

"""Google Drive API routes — scan local Drive folders, list accounts, import calls."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sis.api.deps import get_current_user
from sis.services import gdrive_service
from sis.services.account_service import create_account, list_accounts
from sis.config import GOOGLE_DRIVE_TRANSCRIPTS_PATH

router = APIRouter(prefix="/api/gdrive", tags=["gdrive"])


# ── Schemas ──────────────────────────────────────────────────────────


class DrivePathRequest(BaseModel):
    path: str


class ImportRequest(BaseModel):
    account_name: str
    account_path: str
    max_calls: int = 5
    deal_type: Optional[str] = None
    mrr_estimate: Optional[float] = None
    ae_owner: Optional[str] = None
    team_lead: Optional[str] = None
    team_name: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────


@router.get("/config")
def get_drive_config(user: dict = Depends(get_current_user)):
    """Return the configured Google Drive path."""
    return {"path": GOOGLE_DRIVE_TRANSCRIPTS_PATH or ""}


@router.post("/validate")
def validate_path(body: DrivePathRequest, user: dict = Depends(get_current_user)):
    """Validate a Google Drive folder path."""
    is_valid, message = gdrive_service.validate_drive_path(body.path)
    return {"is_valid": is_valid, "message": message}


@router.post("/accounts")
def list_drive_accounts(body: DrivePathRequest, user: dict = Depends(get_current_user)):
    """List account sub-folders in the Drive folder."""
    is_valid, message = gdrive_service.validate_drive_path(body.path)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    try:
        accounts = gdrive_service.list_account_folders(body.path)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return accounts


@router.post("/calls")
def list_recent_calls(body: ImportRequest, user: dict = Depends(get_current_user)):
    """List the most recent calls for an account."""
    calls = gdrive_service.get_recent_calls_info(
        body.account_path, body.max_calls, account_name=body.account_name
    )
    return calls


@router.post("/import")
def import_from_drive(body: ImportRequest, user: dict = Depends(get_current_user)):
    """Import calls from Google Drive into the database."""
    # Parse calls from local files
    try:
        parsed_calls = gdrive_service.download_and_parse_calls(
            body.account_path, body.max_calls, account_name=body.account_name
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse calls: {e}")

    if not parsed_calls:
        raise HTTPException(status_code=404, detail="No valid calls found to import")

    # Find or create account
    existing = list_accounts()
    account_id = None
    for acct in existing:
        if acct["account_name"].lower() == body.account_name.lower():
            account_id = acct["id"]
            break

    if not account_id:
        from sis.constants import normalize_deal_type
        acct_obj = create_account(
            name=body.account_name,
            deal_type=normalize_deal_type(body.deal_type),
            mrr=body.mrr_estimate,
            ae_owner=body.ae_owner,
            team_lead=body.team_lead,
            team=body.team_name,
        )
        account_id = acct_obj.id

    # Upload to DB (with dedup)
    upload_result = gdrive_service.upload_calls_to_db(parsed_calls, account_id)
    imported = upload_result["imported"]
    skipped = upload_result["skipped"]

    # Build the call detail list — match imported transcripts back to parsed calls
    imported_idx = 0
    calls_detail = []
    for call in parsed_calls:
        gong_id = call.metadata.call_id
        if gong_id and gong_id in skipped:
            calls_detail.append({
                "date": call.metadata.date,
                "title": call.metadata.title[:60],
                "token_count": None,
                "status": "skipped",
            })
        elif imported_idx < len(imported):
            calls_detail.append({
                "date": call.metadata.date,
                "title": call.metadata.title[:60],
                "token_count": imported[imported_idx].token_count,
                "status": "imported",
            })
            imported_idx += 1

    return {
        "account_id": account_id,
        "account_name": body.account_name,
        "imported_count": len(imported),
        "skipped_count": len(skipped),
        "calls": calls_detail,
    }

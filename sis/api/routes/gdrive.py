"""Google Drive API routes — scan local Drive folders, list accounts, import calls."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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


# ── Routes ───────────────────────────────────────────────────────────


@router.get("/config")
def get_drive_config():
    """Return the configured Google Drive path."""
    return {"path": GOOGLE_DRIVE_TRANSCRIPTS_PATH or ""}


@router.post("/validate")
def validate_path(body: DrivePathRequest):
    """Validate a Google Drive folder path."""
    is_valid, message = gdrive_service.validate_drive_path(body.path)
    return {"is_valid": is_valid, "message": message}


@router.post("/accounts")
def list_drive_accounts(body: DrivePathRequest):
    """List account sub-folders in the Drive folder."""
    is_valid, message = gdrive_service.validate_drive_path(body.path)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    accounts = gdrive_service.list_account_folders(body.path)
    return accounts


@router.post("/calls")
def list_recent_calls(body: ImportRequest):
    """List the most recent calls for an account folder."""
    calls = gdrive_service.get_recent_calls_info(body.account_path, body.max_calls)
    return calls


@router.post("/import")
def import_from_drive(body: ImportRequest):
    """Import calls from Google Drive into the database."""
    # Parse calls from local files
    try:
        parsed_calls = gdrive_service.download_and_parse_calls(
            body.account_path, body.max_calls
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
        acct_obj = create_account(name=body.account_name)
        account_id = acct_obj.id

    # Upload to DB
    results = gdrive_service.upload_calls_to_db(parsed_calls, account_id)

    return {
        "account_id": account_id,
        "account_name": body.account_name,
        "imported_count": len(results),
        "calls": [
            {
                "date": call.metadata.date,
                "title": call.metadata.title[:60],
                "token_count": r.token_count,
            }
            for call, r in zip(parsed_calls, results)
        ],
    }

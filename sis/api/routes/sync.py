"""Sync API routes — start/cancel/monitor bulk Gong sync jobs."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sis.api.deps import get_current_user
from sis.db.models import SyncJob, SyncAccountResult
from sis.db.session import get_session
from sis.services import watchlist_service
from sis.services import sync_progress_store as progress_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])

# ── Stale job threshold (30 minutes) ──────────────────────────────────
STALE_JOB_MINUTES = 30

# Strong references to background tasks (prevents GC from killing them)
_background_tasks: set = set()


# ── Request / Response schemas ─────────────────────────────────────────

class SyncStartRequest(BaseModel):
    account_ids: Optional[list[str]] = None  # subset of watchlist, or None=all
    start_date: Optional[str] = None
    skip_n8n: bool = False


# ── Routes ─────────────────────────────────────────────────────────────

@router.post("/start")
async def start_sync(
    body: SyncStartRequest,
    user: dict = Depends(get_current_user),
):
    """Start a bulk sync job. Returns immediately with job_id for SSE tracking.

    Guards:
    - Cleans up stale jobs (running > 30 min)
    - Checks no sync is already running (409 Conflict if so)
    - Validates watchlist is not empty
    """
    # Get watched accounts (before the DB transaction)
    watched = watchlist_service.list_watched_accounts()
    if not watched:
        raise HTTPException(422, detail="No accounts on watchlist. Add accounts first.")

    # Filter to subset if requested
    if body.account_ids:
        id_set = set(body.account_ids)
        watched = [w for w in watched if w["account_id"] in id_set]
        if not watched:
            raise HTTPException(422, detail="None of the requested accounts are on the watchlist.")

    # Single transaction: cleanup stale + check running + create job
    with get_session() as session:
        # Clean up stale jobs (running > 30 min)
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=STALE_JOB_MINUTES)).isoformat()
        stale = session.query(SyncJob).filter(
            SyncJob.status.in_(["pending", "running", "scanning", "importing"]),
            SyncJob.started_at < cutoff,
        ).all()
        for job in stale:
            logger.warning("Marking stale sync job %s as failed", job.id)
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc).isoformat()

        # Check for running sync (in same transaction)
        running = session.query(SyncJob).filter(
            SyncJob.status.in_(["pending", "running", "scanning", "importing"])
        ).first()
        if running:
            raise HTTPException(409, detail={
                "message": "Sync already in progress",
                "job_id": running.id,
            })

        # Create job + account result rows atomically
        job = SyncJob(
            status="pending",
            triggered_by=user.get("user_id"),
            total_accounts=len(watched),
        )
        session.add(job)
        session.flush()
        job_id = job.id

        for acct in watched:
            result_row = SyncAccountResult(
                sync_job_id=job_id,
                account_id=acct["account_id"],
                account_name=acct["account_name"],
            )
            session.add(result_row)

    # Build account list for orchestrator
    account_list = [
        {
            "account_id": w["account_id"],
            "account_name": w["account_name"],
            "sf_account_name": w["sf_account_name"],
        }
        for w in watched
    ]

    # Launch orchestrator as background task (hold strong reference to prevent GC)
    from sis.services.sync_orchestrator import run_sync
    task = asyncio.create_task(run_sync(
        job_id=job_id,
        watched_accounts=account_list,
        start_date=body.start_date,
        skip_n8n=body.skip_n8n,
    ))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "job_id": job_id,
        "status": "started",
        "total_accounts": len(watched),
        "skip_n8n": body.skip_n8n,
    }


@router.get("/status/{job_id}")
def get_sync_status(job_id: str, user: dict = Depends(get_current_user)):
    """Polling fallback for sync status."""
    # Try in-memory first
    snapshot = progress_store.get_sync_snapshot(job_id)
    if snapshot:
        return snapshot

    # Fall back to DB
    with get_session() as session:
        job = session.query(SyncJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(404, detail="Sync job not found")

        results = session.query(SyncAccountResult).filter_by(sync_job_id=job_id).all()
        return {
            "job_id": job.id,
            "status": job.status,
            "phase": "completed" if job.status == "completed" else job.status,
            "total_accounts": job.total_accounts,
            "calls_imported": job.calls_imported or 0,
            "calls_skipped": job.calls_skipped or 0,
            "n8n_calls_succeeded": job.n8n_calls_succeeded or 0,
            "n8n_calls_failed": job.n8n_calls_failed or 0,
            "total_seconds": job.total_seconds,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "accounts": {
                r.account_id: {
                    "name": r.account_name,
                    "n8n_status": r.n8n_status,
                    "n8n_calls_found": r.n8n_calls_found,
                    "import_status": r.import_status,
                    "calls_imported": r.calls_imported or 0,
                    "calls_skipped": r.calls_skipped or 0,
                }
                for r in results
            },
        }


@router.post("/{job_id}/cancel")
def cancel_sync(job_id: str, user: dict = Depends(get_current_user)):
    """Cancel an in-progress sync."""
    progress_store.cancel_sync(job_id)

    with get_session() as session:
        job = session.query(SyncJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(404, detail="Sync job not found")
        if job.status in ("completed", "failed", "cancelled"):
            return {"ok": False, "message": f"Job already {job.status}"}
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc).isoformat()

    return {"ok": True, "message": "Cancellation requested"}


@router.get("/history")
def sync_history(user: dict = Depends(get_current_user)):
    """List recent sync jobs, most recent first."""
    with get_session() as session:
        jobs = (
            session.query(SyncJob)
            .order_by(SyncJob.started_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "job_id": j.id,
                "status": j.status,
                "total_accounts": j.total_accounts,
                "calls_imported": j.calls_imported or 0,
                "calls_skipped": j.calls_skipped or 0,
                "n8n_calls_succeeded": j.n8n_calls_succeeded or 0,
                "n8n_calls_failed": j.n8n_calls_failed or 0,
                "total_seconds": j.total_seconds,
                "started_at": j.started_at,
                "completed_at": j.completed_at,
            }
            for j in jobs
        ]


@router.get("/suggest-sf-name/{account_id}")
def suggest_sf_name(account_id: str, user: dict = Depends(get_current_user)):
    """Guess the Salesforce name from TAM list."""
    with get_session() as session:
        from sis.db.models import Account
        account = session.query(Account).filter_by(id=account_id).first()
        if not account:
            raise HTTPException(404, detail="Account not found")

        suggestion = watchlist_service.suggest_sf_name_from_tam(account.account_name)
        return {
            "account_name": account.account_name,
            "suggested_sf_name": suggestion,
            "confidence": "fuzzy_match" if suggestion else "none",
        }



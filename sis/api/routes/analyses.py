"""Analysis API routes — run pipeline, history, agent details, rerun."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_current_user
from sis.services import analysis_service
from sis.api.schemas.analyses import (
    AgentAnalysisResponse,
    AnalysisHistoryItem,
    AnalysisRequest,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
)
from sis.orchestrator.batch_store import (
    create_batch,
    update_item,
    cancel_batch,
    get_snapshot as get_batch_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyses", tags=["analyses"])
executor = ThreadPoolExecutor(max_workers=4)

BATCH_CONCURRENCY = int(os.environ.get("BATCH_CONCURRENCY", "3"))
batch_executor = ThreadPoolExecutor(max_workers=BATCH_CONCURRENCY)


def _run_pipeline_sync(account_id: str, run_id: str):
    """Run pipeline in thread pool with progress tracking."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        analysis_service.analyze_account(account_id, run_id=run_id)
    except Exception:
        logger.exception("Pipeline failed for account %s", account_id)
        # Ensure progress store shows failure even on unhandled exception
        try:
            from sis.orchestrator.progress_store import mark_run_completed
            mark_run_completed(run_id, "failed")
        except Exception:
            pass


def _run_batch_item(batch_id: str, index: int, item_data: dict):
    """Process one account in a batch: import from Drive -> run analysis."""
    from sis.services import gdrive_service
    from sis.services.account_service import create_account, list_accounts
    from sis.services.transcript_service import get_active_transcript_texts
    from sis.constants import normalize_deal_type
    from sis.orchestrator.progress_store import get_snapshot as get_run_snapshot

    start_time = time.time()
    account_id = None

    try:
        # Phase 1: Upload transcripts
        update_item(batch_id, index, status="uploading")

        parsed_calls = gdrive_service.download_and_parse_calls(
            item_data["drive_path"],
            item_data["max_calls"],
            account_name=item_data["account_name"],
        )

        if not parsed_calls:
            update_item(batch_id, index, status="failed", error="No valid calls found")
            return

        # Find or create account
        existing = list_accounts()
        for acct in existing:
            if acct["account_name"].lower() == item_data["account_name"].lower():
                account_id = acct["id"]
                break

        if account_id:
            # Update existing account's SF fields if provided
            from sis.services.account_service import update_account
            sf_updates = {}
            for f in ["sf_stage", "sf_forecast_category", "sf_close_quarter", "cp_estimate"]:
                if item_data.get(f) is not None:
                    sf_updates[f] = item_data[f]
            if sf_updates:
                update_account(account_id, **sf_updates)

        if not account_id:
            acct_obj = create_account(
                name=item_data["account_name"],
                deal_type=normalize_deal_type(item_data.get("deal_type")),
                cp_estimate=item_data.get("cp_estimate"),
                owner_id=item_data.get("owner_id"),
                sf_stage=item_data.get("sf_stage"),
                sf_forecast_category=item_data.get("sf_forecast_category"),
                sf_close_quarter=item_data.get("sf_close_quarter"),
            )
            account_id = acct_obj.id

        update_item(batch_id, index, account_id=account_id)

        # Upload to DB
        upload_result = gdrive_service.upload_calls_to_db(parsed_calls, account_id)
        imported_count = len(upload_result["imported"])
        skipped_count = len(upload_result["skipped"])
        update_item(batch_id, index, imported_count=imported_count, skipped_count=skipped_count)

        # Phase 2: Run analysis
        texts = get_active_transcript_texts(account_id)
        if not texts:
            update_item(batch_id, index, status="failed", error="No active transcripts after upload")
            return

        update_item(batch_id, index, status="analyzing")
        run_id = analysis_service.create_analysis_run(account_id)
        update_item(batch_id, index, run_id=run_id)

        # Run pipeline synchronously (we're already in a thread)
        analysis_service.analyze_account(account_id, run_id=run_id)

        # Read final cost/time from progress store
        run_snapshot = get_run_snapshot(run_id)
        elapsed = time.time() - start_time
        cost = run_snapshot["total_cost_usd"] if run_snapshot else 0

        update_item(
            batch_id, index,
            status="completed",
            elapsed_seconds=elapsed,
            cost_usd=cost,
        )

    except Exception as e:
        logger.exception("Batch item failed: %s", item_data["account_name"])
        elapsed = time.time() - start_time
        update_item(
            batch_id, index,
            status="failed",
            account_id=account_id,
            error=str(e)[:200],
            elapsed_seconds=elapsed,
        )


def _run_batch(batch_id: str, items: list[dict]):
    """Orchestrate batch items through the concurrency-limited executor."""
    import concurrent.futures

    futures = []
    for i, item_data in enumerate(items):
        future = batch_executor.submit(_run_batch_item, batch_id, i, item_data)
        futures.append(future)

    concurrent.futures.wait(futures)


@router.post("/")
async def run_analysis(body: AnalysisRequest, user: dict = Depends(get_current_user)):
    """Start analysis pipeline — returns immediately, polls via SSE.

    Creates an AnalysisRun row and initializes the progress store before
    spawning the pipeline thread. The returned run_id is real and can be
    used immediately for SSE subscription.
    """
    try:
        from sis.services import transcript_service

        texts = transcript_service.get_active_transcript_texts(body.account_id)
        if not texts:
            raise HTTPException(422, "No active transcripts for this account")
    except ValueError as e:
        raise HTTPException(404, str(e))

    # Create the DB row immediately so SSE can reference it
    run_id = analysis_service.create_analysis_run(body.account_id)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _run_pipeline_sync, body.account_id, run_id)
    return {"status": "started", "account_id": body.account_id, "run_id": run_id}


@router.post("/batch", response_model=BatchAnalysisResponse)
async def run_batch_analysis(body: BatchAnalysisRequest, user: dict = Depends(get_current_user)):
    """Start batch import + analysis for multiple accounts.

    Returns immediately with a batch_id. Poll via SSE at /api/sse/batch/{batch_id}.
    """
    if len(body.items) > 10:
        raise HTTPException(422, "Maximum 10 accounts per batch")
    if len(body.items) == 0:
        raise HTTPException(422, "At least one account required")

    item_dicts = [item.model_dump() for item in body.items]
    batch = create_batch(item_dicts)

    import threading
    t = threading.Thread(target=_run_batch, args=(batch["batch_id"], item_dicts), daemon=True)
    t.start()

    return batch


@router.post("/{run_id}/cancel")
async def cancel_analysis(run_id: str, user: dict = Depends(get_current_user)):
    """Cancel a running analysis pipeline."""
    from sis.orchestrator.progress_store import cancel_run, get_snapshot

    snapshot = get_snapshot(run_id)
    if not snapshot:
        raise HTTPException(404, f"Run {run_id} not found")
    if snapshot["status"] != "running":
        raise HTTPException(422, f"Run is already {snapshot['status']}")

    cancel_run(run_id)
    return {"status": "cancelling", "run_id": run_id}


@router.post("/batch/{batch_id}/cancel")
async def cancel_batch_analysis(batch_id: str, user: dict = Depends(get_current_user)):
    """Cancel all running items in a batch and their analysis pipelines."""
    from sis.orchestrator.progress_store import cancel_run

    snapshot = get_batch_snapshot(batch_id)
    if not snapshot:
        raise HTTPException(404, f"Batch {batch_id} not found")

    run_ids = cancel_batch(batch_id)
    for rid in run_ids:
        try:
            cancel_run(rid)
        except Exception:
            pass  # run may have already finished

    return {"status": "cancelled", "batch_id": batch_id, "cancelled_runs": len(run_ids)}


@router.get("/delta/{account_id}")
def get_delta(account_id: str, user: dict = Depends(get_current_user)):
    """Get assessment delta (latest vs previous) for an account."""
    delta = analysis_service.get_assessment_delta(account_id)
    if delta is None:
        return {"delta": None, "message": "Need at least 2 analysis runs to compute delta"}
    return delta


@router.get("/timeline/{account_id}")
def get_timeline(account_id: str, user: dict = Depends(get_current_user)):
    """Get full assessment history timeline for an account."""
    return analysis_service.get_assessment_timeline(account_id)


@router.get("/history/{account_id}", response_model=List[AnalysisHistoryItem])
def get_history(account_id: str, user: dict = Depends(get_current_user)):
    """Get analysis run history for an account."""
    return analysis_service.get_analysis_history(account_id)


@router.get("/{run_id}/agents", response_model=List[AgentAnalysisResponse])
def get_agents(run_id: str, user: dict = Depends(get_current_user)):
    """Get all agent analyses for a specific run."""
    return analysis_service.get_agent_analyses(run_id)


@router.post("/{run_id}/rerun/{agent_id}")
def rerun_agent(run_id: str, agent_id: str, user: dict = Depends(get_current_user)):
    """Re-run a single agent for an existing analysis run."""
    try:
        return analysis_service.rerun_agent(run_id, agent_id)
    except ValueError as e:
        raise HTTPException(
            404 if "not found" in str(e).lower() else 422, str(e)
        )


@router.get("/carry-forward/{account_id}")
def get_carry_forward_actions(account_id: str, user: dict = Depends(get_current_user)):
    """Get unfollowed actions from prior run that weren't addressed in latest."""
    return analysis_service.get_carry_forward_actions(account_id)


@router.post("/{run_id}/resynthesize")
def resynthesize(run_id: str, user: dict = Depends(get_current_user)):
    """Re-run synthesis (Agent 10) for an existing analysis run."""
    try:
        return analysis_service.resynthesize(run_id)
    except ValueError as e:
        raise HTTPException(
            404 if "not found" in str(e).lower() else 422, str(e)
        )

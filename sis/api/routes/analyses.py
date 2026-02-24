"""Analysis API routes — run pipeline, history, agent details, rerun."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_current_user
from sis.services import analysis_service
from sis.api.schemas.analyses import (
    AgentAnalysisResponse,
    AnalysisHistoryItem,
    AnalysisRequest,
)

router = APIRouter(prefix="/api/analyses", tags=["analyses"])
executor = ThreadPoolExecutor(max_workers=4)


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

"""Analysis API routes — run pipeline, history, agent details, rerun."""

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_optional_user
from sis.services import analysis_service
from sis.api.schemas.analyses import (
    AgentAnalysisResponse,
    AnalysisHistoryItem,
    AnalysisRequest,
)

router = APIRouter(prefix="/api/analyses", tags=["analyses"])
executor = ThreadPoolExecutor(max_workers=4)


def _run_pipeline_sync(account_id: str, run_id: str):
    """Run pipeline in thread pool."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        analysis_service.analyze_account(account_id)
    except Exception:
        logger.exception("Pipeline failed for account %s", account_id)


@router.post("/")
async def run_analysis(body: AnalysisRequest, user: Optional[dict] = Depends(get_optional_user)):
    """Start analysis pipeline — returns immediately, polls via SSE."""
    try:
        # Validate account has transcripts before spawning thread
        from sis.services import transcript_service

        texts = transcript_service.get_active_transcript_texts(body.account_id)
        if not texts:
            raise HTTPException(422, "No active transcripts for this account")
    except ValueError as e:
        raise HTTPException(404, str(e))

    run_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _run_pipeline_sync, body.account_id, run_id)
    return {"status": "started", "account_id": body.account_id, "run_id": run_id}


@router.get("/history/{account_id}", response_model=List[AnalysisHistoryItem])
def get_history(account_id: str):
    """Get analysis run history for an account."""
    return analysis_service.get_analysis_history(account_id)


@router.get("/{run_id}/agents", response_model=List[AgentAnalysisResponse])
def get_agents(run_id: str):
    """Get all agent analyses for a specific run."""
    return analysis_service.get_agent_analyses(run_id)


@router.post("/{run_id}/rerun/{agent_id}")
def rerun_agent(run_id: str, agent_id: str, user: Optional[dict] = Depends(get_optional_user)):
    """Re-run a single agent for an existing analysis run."""
    try:
        return analysis_service.rerun_agent(run_id, agent_id)
    except ValueError as e:
        raise HTTPException(
            404 if "not found" in str(e).lower() else 422, str(e)
        )


@router.post("/{run_id}/resynthesize")
def resynthesize(run_id: str, user: Optional[dict] = Depends(get_optional_user)):
    """Re-run synthesis (Agent 10) for an existing analysis run."""
    try:
        return analysis_service.resynthesize(run_id)
    except ValueError as e:
        raise HTTPException(
            404 if "not found" in str(e).lower() else 422, str(e)
        )

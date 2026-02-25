"""SSE (Server-Sent Events) route — pipeline progress streaming.

Enhanced to read from the in-memory progress store for real-time
per-agent detail. Falls back to DB for completed runs not in memory.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from sis.db.models import AnalysisRun
from sis.db.session import get_session
from sis.orchestrator.progress_store import get_snapshot
from sis.orchestrator.batch_store import get_snapshot as get_batch_snapshot

router = APIRouter(prefix="/api/sse", tags=["sse"])

# Maximum time (seconds) to keep an SSE stream open before closing
SSE_TIMEOUT_SECONDS = 600  # 10 minutes


@router.get("/analysis/{run_id}")
async def analysis_progress(run_id: str):
    """Server-Sent Events stream for pipeline analysis progress.

    Reads from the in-memory progress store (1s interval) for real-time
    per-agent detail. Falls back to DB for runs not in memory.
    The stream closes when the run reaches a terminal status or times out.
    """

    async def event_stream():
        elapsed = 0
        while elapsed < SSE_TIMEOUT_SECONDS:
            status = _get_progress(run_id)
            yield f"data: {json.dumps(status)}\n\n"
            if status["status"] in ("completed", "failed", "partial"):
                break
            await asyncio.sleep(1)
            elapsed += 1
        else:
            # Timed out — send a final timeout event
            yield f"data: {json.dumps({'run_id': run_id, 'status': 'timeout', 'agents': {}})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/batch/{batch_id}")
async def batch_progress(batch_id: str):
    """SSE stream for batch analysis progress.

    Streams the full batch snapshot (all items with statuses) at 1s intervals.
    Closes when all items reach a terminal status or after timeout.
    """

    async def event_stream():
        elapsed = 0
        while elapsed < SSE_TIMEOUT_SECONDS:
            snapshot = get_batch_snapshot(batch_id)
            if not snapshot:
                yield f"data: {json.dumps({'batch_id': batch_id, 'status': 'not_found', 'items': []})}\n\n"
                break
            yield f"data: {json.dumps(snapshot)}\n\n"
            if snapshot["status"] in ("completed", "failed", "partial"):
                break
            await asyncio.sleep(1)
            elapsed += 1
        else:
            yield f"data: {json.dumps({'batch_id': batch_id, 'status': 'timeout', 'items': []})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _get_progress(run_id: str) -> dict:
    """Read current run progress — prefer in-memory store, fall back to DB."""
    # Try progress store first (real-time per-agent detail)
    snapshot = get_snapshot(run_id)
    if snapshot:
        return snapshot

    # Fall back to DB for runs that have already completed and been cleaned up
    with get_session() as session:
        run = session.query(AnalysisRun).filter_by(id=run_id).first()
        if not run:
            return {"run_id": run_id, "status": "not_found", "agents": {}}
        return {
            "run_id": run.id,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "agents": {},
            "total_cost_usd": run.total_cost_usd or 0,
            "total_elapsed_seconds": 0,
            "errors": [],
        }

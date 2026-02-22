"""SSE (Server-Sent Events) route — pipeline progress streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from sis.db.models import AnalysisRun
from sis.db.session import get_session

router = APIRouter(prefix="/api/sse", tags=["sse"])


@router.get("/analysis/{run_id}")
async def analysis_progress(run_id: str):
    """Server-Sent Events stream for pipeline analysis progress.

    Polls the DB every 2 seconds and emits the run status as JSON.
    The stream closes when the run reaches a terminal status
    (completed, failed, or partial).
    """

    async def event_stream():
        while True:
            status = _get_run_status(run_id)
            yield f"data: {json.dumps(status)}\n\n"
            if status["status"] in ("completed", "failed", "partial"):
                break
            await asyncio.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _get_run_status(run_id: str) -> dict:
    """Read current run status from DB."""
    with get_session() as session:
        run = session.query(AnalysisRun).filter_by(id=run_id).first()
        if not run:
            return {"run_id": run_id, "status": "not_found"}
        return {
            "run_id": run.id,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }

# Analysis Progress — Detailed Per-Agent Reporting

## Problem
When a user triggers Import & Analyze, the UI shows only a spinner with elapsed time. There is no visibility into which of the 10 agents is running, which have completed, how much each costs, or how long each takes. Users have no idea what's happening.

## Solution
SSE-based real-time per-agent progress reporting, displayed inline on the upload page.

## Architecture

### Backend: In-Memory Progress Store
**New file: `sis/orchestrator/progress_store.py`**

Thread-safe dict keyed by `run_id`. Each entry:
```python
{
    "run_id": str,
    "status": "running" | "completed" | "failed" | "partial",
    "started_at": str,
    "agents": {
        "agent_1": {
            "status": "pending" | "running" | "completed" | "failed",
            "name": "Stage & Progress",
            "started_at": str | None,
            "elapsed_seconds": float | None,
            "input_tokens": int | None,
            "output_tokens": int | None,
            "cost_usd": float | None,
            "model": str | None,
            "attempts": int | None,
            "error": str | None,
        },
        # ... agents 2-10
    },
    "total_cost_usd": float,
    "total_elapsed_seconds": float,
    "errors": list[str],
}
```

Auto-cleanup: entries removed 5 minutes after reaching terminal status.

### Backend: Pipeline Changes
**Modified: `sis/orchestrator/pipeline.py`**

- Accept optional `run_id` to publish progress against.
- On each agent start: mark `running` in progress store.
- On each agent complete: mark `completed` with tokens/cost/time.
- Agents 1-8 (and 0E for expansion) all run in parallel via `asyncio.as_completed` so each agent's completion is reported individually.
- On pipeline end: mark overall status.

### Backend: SSE Endpoint Enhancement
**Modified: `sis/api/routes/sse.py`**

Read from progress store instead of DB. Emit full snapshot every 1s. Fall back to DB for completed runs not in memory.

### Backend: Analysis API Change
**Modified: `sis/api/routes/analyses.py`**

`POST /api/analyses/` now:
1. Creates `AnalysisRun` row immediately (status=running) and returns real `run_id`
2. Passes `run_id` to pipeline thread so progress store is keyed correctly
3. Frontend connects SSE with this `run_id`

### Frontend: Progress Component
**New: `frontend/src/components/analysis-progress-detail.tsx`**

Displays:
1. Overall progress bar (X/10 agents)
2. Agent list — 10 rows with: name, status icon (spinner/check/X/dash), elapsed, tokens, cost
3. Running totals footer — total cost, total time
4. On completion: success banner + "View Deal Detail" link

### Frontend: Upload Page Integration
**Modified: `frontend/src/app/upload/page.tsx`**

After import succeeds and analysis starts:
- Hide the calls table and import button
- Show the detailed progress component with the returned `run_id`
- No redirect to /analyze
- On completion: show results link to `/deals/{account_id}`

## Agent Names (for display)
1. Stage & Progress
2. Relationship & Power Map
3. Commercial & Risk
4. Momentum & Engagement
5. Technical Validation
6. Economic Buyer
7. MSP & Next Steps
8. Competitive Displacement
9. Open Discovery
10. Synthesis

## Files to Create/Modify
- **Create:** `sis/orchestrator/progress_store.py`
- **Create:** `frontend/src/components/analysis-progress-detail.tsx`
- **Modify:** `sis/orchestrator/pipeline.py` — per-agent progress + as_completed
- **Modify:** `sis/api/routes/sse.py` — read from progress store
- **Modify:** `sis/api/routes/analyses.py` — return real run_id, pass to pipeline
- **Modify:** `sis/services/analysis_service.py` — accept/pass run_id
- **Modify:** `frontend/src/app/upload/page.tsx` — show progress inline
- **Modify:** `frontend/src/lib/api.ts` — no changes needed (SSE via EventSource)

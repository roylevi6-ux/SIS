# Batch Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to select up to 10 accounts from Google Drive, tag each with deal type + IC + call count, and run all imports + analyses in parallel with real-time batch progress tracking.

**Architecture:** New `POST /api/analyses/batch` endpoint accepts a list of account items, queues them in a `batch_store` (same pattern as `progress_store`), and processes up to `BATCH_CONCURRENCY` (default 3) pipelines concurrently via a `ThreadPoolExecutor`. A new batch SSE endpoint streams progress. The frontend replaces the single-account Google Drive selector with a multi-select table and adds a `BatchProgressView` component.

**Tech Stack:** FastAPI, Pydantic, threading, SSE, React, shadcn/ui, EventSource

**Design Doc:** `docs/plans/2026-02-25-batch-analysis-design.md`

---

## Task 1: Backend — Batch Store Module

**Files:**
- Create: `sis/orchestrator/batch_store.py`

**Step 1: Create batch_store.py**

This module mirrors the pattern in `sis/orchestrator/progress_store.py` — thread-safe in-memory dict keyed by `batch_id`.

```python
"""In-memory batch progress store for multi-account import + analysis.

Thread-safe dict keyed by batch_id. Each entry holds per-account status
within the batch. Auto-cleaned 10 minutes after terminal status.

Used by:
- analyses.py: writes per-account progress as batch executes
- sse.py: reads batch snapshots for SSE streaming to frontend
"""

from __future__ import annotations

import copy
import threading
import uuid
from datetime import datetime, timezone
from typing import Literal

_lock = threading.Lock()
_store: dict[str, dict] = {}
_CLEANUP_DELAY = 600  # 10 minutes

ItemStatus = Literal["queued", "uploading", "analyzing", "completed", "failed"]
BatchStatus = Literal["running", "completed", "partial", "failed"]


def create_batch(items: list[dict]) -> dict:
    """Create a new batch entry with all items in queued state.

    Args:
        items: List of dicts, each with at least 'account_name'.

    Returns:
        The initial batch snapshot (batch_id + items list).
    """
    batch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    batch_items = []
    for i, item in enumerate(items):
        batch_items.append({
            "index": i,
            "account_name": item["account_name"],
            "status": "queued",
            "account_id": None,
            "run_id": None,
            "error": None,
            "imported_count": 0,
            "skipped_count": 0,
            "elapsed_seconds": None,
            "cost_usd": None,
        })

    entry = {
        "batch_id": batch_id,
        "status": "running",
        "created_at": now,
        "items": batch_items,
        "total_items": len(batch_items),
        "completed_count": 0,
        "failed_count": 0,
    }

    with _lock:
        _store[batch_id] = entry

    return copy.deepcopy(entry)


def update_item(
    batch_id: str,
    index: int,
    *,
    status: ItemStatus | None = None,
    account_id: str | None = None,
    run_id: str | None = None,
    error: str | None = None,
    imported_count: int | None = None,
    skipped_count: int | None = None,
    elapsed_seconds: float | None = None,
    cost_usd: float | None = None,
) -> None:
    """Update a single item within a batch."""
    with _lock:
        entry = _store.get(batch_id)
        if not entry:
            return
        item = entry["items"][index]
        if status is not None:
            item["status"] = status
        if account_id is not None:
            item["account_id"] = account_id
        if run_id is not None:
            item["run_id"] = run_id
        if error is not None:
            item["error"] = error
        if imported_count is not None:
            item["imported_count"] = imported_count
        if skipped_count is not None:
            item["skipped_count"] = skipped_count
        if elapsed_seconds is not None:
            item["elapsed_seconds"] = round(elapsed_seconds, 1)
        if cost_usd is not None:
            item["cost_usd"] = round(cost_usd, 4)
        _recompute_batch(entry)


def get_snapshot(batch_id: str) -> dict | None:
    """Get a read-only snapshot of the batch."""
    with _lock:
        entry = _store.get(batch_id)
        if not entry:
            return None
        return copy.deepcopy(entry)


def _recompute_batch(entry: dict) -> None:
    """Recompute batch-level counts. Caller must hold _lock."""
    completed = sum(1 for i in entry["items"] if i["status"] == "completed")
    failed = sum(1 for i in entry["items"] if i["status"] == "failed")
    entry["completed_count"] = completed
    entry["failed_count"] = failed

    total = entry["total_items"]
    if completed + failed == total:
        if failed == total:
            entry["status"] = "failed"
        elif failed > 0:
            entry["status"] = "partial"
        else:
            entry["status"] = "completed"
        # Schedule cleanup
        cleanup = threading.Timer(_CLEANUP_DELAY, _cleanup_batch, args=[entry["batch_id"]])
        cleanup.daemon = True
        cleanup.start()


def _cleanup_batch(batch_id: str) -> None:
    """Remove a batch from the store after cleanup delay."""
    with _lock:
        _store.pop(batch_id, None)
```

**Step 2: Verify module imports cleanly**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.orchestrator.batch_store import create_batch, update_item, get_snapshot; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add sis/orchestrator/batch_store.py
git commit -m "feat: add batch_store module for multi-account progress tracking"
```

---

## Task 2: Backend — Batch Schemas

**Files:**
- Modify: `sis/api/schemas/analyses.py`

**Step 1: Add batch request/response schemas**

Add these classes to the end of `sis/api/schemas/analyses.py`:

```python
# ── Batch Analysis ──────────────────────────────────────────────────


class BatchItemRequest(BaseModel):
    """Single account in a batch analysis request."""
    account_name: str
    drive_path: str
    max_calls: int = 5
    deal_type: Optional[str] = None
    mrr_estimate: Optional[float] = None
    owner_id: Optional[str] = None


class BatchAnalysisRequest(BaseModel):
    """Request to import + analyze multiple accounts."""
    items: List[BatchItemRequest]


class BatchItemResponse(BaseModel):
    """Single account status in batch response."""
    account_name: str
    status: str
    account_id: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None
    imported_count: int = 0
    skipped_count: int = 0
    elapsed_seconds: Optional[float] = None
    cost_usd: Optional[float] = None


class BatchAnalysisResponse(BaseModel):
    """Response after starting a batch analysis."""
    batch_id: str
    status: str
    total_items: int
    completed_count: int
    failed_count: int
    items: List[BatchItemResponse]
```

**Step 2: Verify schemas parse correctly**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.api.schemas.analyses import BatchAnalysisRequest, BatchAnalysisResponse; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add sis/api/schemas/analyses.py
git commit -m "feat: add Pydantic schemas for batch analysis endpoint"
```

---

## Task 3: Backend — Batch Endpoint + Worker

**Files:**
- Modify: `sis/api/routes/analyses.py`

**Step 1: Add the batch endpoint and worker function**

Add these imports at the top of `analyses.py` (alongside existing imports):

```python
import os
import time
import logging

from sis.api.schemas.analyses import BatchAnalysisRequest, BatchAnalysisResponse
from sis.orchestrator.batch_store import create_batch, update_item, get_snapshot as get_batch_snapshot
```

Add the batch worker function (below the existing `_run_pipeline_sync`):

```python
BATCH_CONCURRENCY = int(os.environ.get("BATCH_CONCURRENCY", "3"))
batch_executor = ThreadPoolExecutor(max_workers=BATCH_CONCURRENCY)

logger = logging.getLogger(__name__)


def _run_batch_item(batch_id: str, index: int, item_data: dict):
    """Process one account in a batch: import from Drive → run analysis.

    Args:
        batch_id: Batch this item belongs to.
        index: Item index in the batch.
        item_data: Dict with account_name, drive_path, max_calls, deal_type, owner_id, mrr_estimate.
    """
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

        if not account_id:
            acct_obj = create_account(
                name=item_data["account_name"],
                deal_type=normalize_deal_type(item_data.get("deal_type")),
                mrr=item_data.get("mrr_estimate"),
                owner_id=item_data.get("owner_id"),
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

    # Wait for all to complete (each future updates batch_store independently)
    concurrent.futures.wait(futures)
```

Add the endpoint:

```python
@router.post("/batch", response_model=BatchAnalysisResponse)
async def run_batch_analysis(body: BatchAnalysisRequest, user: dict = Depends(get_current_user)):
    """Start batch import + analysis for multiple accounts.

    Returns immediately with a batch_id. Poll via SSE at /api/sse/batch/{batch_id}.
    """
    if len(body.items) > 10:
        raise HTTPException(422, "Maximum 10 accounts per batch")
    if len(body.items) == 0:
        raise HTTPException(422, "At least one account required")

    # Build item dicts for the worker
    item_dicts = [item.model_dump() for item in body.items]

    # Create batch in store
    batch = create_batch(item_dicts)

    # Spawn batch orchestrator in background thread
    import threading
    t = threading.Thread(target=_run_batch, args=(batch["batch_id"], item_dicts), daemon=True)
    t.start()

    return batch
```

**Step 2: Verify server starts without errors**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.api.routes.analyses import router; print('routes:', [r.path for r in router.routes])"`
Expected: Should include `/batch` in the routes list.

**Step 3: Commit**

```bash
git add sis/api/routes/analyses.py
git commit -m "feat: add POST /api/analyses/batch endpoint with concurrency-limited worker"
```

---

## Task 4: Backend — Batch SSE Endpoint

**Files:**
- Modify: `sis/api/routes/sse.py`

**Step 1: Add batch SSE route**

Add this import at the top of `sse.py`:

```python
from sis.orchestrator.batch_store import get_snapshot as get_batch_snapshot
```

Add this route below the existing `analysis_progress` endpoint:

```python
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
```

**Step 2: Verify endpoint registers**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.api.routes.sse import router; print('routes:', [r.path for r in router.routes])"`
Expected: Should include `/batch/{batch_id}`.

**Step 3: Commit**

```bash
git add sis/api/routes/sse.py
git commit -m "feat: add GET /api/sse/batch/{batch_id} for batch progress streaming"
```

---

## Task 5: Frontend — Batch Types + API Method

**Files:**
- Modify: `frontend/src/lib/api-types.ts`
- Modify: `frontend/src/lib/api.ts`

**Step 1: Add batch types to api-types.ts**

Append to the end of `frontend/src/lib/api-types.ts`:

```typescript
// ── Batch Analysis ──
export interface BatchItemRequest {
  account_name: string;
  drive_path: string;
  max_calls: number;
  deal_type?: string;
  mrr_estimate?: number;
  owner_id?: string;
}

export interface BatchItem {
  index: number;
  account_name: string;
  status: 'queued' | 'uploading' | 'analyzing' | 'completed' | 'failed';
  account_id: string | null;
  run_id: string | null;
  error: string | null;
  imported_count: number;
  skipped_count: number;
  elapsed_seconds: number | null;
  cost_usd: number | null;
}

export interface BatchAnalysisResponse {
  batch_id: string;
  status: 'running' | 'completed' | 'partial' | 'failed';
  total_items: number;
  completed_count: number;
  failed_count: number;
  items: BatchItem[];
}
```

**Step 2: Add batch API method to api.ts**

Add the import for the new types at the top of `api.ts` (in the existing import block):

```typescript
import type {
  // ... existing imports ...
  BatchItemRequest,
  BatchAnalysisResponse,
} from './api-types';
```

Add inside the `analyses` object in `api.ts` (after the existing `carryForwardActions` method):

```typescript
    batch: (items: BatchItemRequest[]) =>
      apiFetch<BatchAnalysisResponse>('/api/analyses/batch', {
        method: 'POST',
        body: JSON.stringify({ items }),
      }),
```

**Step 3: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend
git add src/lib/api-types.ts src/lib/api.ts
git commit -m "feat: add batch analysis types and API method"
```

---

## Task 6: Frontend — Batch SSE Hook

**Files:**
- Create: `frontend/src/lib/hooks/use-batch-analysis.ts`

**Step 1: Create the hook**

```typescript
'use client';

import { useEffect, useState, useRef } from 'react';
import type { BatchAnalysisResponse } from '@/lib/api-types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Hook that connects to the batch SSE endpoint and returns live progress.
 * Automatically closes when all items reach terminal status.
 */
export function useBatchProgress(batchId: string | null) {
  const [batch, setBatch] = useState<BatchAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!batchId) return;

    const es = new EventSource(`${API_BASE}/api/sse/batch/${batchId}`);

    es.onmessage = (event) => {
      try {
        const data: BatchAnalysisResponse = JSON.parse(event.data);
        setBatch(data);
        if (['completed', 'failed', 'partial', 'not_found', 'timeout'].includes(data.status)) {
          es.close();
        }
      } catch {
        // Malformed JSON — ignore
      }
    };

    es.onerror = () => {
      es.close();
      setError('Connection to batch progress stream lost');
    };

    return () => {
      es.close();
    };
  }, [batchId]);

  const isTerminal = batch?.status === 'completed' || batch?.status === 'failed' || batch?.status === 'partial';

  return { batch, error, isTerminal };
}
```

**Step 2: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend
git add src/lib/hooks/use-batch-analysis.ts
git commit -m "feat: add useBatchProgress hook for batch SSE streaming"
```

---

## Task 7: Frontend — BatchProgressView Component

**Files:**
- Create: `frontend/src/components/batch-progress-view.tsx`

**Step 1: Create the component**

This component shows the summary grid from the design doc. It reuses the existing `AnalysisProgressDetail` component for expanded per-agent detail.

```tsx
'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronRight,
  Upload,
  ExternalLink,
  RotateCcw,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { AnalysisProgressDetail } from '@/components/analysis-progress-detail';
import { useBatchProgress } from '@/lib/hooks/use-batch-analysis';
import type { BatchItem } from '@/lib/api-types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

function statusIcon(status: BatchItem['status']) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="size-4 text-emerald-500" />;
    case 'failed':
      return <XCircle className="size-4 text-destructive" />;
    case 'uploading':
      return <Upload className="size-4 animate-pulse text-blue-500" />;
    case 'analyzing':
      return <Loader2 className="size-4 animate-spin text-primary" />;
    case 'queued':
    default:
      return <Clock className="size-4 text-muted-foreground/40" />;
  }
}

function statusLabel(status: BatchItem['status']): string {
  switch (status) {
    case 'completed': return 'Done';
    case 'failed': return 'Failed';
    case 'uploading': return 'Uploading...';
    case 'analyzing': return 'Analyzing...';
    case 'queued': return 'Queued';
    default: return status;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface BatchProgressViewProps {
  batchId: string;
  onRetryItem?: (item: BatchItem) => void;
}

export function BatchProgressView({ batchId, onRetryItem }: BatchProgressViewProps) {
  const { batch, error, isTerminal } = useBatchProgress(batchId);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (error && !batch) {
    return (
      <Card className="border-destructive">
        <CardContent className="flex items-center gap-3 py-6">
          <XCircle className="size-5 text-destructive shrink-0" />
          <div>
            <p className="text-sm font-medium">Connection lost</p>
            <p className="text-xs text-muted-foreground">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!batch) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-6">
          <Loader2 className="size-5 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Connecting to batch progress...</p>
        </CardContent>
      </Card>
    );
  }

  const totalItems = batch.total_items;
  const doneCount = batch.completed_count + batch.failed_count;
  const progressPct = totalItems > 0 ? (batch.completed_count / totalItems) * 100 : 0;

  const totalCost = batch.items.reduce((sum, i) => sum + (i.cost_usd ?? 0), 0);
  const totalElapsed = batch.items.reduce((max, i) => Math.max(max, i.elapsed_seconds ?? 0), 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">
          {isTerminal
            ? `Batch Complete — ${batch.completed_count}/${totalItems} succeeded`
            : `Batch Analysis — ${batch.completed_count}/${totalItems} complete`}
        </CardTitle>
        <Progress value={progressPct} className="h-2 mt-2" />
        {isTerminal && (
          <p className="text-xs text-muted-foreground mt-1">
            Total: {formatElapsed(totalElapsed)} · {formatCost(totalCost)}
            {batch.failed_count > 0 && ` · ${batch.failed_count} failed`}
          </p>
        )}
      </CardHeader>

      <CardContent className="space-y-0 pt-0">
        <div className="divide-y divide-border/50">
          {batch.items.map((item) => {
            const isExpanded = expandedIndex === item.index;
            const canExpand = item.status === 'analyzing' && item.run_id;
            const isComplete = item.status === 'completed';

            return (
              <div key={item.index}>
                {/* Summary row */}
                <div
                  className={`flex items-center gap-3 py-2.5 text-sm ${canExpand || isComplete ? 'cursor-pointer hover:bg-muted/50 rounded-md px-1 -mx-1' : ''}`}
                  onClick={() => {
                    if (canExpand || isComplete) {
                      setExpandedIndex(isExpanded ? null : item.index);
                    }
                  }}
                >
                  {/* Expand chevron */}
                  <div className="w-4 shrink-0">
                    {(canExpand || isComplete) && (
                      isExpanded
                        ? <ChevronDown className="size-3.5 text-muted-foreground" />
                        : <ChevronRight className="size-3.5 text-muted-foreground" />
                    )}
                  </div>

                  {/* Status icon */}
                  <div className="w-5 shrink-0 flex justify-center">
                    {statusIcon(item.status)}
                  </div>

                  {/* Account name */}
                  <span className={`flex-1 font-medium ${item.status === 'queued' ? 'text-muted-foreground/60' : ''}`}>
                    {item.account_name}
                  </span>

                  {/* Status label */}
                  <span className="w-24 text-xs text-muted-foreground">
                    {statusLabel(item.status)}
                  </span>

                  {/* Elapsed */}
                  <span className="w-14 text-right text-xs text-muted-foreground tabular-nums">
                    {item.elapsed_seconds != null ? formatElapsed(item.elapsed_seconds) : ''}
                  </span>

                  {/* Cost */}
                  <span className="w-16 text-right text-xs text-muted-foreground tabular-nums">
                    {item.cost_usd != null ? formatCost(item.cost_usd) : ''}
                  </span>

                  {/* Action */}
                  <div className="w-20 text-right">
                    {isComplete && item.account_id && (
                      <Button asChild variant="ghost" size="sm" className="h-6 text-xs">
                        <Link href={`/deals/${item.account_id}`}>
                          View <ExternalLink className="size-3 ml-1" />
                        </Link>
                      </Button>
                    )}
                    {item.status === 'failed' && onRetryItem && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs"
                        onClick={(e) => { e.stopPropagation(); onRetryItem(item); }}
                      >
                        <RotateCcw className="size-3 mr-1" /> Retry
                      </Button>
                    )}
                  </div>
                </div>

                {/* Error message */}
                {item.status === 'failed' && item.error && (
                  <div className="ml-9 mb-2 text-xs text-destructive">{item.error}</div>
                )}

                {/* Expanded: per-agent detail */}
                {isExpanded && item.run_id && item.account_id && (
                  <div className="ml-9 mb-3">
                    <AnalysisProgressDetail
                      runId={item.run_id}
                      accountId={item.account_id}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend
git add src/components/batch-progress-view.tsx
git commit -m "feat: add BatchProgressView component with expandable agent detail"
```

---

## Task 8: Frontend — Multi-Select Upload Table

**Files:**
- Modify: `frontend/src/app/upload/page.tsx`

This is the largest frontend change. The Google Drive tab's single-account `<Select>` becomes a multi-select table with per-row checkboxes, call count input, deal type dropdown, and IC dropdown. On submit, it calls the batch endpoint and transitions to the `BatchProgressView`.

**Step 1: Add state and types for batch selection**

At the top of the Google Drive tab component (the `GoogleDriveTab` function), replace the single-account selection state with batch state:

```typescript
// Replace these single-account states:
//   const [selectedAccount, setSelectedAccount] = useState<DriveAccount | null>(null);
//   const [recentCalls, setRecentCalls] = useState<DriveCall[]>([]);
//   etc.
// With:

interface BatchRow {
  account: DriveAccount;
  selected: boolean;
  maxCalls: number;
  dealType: string;
  ownerId: string;
  ownerIC: ICUser | null;
}

const [batchRows, setBatchRows] = useState<BatchRow[]>([]);
const [batchId, setBatchId] = useState<string | null>(null);
const [batchError, setBatchError] = useState<string>('');
const [isSubmitting, setIsSubmitting] = useState(false);

const MAX_BATCH_SIZE = 10;
```

**Step 2: Update account list loading**

When `driveAccounts` is loaded (after path validation), initialize `batchRows`:

```typescript
// After: setDriveAccounts(accounts);
setBatchRows(accounts.map((a) => ({
  account: a,
  selected: false,
  maxCalls: Math.min(5, a.call_count),
  dealType: '',
  ownerId: '',
  ownerIC: null,
})));
```

**Step 3: Build the selection table**

Replace the single-account `<Select>` and the "Recent calls" table with a multi-select table. The table has columns: checkbox, account name, calls (input "N of M"), deal type dropdown, IC dropdown.

Key behaviors:
- `checkbox.onChange` → toggle `selected` on that row. Disable checkbox if 10 already selected and this one isn't.
- `maxCalls` input: type=number, min=1, max=account.call_count, only shown when selected.
- Deal type and IC dropdowns: only shown when selected.
- Submit button: disabled unless every selected row has dealType and ownerId filled. Shows count: "Import & Analyze N Accounts".

**Step 4: Handle submit**

```typescript
async function handleBatchSubmit() {
  const selected = batchRows.filter((r) => r.selected);
  if (selected.length === 0) return;

  setIsSubmitting(true);
  setBatchError('');

  try {
    const items = selected.map((r) => ({
      account_name: r.account.name,
      drive_path: r.account.path,
      max_calls: r.maxCalls,
      deal_type: r.dealType || undefined,
      owner_id: r.ownerId || undefined,
    }));

    const result = await api.analyses.batch(items);
    setBatchId(result.batch_id);
  } catch (err) {
    setBatchError(err instanceof Error ? err.message : 'Batch submission failed');
  } finally {
    setIsSubmitting(false);
  }
}
```

**Step 5: Show BatchProgressView when batch is running**

```typescript
// At the top of the component's return:
if (batchId) {
  return <BatchProgressView batchId={batchId} />;
}
```

**Step 6: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend
git add src/app/upload/page.tsx
git commit -m "feat: replace single-account selector with multi-select batch table"
```

---

## Task 9: Integration Test — End-to-End Batch Flow

**Files:**
- The existing codebase has no test directory structure. This task validates the batch flow manually.

**Step 1: Start the backend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m uvicorn sis.api.app:app --reload --port 8000`

**Step 2: Test batch endpoint with curl**

```bash
curl -X POST http://localhost:8000/api/analyses/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "items": [
      {"account_name": "TestAccount1", "drive_path": "/tmp/test", "max_calls": 3, "deal_type": "New Logo"},
      {"account_name": "TestAccount2", "drive_path": "/tmp/test", "max_calls": 5, "deal_type": "Renewal"}
    ]
  }'
```

Expected: `{"batch_id": "...", "status": "running", "total_items": 2, ...}`

**Step 3: Test validation — too many items**

```bash
curl -X POST http://localhost:8000/api/analyses/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"items": [{"account_name":"a","drive_path":"/tmp","max_calls":1},{"account_name":"b","drive_path":"/tmp","max_calls":1},{"account_name":"c","drive_path":"/tmp","max_calls":1},{"account_name":"d","drive_path":"/tmp","max_calls":1},{"account_name":"e","drive_path":"/tmp","max_calls":1},{"account_name":"f","drive_path":"/tmp","max_calls":1},{"account_name":"g","drive_path":"/tmp","max_calls":1},{"account_name":"h","drive_path":"/tmp","max_calls":1},{"account_name":"i","drive_path":"/tmp","max_calls":1},{"account_name":"j","drive_path":"/tmp","max_calls":1},{"account_name":"k","drive_path":"/tmp","max_calls":1}]}'
```

Expected: `422 — "Maximum 10 accounts per batch"`

**Step 4: Test batch SSE**

```bash
curl -N http://localhost:8000/api/sse/batch/<batch_id_from_step_2>
```

Expected: Streaming JSON events with batch status updates.

**Step 5: Test frontend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run dev`

Navigate to `/upload`, switch to Google Drive tab, enter a valid drive path, verify the multi-select table appears with checkboxes, per-row call count inputs, deal type, and IC dropdowns.

**Step 6: Commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix: integration fixes for batch analysis flow"
```

---

## Task 10: Keep Single-Account Flow Working

**Files:**
- Verify: `frontend/src/app/upload/page.tsx` — the Paste and Local Folder tabs are untouched
- Verify: `sis/api/routes/analyses.py` — `POST /api/analyses/` single-account endpoint unchanged

**Step 1: Verify single-account analysis still works**

Navigate to `/upload`, use the Paste tab, create an account with a pasted transcript, run analysis. Confirm SSE progress and completion work as before.

**Step 2: Verify local folder tab still works**

The Local Folder tab should also get the batch treatment (it uses the same GDrive service under the hood). If it still uses the single-account flow, that's fine for v1 — batch is only for the Google Drive tab.

**Step 3: Commit if no changes needed**

No commit needed if everything passes.

---

## Dependency Order

```
Task 1 (batch_store) ─┐
Task 2 (schemas)      ─┼─> Task 3 (endpoint) ─> Task 4 (SSE) ─┐
                       │                                        │
Task 5 (FE types/api) ─> Task 6 (SSE hook) ─> Task 7 (BatchProgressView) ─> Task 8 (upload page) ─> Task 9 (integration)
                                                                                                        │
                                                                                                  Task 10 (regression)
```

Tasks 1-2 and Task 5 can run in parallel (backend schemas + frontend types are independent).
Tasks 3-4 depend on Tasks 1-2.
Tasks 6-7 depend on Task 5.
Task 8 depends on Tasks 5-7.
Task 9 depends on all prior tasks.
Task 10 is a final regression check.

# Batch Analysis — Design Document

**Date**: 2026-02-25
**Status**: Approved

## Problem

Today, importing and analyzing accounts is one-at-a-time: select an account from Google Drive, tag deal type + IC, upload transcripts, wait for analysis to finish, then repeat. For a VP running 10 accounts through the system, this means 10 sequential round-trips — slow and tedious.

## Solution

A batch import & analysis flow: select up to 10 accounts from the Google Drive scan, tag each with deal type, IC, and number of calls to import, then kick off all uploads + analyses in parallel with a single click. A summary grid shows real-time progress across all accounts.

---

## UX Design

### Selection Table

After scanning the Google Drive folder, the account list becomes a multi-select table:

```
┌──────────────────────────────────────────────────────────────────┐
│ Select accounts to import (3 of 12 selected)                     │
├─────┬──────────────┬──────────────┬────────────┬────────────────┤
│  [x]│ Airalo       │ 5 of 34      │ [New Logo] │ [J. Smith]     │
│  [x]│ Wirex        │ 5 of 12      │ [Upsell  ] │ [M. Jones]     │
│  [x]│ Babyboo      │ 3 of 3       │ [New Logo] │ [J. Smith]     │
│  [ ]│ Rakuten      │   — 28 avail │            │                │
│  [ ]│ Abound       │   —  6 avail │            │                │
└─────┴──────────────┴──────────────┴────────────┴────────────────┘
│              [ Import & Analyze 3 Accounts ]                     │
└──────────────────────────────────────────────────────────────────┘
```

**Behaviors:**
- Unchecked rows show `— N avail` in muted text (read-only).
- Checked rows show a number input defaulting to 5 (or total if < 5), with `of N` showing available count. Input clamped 1–N.
- Deal type and IC dropdowns only appear on checked rows.
- "Import & Analyze" button disabled unless every checked row has deal type + IC filled.
- Maximum 10 accounts selected at once (checkbox disabled after 10).
- `call_count` from `list_account_folders()` provides the available count.

### Progress View

After clicking "Import & Analyze N Accounts", the page transitions to:

```
┌──────────────────────────────────────────────────────────┐
│  Batch Analysis — 2/5 complete                            │
│  ████████████░░░░░░░░░░░░░░  40%                          │
├──────────────────────────────────────────────────────────┤
│  Done  Airalo         12.4s   $0.08          [View ->]   │
│  Done  Wirex           9.1s   $0.06          [View ->]   │
│  5/10  Babyboo                running...                  │
│  Wait  Rakuten        Queued                              │
│  Wait  Direct Group   Queued                              │
├──────────────────────────────────────────────────────────┤
│  v Babyboo — Agent Detail                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Done  Stage & Progress      2.1s   $0.01           │  │
│  │ Done  Relationship Map      3.4s   $0.02           │  │
│  │ Run   Technical Validation  running...              │  │
│  │ Wait  Economic Buyer        pending                 │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Behaviors:**
- Each row clickable to expand per-agent detail (reuses `AnalysisProgressDetail`).
- "View ->" on completed accounts navigates to deal detail page.
- Failed accounts show error inline with retry button.
- Completion banner: "Batch complete — 5/5 analyzed. Total: 52.3s, $0.41"

---

## Backend Architecture

### Controlled Concurrency Queue

10 accounts queued, 3 run concurrently (configurable via `BATCH_CONCURRENCY` env var, default 3). Each slot runs the full sequence:
1. Create/find account in DB
2. Upload transcripts from Google Drive (with dedup)
3. Run analysis pipeline (10 agents)

When a slot finishes, the next queued account starts automatically.

At 3 concurrent pipelines, peak LLM load is ~24 concurrent requests (3 pipelines x 8 parallel agents). Well within Anthropic Claude's paid-tier rate limits (~50+ concurrent).

### New Endpoint: `POST /api/analyses/batch`

**Request:**
```json
{
  "items": [
    {
      "account_name": "Airalo",
      "drive_path": "/path/to/folder",
      "max_calls": 5,
      "deal_type": "New Logo",
      "owner_id": "user-uuid-123",
      "mrr_estimate": 5000
    }
  ]
}
```

**Response (immediate):**
```json
{
  "batch_id": "batch-uuid",
  "items": [
    { "account_name": "Airalo", "status": "queued", "run_id": null },
    { "account_name": "Wirex", "status": "queued", "run_id": null }
  ]
}
```

### Batch Store (`batch_store.py`)

In-memory thread-safe dict (same pattern as `progress_store.py`), keyed by `batch_id`. Tracks per-account status within the batch:

```
queued -> uploading -> analyzing -> completed | failed
```

Each item tracks: `account_name`, `status`, `account_id` (once created), `run_id` (once analysis starts), `error` (if failed), `imported_count`, `skipped_count`, `elapsed_seconds`, `cost_usd`.

Auto-cleanup after 10 minutes of terminal state.

### New SSE Endpoint: `GET /api/sse/batch/{batch_id}`

Streams batch-level progress at 1s intervals. Each event contains the full batch snapshot (all items with their current status). The frontend combines this with per-run SSE for agent-level drill-down.

### Concurrency Implementation

The existing `ThreadPoolExecutor(max_workers=4)` in `analyses.py` stays for single-account runs. The batch endpoint uses its own executor with `max_workers=BATCH_CONCURRENCY` (default 3). This prevents runaway LLM calls while still finishing a 10-account batch in ~50-75 seconds.

`BATCH_CONCURRENCY` is an env var — tune up to 4-5 if Anthropic rate limits allow, or down to 2 if needed.

---

## Change Summary

| Layer | What | Type |
|-------|------|------|
| Backend | `sis/api/routes/analyses.py` — add `POST /batch` endpoint | Modified |
| Backend | `sis/orchestrator/batch_store.py` — batch progress tracking | New |
| Backend | `sis/api/routes/sse.py` — add `GET /batch/{batch_id}` SSE | Modified |
| Backend | `sis/api/schemas/analyses.py` — batch request/response schemas | Modified |
| Frontend | `frontend/src/app/upload/page.tsx` — multi-select table with per-row config | Modified |
| Frontend | `frontend/src/components/batch-progress-view.tsx` — summary grid + expandable detail | New |
| Frontend | `frontend/src/lib/api.ts` — `analyses.batch()` method | Modified |
| Frontend | `frontend/src/lib/api-types.ts` — batch types | Modified |
| Frontend | `frontend/src/lib/hooks/use-batch-analysis.ts` — batch SSE hook | New |

**Unchanged:** Single-account upload flow, per-agent progress store, per-run SSE endpoint, analysis pipeline, Google Drive service (already returns `call_count`).

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LLM rate limits with 3 concurrent pipelines | 3-slot queue caps at ~24 concurrent LLM calls. Well within Anthropic paid tier. `BATCH_CONCURRENCY` env var to tune. |
| Batch takes too long (10 accounts x ~15s each) | 3 concurrent slots = ~4 rounds = ~60s total. Acceptable with real-time progress. |
| User closes tab mid-batch | Backend runs independently of frontend. Batch completes even without SSE consumer. |
| Memory pressure from 3 concurrent pipelines | Each pipeline is ~50MB peak. 3 concurrent = ~150MB. Fine for current deployment. |
| Cost spike from large batches | 10 accounts x ~$0.08 = ~$0.80 per batch. Future: wire up RunBudget for cost guard. |

"""In-memory progress store for multi-account batch import/analysis tracking.

Thread-safe dict keyed by batch_id. Each entry holds the batch-level status
plus a per-item list with individual account status, run linkage, import
counts, and cost. Auto-cleaned 10 minutes after the batch reaches a terminal
state.

Used by:
- batch_pipeline.py (or equivalent): writes item progress as accounts are
  imported and analyzed in parallel
- batch_sse.py (or equivalent): reads snapshots for SSE streaming to frontend
"""

from __future__ import annotations

import copy
import threading
import uuid
from datetime import datetime, timezone
from typing import Literal

ItemStatus = Literal["queued", "uploading", "analyzing", "completed", "failed"]
BatchStatus = Literal["running", "completed", "partial", "failed"]

_lock = threading.Lock()
_store: dict[str, dict] = {}
_CLEANUP_DELAY = 600  # 10 minutes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_batch(items: list[dict]) -> dict:
    """Create a new batch entry and return a deepcopy of it.

    Each item in *items* must contain at least an ``account_name`` key.
    Additional keys in each item dict are ignored.

    Returns a deepcopy of the stored batch entry so the caller cannot mutate
    internal state.
    """
    batch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    batch_items = []
    for index, item in enumerate(items):
        batch_items.append(
            {
                "index": index,
                "account_name": item.get("account_name", ""),
                "status": "queued",
                "account_id": None,
                "run_id": None,
                "error": None,
                "imported_count": 0,
                "skipped_count": 0,
                "elapsed_seconds": None,
                "cost_usd": None,
            }
        )

    entry: dict = {
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
    """Update fields on a single item within a batch.

    Only non-None keyword arguments are written so callers can do partial
    updates without overwriting previously set values.

    Raises ``KeyError`` if *batch_id* does not exist.
    Raises ``IndexError`` if *index* is out of range.
    """
    with _lock:
        entry = _store.get(batch_id)
        if entry is None:
            raise KeyError(f"batch_id not found: {batch_id}")

        item = entry["items"][index]  # raises IndexError if out of range

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


def cancel_batch(batch_id: str) -> list[str]:
    """Cancel all non-terminal items in a batch. Returns list of run_ids to cancel."""
    run_ids = []
    with _lock:
        entry = _store.get(batch_id)
        if entry is None:
            return run_ids
        for item in entry["items"]:
            if item["status"] not in _TERMINAL_ITEM_STATUSES:
                if item.get("run_id"):
                    run_ids.append(item["run_id"])
                item["status"] = "failed"
                item["error"] = "Cancelled by user"
        _recompute_batch(entry)
    return run_ids


def get_snapshot(batch_id: str) -> dict | None:
    """Return a deepcopy of the batch entry, or None if not found."""
    with _lock:
        entry = _store.get(batch_id)
        if entry is None:
            return None
        return copy.deepcopy(entry)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TERMINAL_ITEM_STATUSES: frozenset[str] = frozenset({"completed", "failed"})


def _recompute_batch(entry: dict) -> None:
    """Recompute batch-level counters and status. Caller must hold _lock.

    Terminal item statuses: "completed" and "failed".
    Once all items are terminal the batch status is set to:
      - "completed" — zero failed items
      - "partial"   — some (but not all) items failed
      - "failed"    — every item failed
    A cleanup timer is scheduled when the batch becomes terminal.
    """
    completed = 0
    failed = 0

    for item in entry["items"]:
        if item["status"] == "completed":
            completed += 1
        elif item["status"] == "failed":
            failed += 1

    entry["completed_count"] = completed
    entry["failed_count"] = failed

    total = entry["total_items"]
    terminal_count = completed + failed

    if terminal_count < total:
        # Still items in progress — batch remains "running"
        return

    # All items are terminal: determine final batch status
    if failed == 0:
        entry["status"] = "completed"
    elif failed == total:
        entry["status"] = "failed"
    else:
        entry["status"] = "partial"

    # Schedule auto-cleanup outside the lock to avoid Timer holding _lock
    batch_id = entry["batch_id"]
    cleanup_thread = threading.Timer(_CLEANUP_DELAY, _cleanup_batch, args=[batch_id])
    cleanup_thread.daemon = True
    cleanup_thread.start()


def _cleanup_batch(batch_id: str) -> None:
    """Remove a batch from the store after the cleanup delay."""
    with _lock:
        _store.pop(batch_id, None)

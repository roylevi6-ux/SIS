"""In-memory progress store for sync jobs — SSE streaming source.

Thread-safe dict keyed by job_id. Each entry tracks per-account N8N extraction
status, Drive polling state, and import results.

Used by:
- sync_orchestrator.py: writes progress as sync executes
- Sync SSE endpoint: reads snapshots for streaming to frontend
"""

from __future__ import annotations

import copy
import threading
from typing import Any

_lock = threading.Lock()
_store: dict[str, dict] = {}


def init_sync(job_id: str, accounts: list[dict]) -> None:
    """Initialize sync entry with all accounts in pending state."""
    with _lock:
        _store[job_id] = {
            "job_id": job_id,
            "status": "running",
            "phase": "n8n_extraction",
            "total_accounts": len(accounts),
            "n8n_progress": {"completed": 0, "total": len(accounts), "current_account": None},
            "drive_poll": None,
            "import_progress": {"completed": 0, "total": len(accounts)},
            "accounts": {
                a["account_id"]: {
                    "name": a["account_name"],
                    "n8n_status": "pending",
                    "n8n_calls_found": None,
                    "import_status": "pending",
                    "calls_imported": 0,
                    "calls_skipped": 0,
                }
                for a in accounts
            },
            "summary": None,
            "errors": [],
            "_n8n_counted": set(),
            "_import_counted": set(),
        }


def update_n8n_status(
    job_id: str,
    account_id: str,
    status: str,
    calls_found: int | None = None,
    error: str | None = None,
) -> None:
    """Update N8N extraction status for a single account."""
    with _lock:
        entry = _store.get(job_id)
        if not entry:
            return
        acct = entry["accounts"].get(account_id, {})
        acct["n8n_status"] = status
        if calls_found is not None:
            acct["n8n_calls_found"] = calls_found
        if status in ("success", "failed", "skipped") and account_id not in entry["_n8n_counted"]:
            entry["_n8n_counted"].add(account_id)
            entry["n8n_progress"]["completed"] += 1
        if error:
            entry["errors"].append(f"N8N {acct.get('name', account_id)}: {error}")


def set_phase(job_id: str, phase: str, detail: dict | None = None) -> None:
    """Set the current sync phase, with optional extra fields."""
    with _lock:
        entry = _store.get(job_id)
        if not entry:
            return
        entry["phase"] = phase
        if detail:
            entry.update(detail)


def update_n8n_current(job_id: str, account_name: str) -> None:
    """Set which account is currently being processed by N8N."""
    with _lock:
        entry = _store.get(job_id)
        if entry:
            entry["n8n_progress"]["current_account"] = account_name


def update_drive_poll_status(
    job_id: str,
    elapsed_seconds: int,
    max_seconds: int,
    file_count: int,
    stable_checks: int,
) -> None:
    """Update Drive polling state (shown in UI during wait phase)."""
    with _lock:
        entry = _store.get(job_id)
        if not entry:
            return
        entry["drive_poll"] = {
            "elapsed_seconds": elapsed_seconds,
            "max_seconds": max_seconds,
            "file_count": file_count,
            "stable_checks": stable_checks,
            "needed_checks": 2,
            "status": "polling",
        }


def update_import_status(
    job_id: str,
    account_id: str,
    status: str,
    imported: int = 0,
    skipped: int = 0,
) -> None:
    """Update import status for a single account."""
    with _lock:
        entry = _store.get(job_id)
        if not entry:
            return
        acct = entry["accounts"].get(account_id, {})
        acct["import_status"] = status
        acct["calls_imported"] = imported
        acct["calls_skipped"] = skipped
        if status in ("done", "failed", "skipped") and account_id not in entry["_import_counted"]:
            entry["_import_counted"].add(account_id)
            entry["import_progress"]["completed"] += 1


def mark_sync_completed(job_id: str, summary: dict) -> None:
    """Mark the sync job as completed with final summary stats."""
    with _lock:
        entry = _store.get(job_id)
        if not entry:
            return
        entry["status"] = "completed"
        entry["phase"] = "completed"
        entry["summary"] = summary


def mark_sync_failed(job_id: str, error: str) -> None:
    """Mark the sync job as failed with an error message."""
    with _lock:
        entry = _store.get(job_id)
        if not entry:
            return
        entry["status"] = "failed"
        entry["phase"] = "failed"
        entry["errors"].append(error)


def get_sync_snapshot(job_id: str) -> dict | None:
    """Get a read-only deep copy of the current sync progress."""
    with _lock:
        entry = _store.get(job_id)
        if not entry:
            return None
        snapshot = copy.deepcopy(entry)
        # Strip internal tracking sets (not JSON-serializable)
        snapshot.pop("_n8n_counted", None)
        snapshot.pop("_import_counted", None)
        return snapshot


def cancel_sync(job_id: str) -> None:
    """Flag a sync job for cancellation."""
    with _lock:
        entry = _store.get(job_id)
        if entry:
            entry["status"] = "cancelled"
            entry["phase"] = "cancelled"


def is_sync_cancelled(job_id: str) -> bool:
    """Check if a sync job has been flagged for cancellation."""
    with _lock:
        entry = _store.get(job_id)
        return entry.get("status") == "cancelled" if entry else False


def cleanup_sync(job_id: str) -> None:
    """Remove sync entry from memory (call after SSE stream closes)."""
    with _lock:
        _store.pop(job_id, None)

"""In-memory progress store for real-time per-agent pipeline tracking.

Thread-safe dict keyed by run_id. Each entry holds per-agent status,
tokens, cost, elapsed time. Auto-cleaned 5 minutes after terminal status.

Used by:
- pipeline.py: writes agent progress as pipeline executes
- sse.py: reads progress snapshots for SSE streaming to frontend
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Literal

from sis.orchestrator.cost_tracker import calculate_cost

# Agent display names, ordered 1-10
AGENT_DISPLAY_NAMES = {
    "agent_1": "Stage & Progress",
    "agent_2": "Relationship & Power Map",
    "agent_3": "Commercial & Risk",
    "agent_4": "Momentum & Engagement",
    "agent_5": "Technical Validation",
    "agent_6": "Economic Buyer",
    "agent_7": "MSP & Next Steps",
    "agent_8": "Competitive Displacement",
    "agent_9": "Open Discovery",
    "agent_10": "Synthesis",
}

AgentStatus = Literal["pending", "running", "completed", "failed"]
RunStatus = Literal["running", "completed", "failed", "partial"]

_lock = threading.Lock()
_store: dict[str, dict] = {}
_CLEANUP_DELAY = 300  # 5 minutes


def init_run(run_id: str) -> None:
    """Initialize a new run entry with all 10 agents in pending state."""
    now = datetime.now(timezone.utc).isoformat()
    agents = {}
    for agent_id, name in AGENT_DISPLAY_NAMES.items():
        agents[agent_id] = {
            "status": "pending",
            "name": name,
            "started_at": None,
            "elapsed_seconds": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "model": None,
            "attempts": None,
            "error": None,
        }

    with _lock:
        _store[run_id] = {
            "run_id": run_id,
            "status": "running",
            "started_at": now,
            "agents": agents,
            "total_cost_usd": 0.0,
            "total_elapsed_seconds": 0.0,
            "errors": [],
        }


def mark_agent_running(run_id: str, agent_id: str) -> None:
    """Mark an agent as running."""
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        entry = _store.get(run_id)
        if not entry:
            return
        agent = entry["agents"].get(agent_id)
        if agent:
            agent["status"] = "running"
            agent["started_at"] = now


def mark_agent_completed(
    run_id: str,
    agent_id: str,
    input_tokens: int,
    output_tokens: int,
    elapsed_seconds: float,
    model: str,
    attempts: int = 1,
) -> None:
    """Mark an agent as completed with token/cost/time data."""
    cost = calculate_cost(model, input_tokens, output_tokens)
    with _lock:
        entry = _store.get(run_id)
        if not entry:
            return
        agent = entry["agents"].get(agent_id)
        if agent:
            agent["status"] = "completed"
            agent["input_tokens"] = input_tokens
            agent["output_tokens"] = output_tokens
            agent["elapsed_seconds"] = round(elapsed_seconds, 1)
            agent["cost_usd"] = round(cost, 4)
            agent["model"] = model
            agent["attempts"] = attempts
        _recompute_totals(entry)


def mark_agent_failed(run_id: str, agent_id: str, error: str) -> None:
    """Mark an agent as failed."""
    with _lock:
        entry = _store.get(run_id)
        if not entry:
            return
        agent = entry["agents"].get(agent_id)
        if agent:
            agent["status"] = "failed"
            agent["error"] = error
        entry["errors"].append(f"[{agent_id}] {error}")


def mark_run_completed(run_id: str, status: RunStatus = "completed") -> None:
    """Mark the overall run as completed/failed/partial."""
    with _lock:
        entry = _store.get(run_id)
        if not entry:
            return
        entry["status"] = status
        _recompute_totals(entry)

    # Schedule cleanup
    cleanup_thread = threading.Timer(_CLEANUP_DELAY, _cleanup_run, args=[run_id])
    cleanup_thread.daemon = True
    cleanup_thread.start()


def get_snapshot(run_id: str) -> dict | None:
    """Get a read-only snapshot of the current run progress."""
    with _lock:
        entry = _store.get(run_id)
        if not entry:
            return None
        # Deep copy to avoid mutation
        import copy
        return copy.deepcopy(entry)


def _recompute_totals(entry: dict) -> None:
    """Recompute total cost and elapsed from agent data. Caller must hold _lock."""
    total_cost = 0.0
    total_elapsed = 0.0
    for agent in entry["agents"].values():
        if agent["cost_usd"] is not None:
            total_cost += agent["cost_usd"]
        if agent["elapsed_seconds"] is not None:
            total_elapsed += agent["elapsed_seconds"]
    entry["total_cost_usd"] = round(total_cost, 4)
    entry["total_elapsed_seconds"] = round(total_elapsed, 1)


def _cleanup_run(run_id: str) -> None:
    """Remove a run from the store after the cleanup delay."""
    with _lock:
        _store.pop(run_id, None)

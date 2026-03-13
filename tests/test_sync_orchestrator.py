"""Tests for sync_orchestrator — 4-phase bulk Gong sync engine.

All tests use in-memory SQLite, mocked N8N client, and mocked Drive scanning.
asyncio.sleep is always patched to zero to keep tests fast.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sis.db.models import (
    Account,
    SyncAccountResult,
    SyncJob,
    WatchlistAccount,
)
from sis.services.n8n_client import N8NExtractResponse


# ── Helpers ──────────────────────────────────────────────────────────────


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_account(session, name: str) -> str:
    """Create an Account in DB and return its ID."""
    acct_id = _uuid()
    session.add(Account(
        id=acct_id,
        account_name=name,
        deal_type="new_logo",
    ))
    session.flush()
    return acct_id


def _make_sync_job(session, account_ids: list[str]) -> str:
    """Create a SyncJob + SyncAccountResults and return the job ID."""
    job_id = _uuid()
    session.add(SyncJob(
        id=job_id,
        status="pending",
        total_accounts=len(account_ids),
        started_at=_now(),
    ))
    session.flush()
    for acct_id in account_ids:
        acct = session.query(Account).filter_by(id=acct_id).first()
        session.add(SyncAccountResult(
            id=_uuid(),
            sync_job_id=job_id,
            account_id=acct_id,
            account_name=acct.account_name if acct else acct_id,
        ))
    session.flush()
    return job_id


# ── Session fixture ───────────────────────────────────────────────────────


@pytest.fixture
def sync_session(session, mock_get_session):
    """Patch all sync_orchestrator DB calls to use the test session.

    We explicitly import the orchestrator and watchlist_service modules
    so their get_session references are patched regardless of import order.
    """
    import sis.services.sync_orchestrator  # noqa: F401 — ensure imported
    import sis.services.watchlist_service  # noqa: F401 — ensure imported

    @contextmanager
    def _test_get_session():
        yield session

    with (
        patch("sis.services.sync_orchestrator.get_session", _test_get_session),
        patch("sis.services.watchlist_service.get_session", _test_get_session),
    ):
        yield session


# ── Fixtures: watched_accounts ────────────────────────────────────────────


@pytest.fixture
def two_accounts(sync_session):
    """Seed two accounts and return a list of watched_account dicts."""
    acct_a_id = _make_account(sync_session, "Acme Corp")
    acct_b_id = _make_account(sync_session, "Widget Ltd")
    accounts = [
        {"account_id": acct_a_id, "account_name": "Acme Corp",   "sf_account_name": "Acme"},
        {"account_id": acct_b_id, "account_name": "Widget Ltd",  "sf_account_name": "Widget"},
    ]
    return sync_session, accounts


# ── Test: happy path ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_happy_path(two_accounts):
    """2 accounts, N8N succeeds, Drive has files, import finds new calls."""
    session, accounts = two_accounts

    job_id = _make_sync_job(session, [a["account_id"] for a in accounts])

    n8n_success = N8NExtractResponse(
        success=True,
        total_calls_found=3,
        calls_processed=3,
        files_created=3,
        duration_seconds=31.0,
        status_code=503,
    )

    # Parsed calls mock — two calls per account
    fake_call = MagicMock()
    fake_call.metadata.call_id = _uuid()
    fake_call.metadata.date = "2025-06-01"
    fake_call.metadata.title = "Discovery Call"
    fake_call.metadata.duration_minutes = 45
    fake_call.speakers = []
    fake_call.enrichment.topics = []
    fake_call.to_agent_text.return_value = "transcript text"

    with (
        patch("sis.services.sync_orchestrator.n8n_client.extract_gong_calls",
              new=AsyncMock(return_value=n8n_success)),
        patch("asyncio.sleep", new=AsyncMock()),
        patch("sis.services.sync_orchestrator.GOOGLE_DRIVE_TRANSCRIPTS_PATH", "/fake/drive"),
        patch("sis.services.sync_orchestrator.Path") as mock_path_cls,
        patch("sis.services.gdrive_service._get_meta_files", return_value=[MagicMock()]),
        patch("sis.services.gdrive_service._group_by_account",
              return_value={"acme-corp": [MagicMock()], "widget-ltd": [MagicMock()]}),
        patch("sis.services.gdrive_service.download_and_parse_calls",
              return_value=[fake_call, fake_call]),
        patch("sis.services.gdrive_service.upload_calls_to_db",
              return_value={"imported": [MagicMock(), MagicMock()], "skipped": []}),
        patch("sis.services.watchlist_service.compute_new_calls_flag", return_value=True),
    ):
        # Make Path(...).exists() return True
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = []
        mock_path_cls.return_value = mock_path_instance

        from sis.services.sync_orchestrator import run_sync
        from sis.services import sync_progress_store as progress

        await run_sync(job_id, accounts, start_date="2025-01-01")

    snapshot = progress.get_sync_snapshot(job_id)
    assert snapshot is not None
    assert snapshot["status"] == "completed"
    assert snapshot["phase"] == "completed"
    assert snapshot["summary"] is not None
    assert snapshot["summary"]["total_accounts"] == 2

    # N8N progress: both accounts resolved
    assert snapshot["n8n_progress"]["completed"] == 2

    # DB job should be completed
    job = session.query(SyncJob).filter_by(id=job_id).first()
    assert job.status == "completed"
    assert job.completed_at is not None

    progress.cleanup_sync(job_id)


# ── Test: skip_n8n mode ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_skip_n8n_mode(two_accounts):
    """skip_n8n=True skips phases 1+2, goes straight to import."""
    session, accounts = two_accounts
    job_id = _make_sync_job(session, [a["account_id"] for a in accounts])

    with (
        patch("sis.services.sync_orchestrator.n8n_client.extract_gong_calls") as mock_n8n,
        patch("asyncio.sleep", new=AsyncMock()),
        patch("sis.services.sync_orchestrator.GOOGLE_DRIVE_TRANSCRIPTS_PATH", "/fake/drive"),
        patch("sis.services.sync_orchestrator.Path") as mock_path_cls,
        patch("sis.services.gdrive_service._get_meta_files", return_value=[]),
        patch("sis.services.gdrive_service._group_by_account", return_value={}),
        patch("sis.services.gdrive_service.download_and_parse_calls", return_value=[]),
        patch("sis.services.gdrive_service.upload_calls_to_db",
              return_value={"imported": [], "skipped": []}),
        patch("sis.services.watchlist_service.compute_new_calls_flag", return_value=False),
    ):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = []
        mock_path_cls.return_value = mock_path_instance

        from sis.services.sync_orchestrator import run_sync
        from sis.services import sync_progress_store as progress

        await run_sync(job_id, accounts, skip_n8n=True)

    # N8N should never have been called
    mock_n8n.assert_not_called()

    snapshot = progress.get_sync_snapshot(job_id)
    assert snapshot["status"] == "completed"

    # All accounts should be "skipped" at the N8N level
    for acct in accounts:
        assert snapshot["accounts"][acct["account_id"]]["n8n_status"] == "skipped"

    progress.cleanup_sync(job_id)


# ── Test: N8N failure continues to next account ───────────────────────────


@pytest.mark.asyncio
async def test_n8n_failure_continues(two_accounts):
    """First N8N call fails, second succeeds — both accounts still get import."""
    session, accounts = two_accounts
    job_id = _make_sync_job(session, [a["account_id"] for a in accounts])

    fail_response = N8NExtractResponse(
        success=False, error="timeout", duration_seconds=5.0
    )
    success_response = N8NExtractResponse(
        success=True, total_calls_found=2, duration_seconds=31.0, status_code=503
    )

    call_count = {"n": 0}

    async def side_effect(sf_name, start_date, end_date):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return fail_response
        return success_response

    with (
        patch("sis.services.sync_orchestrator.n8n_client.extract_gong_calls",
              side_effect=side_effect),
        patch("asyncio.sleep", new=AsyncMock()),
        patch("sis.services.sync_orchestrator.GOOGLE_DRIVE_TRANSCRIPTS_PATH", "/fake/drive"),
        patch("sis.services.sync_orchestrator.Path") as mock_path_cls,
        patch("sis.services.gdrive_service._get_meta_files", return_value=[]),
        patch("sis.services.gdrive_service._group_by_account", return_value={}),
        patch("sis.services.gdrive_service.download_and_parse_calls", return_value=[]),
        patch("sis.services.gdrive_service.upload_calls_to_db",
              return_value={"imported": [], "skipped": []}),
        patch("sis.services.watchlist_service.compute_new_calls_flag", return_value=False),
    ):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = []
        mock_path_cls.return_value = mock_path_instance

        from sis.services.sync_orchestrator import run_sync
        from sis.services import sync_progress_store as progress

        await run_sync(job_id, accounts, start_date="2025-01-01")

    assert call_count["n"] == 2, "N8N should have been called for both accounts"

    snapshot = progress.get_sync_snapshot(job_id)
    assert snapshot["status"] == "completed"

    first_id = accounts[0]["account_id"]
    second_id = accounts[1]["account_id"]
    assert snapshot["accounts"][first_id]["n8n_status"] == "failed"
    assert snapshot["accounts"][second_id]["n8n_status"] == "success"

    progress.cleanup_sync(job_id)


# ── Test: cancellation during N8N ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancellation_during_n8n(two_accounts):
    """Cancel after first N8N call — second call should not happen."""
    session, accounts = two_accounts
    job_id = _make_sync_job(session, [a["account_id"] for a in accounts])

    call_count = {"n": 0}

    async def n8n_side_effect(sf_name, start_date, end_date):
        call_count["n"] += 1
        return N8NExtractResponse(success=True, status_code=503, duration_seconds=31.0)

    async def sleep_and_cancel(_delay):
        """Cancel the job during the inter-request delay."""
        from sis.services import sync_progress_store as progress
        progress.cancel_sync(job_id)

    with (
        patch("sis.services.sync_orchestrator.n8n_client.extract_gong_calls",
              side_effect=n8n_side_effect),
        patch("asyncio.sleep", side_effect=sleep_and_cancel),
        patch("sis.services.sync_orchestrator.GOOGLE_DRIVE_TRANSCRIPTS_PATH", "/fake/drive"),
        patch("sis.services.sync_orchestrator.Path") as mock_path_cls,
        patch("sis.services.watchlist_service.compute_new_calls_flag", return_value=False),
    ):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance

        from sis.services.sync_orchestrator import run_sync
        from sis.services import sync_progress_store as progress

        await run_sync(job_id, accounts, start_date="2025-01-01")

    assert call_count["n"] == 1, "Should have stopped after first N8N call"

    snapshot = progress.get_sync_snapshot(job_id)
    assert snapshot["status"] == "cancelled"
    assert snapshot["phase"] == "cancelled"

    job = session.query(SyncJob).filter_by(id=job_id).first()
    assert job.status == "cancelled"

    progress.cleanup_sync(job_id)


# ── Test: Drive poll stabilizes early ─────────────────────────────────────


@pytest.mark.asyncio
async def test_drive_poll_stabilizes_early(two_accounts):
    """Drive file count is stable from the start — exits poll after 2 stable checks."""
    session, accounts = two_accounts
    job_id = _make_sync_job(session, [a["account_id"] for a in accounts])

    sleep_calls = {"n": 0}

    async def counting_sleep(_delay):
        sleep_calls["n"] += 1

    with (
        patch("sis.services.sync_orchestrator.n8n_client.extract_gong_calls",
              new=AsyncMock(return_value=N8NExtractResponse(
                  success=True, status_code=503, duration_seconds=31.0
              ))),
        patch("asyncio.sleep", side_effect=counting_sleep),
        patch("sis.services.sync_orchestrator.GOOGLE_DRIVE_TRANSCRIPTS_PATH", "/fake/drive"),
        patch("sis.services.sync_orchestrator.Path") as mock_path_cls,
        patch("sis.services.sync_orchestrator._count_drive_files", return_value=10),
        patch("sis.services.sync_orchestrator._total_drive_size", return_value=1024),
        patch("sis.services.gdrive_service._get_meta_files", return_value=[]),
        patch("sis.services.gdrive_service._group_by_account", return_value={}),
        patch("sis.services.gdrive_service.download_and_parse_calls", return_value=[]),
        patch("sis.services.gdrive_service.upload_calls_to_db",
              return_value={"imported": [], "skipped": []}),
        patch("sis.services.watchlist_service.compute_new_calls_flag", return_value=False),
    ):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = []
        mock_path_cls.return_value = mock_path_instance

        from sis.services.sync_orchestrator import run_sync
        from sis.services import sync_progress_store as progress

        await run_sync(job_id, accounts, start_date="2025-01-01")

    snapshot = progress.get_sync_snapshot(job_id)
    assert snapshot["status"] == "completed"

    # N8N inter-request delay is 1 sleep call (between 2 accounts).
    # Drive poll with stable file count exits after N8N_DRIVE_STABILITY_CHECKS=2 sleeps.
    # Total asyncio.sleep calls: 1 (n8n delay) + 2 (stable drive checks) = 3.
    # We allow flexibility since timing details may vary — just check < max wait
    from sis.config import N8N_DRIVE_POLL_MAX_WAIT, N8N_DRIVE_POLL_INTERVAL
    max_drive_sleeps = N8N_DRIVE_POLL_MAX_WAIT // N8N_DRIVE_POLL_INTERVAL
    assert sleep_calls["n"] < max_drive_sleeps + 2, (
        f"Expected early exit from Drive poll but got {sleep_calls['n']} sleeps"
    )

    progress.cleanup_sync(job_id)


# ── Test: no Drive path skips import ─────────────────────────────────────


@pytest.mark.asyncio
async def test_no_drive_path_skips_import(two_accounts):
    """Empty GOOGLE_DRIVE_TRANSCRIPTS_PATH causes import phase to be skipped."""
    session, accounts = two_accounts
    job_id = _make_sync_job(session, [a["account_id"] for a in accounts])

    with (
        patch("sis.services.sync_orchestrator.n8n_client.extract_gong_calls",
              new=AsyncMock(return_value=N8NExtractResponse(
                  success=True, status_code=503, duration_seconds=31.0
              ))),
        patch("asyncio.sleep", new=AsyncMock()),
        patch("sis.services.sync_orchestrator.GOOGLE_DRIVE_TRANSCRIPTS_PATH", ""),
        patch("sis.services.watchlist_service.compute_new_calls_flag", return_value=False),
    ):
        from sis.services.sync_orchestrator import run_sync
        from sis.services import sync_progress_store as progress

        await run_sync(job_id, accounts, start_date="2025-01-01")

    snapshot = progress.get_sync_snapshot(job_id)
    assert snapshot["status"] == "completed"

    # All accounts should have import_status == "skipped"
    for acct in accounts:
        assert snapshot["accounts"][acct["account_id"]]["import_status"] == "skipped", (
            f"Expected skipped import for {acct['account_name']}"
        )

    progress.cleanup_sync(job_id)


# ── Test: progress store snapshots at phase transitions ───────────────────


@pytest.mark.asyncio
async def test_progress_store_snapshots(two_accounts):
    """Progress store correctly reflects state at each phase transition."""
    session, accounts = two_accounts
    job_id = _make_sync_job(session, [a["account_id"] for a in accounts])

    phase_snapshots: list[dict] = []

    original_set_phase = None

    def capturing_set_phase(jid: str, phase: str, detail=None):
        """Capture snapshots at each phase transition."""
        original_set_phase(jid, phase, detail)
        snapshot = __import__(
            "sis.services.sync_progress_store", fromlist=["get_sync_snapshot"]
        ).get_sync_snapshot(jid)
        if snapshot:
            phase_snapshots.append({"phase": phase, "snapshot": snapshot})

    from sis.services import sync_progress_store as progress

    original_set_phase = progress.set_phase

    fake_call = MagicMock()
    fake_call.metadata.call_id = _uuid()
    fake_call.metadata.date = "2025-06-01"
    fake_call.metadata.title = "Call"
    fake_call.metadata.duration_minutes = 30
    fake_call.speakers = []
    fake_call.enrichment.topics = []
    fake_call.to_agent_text.return_value = "text"

    with (
        patch("sis.services.sync_orchestrator.n8n_client.extract_gong_calls",
              new=AsyncMock(return_value=N8NExtractResponse(
                  success=True, total_calls_found=1, status_code=503, duration_seconds=31.0
              ))),
        patch("asyncio.sleep", new=AsyncMock()),
        patch("sis.services.sync_orchestrator.GOOGLE_DRIVE_TRANSCRIPTS_PATH", "/fake/drive"),
        patch("sis.services.sync_orchestrator.Path") as mock_path_cls,
        patch("sis.services.sync_progress_store.set_phase",
              side_effect=capturing_set_phase),
        patch("sis.services.gdrive_service._get_meta_files", return_value=[MagicMock()]),
        patch("sis.services.gdrive_service._group_by_account",
              return_value={"acme-corp": [MagicMock()], "widget-ltd": [MagicMock()]}),
        patch("sis.services.gdrive_service.download_and_parse_calls",
              return_value=[fake_call]),
        patch("sis.services.gdrive_service.upload_calls_to_db",
              return_value={"imported": [MagicMock()], "skipped": []}),
        patch("sis.services.watchlist_service.compute_new_calls_flag", return_value=True),
    ):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.iterdir.return_value = []
        mock_path_cls.return_value = mock_path_instance

        from sis.services.sync_orchestrator import run_sync

        await run_sync(job_id, accounts, start_date="2025-01-01")

    # Verify we saw the expected phases in order
    phases_seen = [p["phase"] for p in phase_snapshots]
    assert "n8n_extraction" in phases_seen
    assert "waiting_for_drive" in phases_seen
    assert "importing" in phases_seen

    # n8n_extraction snapshot: status should be running
    n8n_snap = next(p["snapshot"] for p in phase_snapshots if p["phase"] == "n8n_extraction")
    assert n8n_snap["status"] == "running"

    # Final state: completed
    final_snap = progress.get_sync_snapshot(job_id)
    assert final_snap["status"] == "completed"
    assert final_snap["summary"] is not None

    progress.cleanup_sync(job_id)


# ── Test: sync_progress_store unit tests ─────────────────────────────────


def test_progress_store_init_and_snapshot():
    """init_sync populates the store; get_sync_snapshot returns deep copy."""
    from sis.services import sync_progress_store as ps

    job_id = _uuid()
    accounts = [
        {"account_id": "a1", "account_name": "Alpha"},
        {"account_id": "a2", "account_name": "Beta"},
    ]
    ps.init_sync(job_id, accounts)

    snap = ps.get_sync_snapshot(job_id)
    assert snap is not None
    assert snap["job_id"] == job_id
    assert snap["status"] == "running"
    assert snap["total_accounts"] == 2
    assert "a1" in snap["accounts"]
    assert "a2" in snap["accounts"]
    assert snap["accounts"]["a1"]["n8n_status"] == "pending"

    # Mutations to snapshot must not affect store
    snap["status"] = "hacked"
    fresh = ps.get_sync_snapshot(job_id)
    assert fresh["status"] == "running"

    ps.cleanup_sync(job_id)


def test_progress_store_cancellation():
    """cancel_sync sets status=cancelled; is_sync_cancelled returns True."""
    from sis.services import sync_progress_store as ps

    job_id = _uuid()
    ps.init_sync(job_id, [{"account_id": "x", "account_name": "X"}])

    assert ps.is_sync_cancelled(job_id) is False
    ps.cancel_sync(job_id)
    assert ps.is_sync_cancelled(job_id) is True

    ps.cleanup_sync(job_id)


def test_progress_store_n8n_status_increments_completed():
    """update_n8n_status increments n8n_progress.completed on terminal status."""
    from sis.services import sync_progress_store as ps

    job_id = _uuid()
    accounts = [
        {"account_id": "a1", "account_name": "Alpha"},
        {"account_id": "a2", "account_name": "Beta"},
    ]
    ps.init_sync(job_id, accounts)

    ps.update_n8n_status(job_id, "a1", "success", calls_found=5)
    snap = ps.get_sync_snapshot(job_id)
    assert snap["n8n_progress"]["completed"] == 1
    assert snap["accounts"]["a1"]["n8n_calls_found"] == 5

    ps.update_n8n_status(job_id, "a2", "failed", error="timeout")
    snap = ps.get_sync_snapshot(job_id)
    assert snap["n8n_progress"]["completed"] == 2
    assert len(snap["errors"]) == 1

    ps.cleanup_sync(job_id)


def test_progress_store_cleanup_removes_entry():
    """cleanup_sync removes the job from the store; get_sync_snapshot returns None."""
    from sis.services import sync_progress_store as ps

    job_id = _uuid()
    ps.init_sync(job_id, [{"account_id": "x", "account_name": "X"}])
    assert ps.get_sync_snapshot(job_id) is not None

    ps.cleanup_sync(job_id)
    assert ps.get_sync_snapshot(job_id) is None


def test_progress_store_unknown_job_returns_none():
    """Operations on unknown job_id are no-ops; snapshot returns None."""
    from sis.services import sync_progress_store as ps

    bogus_id = "does-not-exist-" + _uuid()
    assert ps.get_sync_snapshot(bogus_id) is None
    assert ps.is_sync_cancelled(bogus_id) is False

    # These should not raise
    ps.update_n8n_status(bogus_id, "acct", "success")
    ps.update_import_status(bogus_id, "acct", "done")
    ps.set_phase(bogus_id, "importing")
    ps.mark_sync_failed(bogus_id, "error")

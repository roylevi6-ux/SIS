"""Sync orchestrator — 4-phase async engine for bulk Gong sync.

Phases:
1. N8N Extraction: Call webhook for each watched account (sequential, 15s delay)
2. Drive Sync Wait: Poll local Drive folder for file count stability
3. Scan + Import: Parse and import new calls from Drive folder
4. Finalize: Compute has_new_calls flags, persist summary

Entry point: run_sync() — called as a background task from the sync API endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from sis.config import (
    N8N_INTER_REQUEST_DELAY,
    N8N_DRIVE_POLL_INTERVAL,
    N8N_DRIVE_POLL_MAX_WAIT,
    N8N_DRIVE_STABILITY_CHECKS,
    N8N_DEFAULT_START_DATE,
    GOOGLE_DRIVE_TRANSCRIPTS_PATH,
)
from sis.db.session import get_session
from sis.db.models import SyncJob, SyncAccountResult
from sis.services import n8n_client
from sis.services import sync_progress_store as progress
from sis.services import watchlist_service

logger = logging.getLogger(__name__)


# ── Public entry point ────────────────────────────────────────────────────


async def run_sync(
    job_id: str,
    watched_accounts: list[dict],
    start_date: str | None = None,
    skip_n8n: bool = False,
) -> None:
    """Execute the full sync flow as a background task.

    Args:
        job_id: Pre-created SyncJob ID (already persisted to DB).
        watched_accounts: List of dicts with keys:
            account_id, account_name, sf_account_name.
        start_date: Override start date for Gong extraction
            (default: N8N_DEFAULT_START_DATE from config).
        skip_n8n: If True, skip phases 1+2 and go straight to import.
            Useful for re-importing from an already-synced Drive folder.
    """
    start_date = start_date or N8N_DEFAULT_START_DATE
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sync_start = time.time()

    # Initialize progress store with all accounts in pending state
    progress.init_sync(job_id, watched_accounts)

    # Update DB job status to running
    _update_job_status(job_id, "running")

    try:
        # ── Phase 1: N8N Extraction ─────────────────────────────────────────
        if not skip_n8n:
            await _phase_n8n_extraction(job_id, watched_accounts, start_date, end_date)

            if progress.is_sync_cancelled(job_id):
                _finalize_cancelled(job_id)
                return

            # ── Phase 2: Drive Sync Wait ────────────────────────────────────
            await _phase_drive_sync_wait(job_id)

            if progress.is_sync_cancelled(job_id):
                _finalize_cancelled(job_id)
                return
        else:
            # Skip N8N — mark all accounts as skipped in progress store
            for acct in watched_accounts:
                progress.update_n8n_status(job_id, acct["account_id"], "skipped")

        # ── Phase 3: Scan + Import ──────────────────────────────────────────
        await _phase_scan_and_import(job_id, watched_accounts)

        if progress.is_sync_cancelled(job_id):
            _finalize_cancelled(job_id)
            return

        # ── Phase 4: Finalize ───────────────────────────────────────────────
        _phase_finalize(job_id, watched_accounts, sync_start)

    except Exception as e:
        logger.error("Sync orchestrator crashed for job %s: %s", job_id, e, exc_info=True)
        progress.mark_sync_failed(job_id, str(e))
        _update_job_status(job_id, "failed", error=str(e))


# ── Phase implementations ─────────────────────────────────────────────────


async def _phase_n8n_extraction(
    job_id: str,
    watched_accounts: list[dict],
    start_date: str,
    end_date: str,
) -> None:
    """Phase 1: Trigger Gong extraction via N8N webhook for each account.

    Sequential with N8N_INTER_REQUEST_DELAY between requests to avoid
    overwhelming the webhook gateway.
    """
    progress.set_phase(job_id, "n8n_extraction")
    n8n_start = time.time()

    for i, acct in enumerate(watched_accounts):
        if progress.is_sync_cancelled(job_id):
            break

        account_id = acct["account_id"]
        sf_name = acct["sf_account_name"]

        progress.update_n8n_current(job_id, acct["account_name"])
        logger.info(
            "N8N extraction %d/%d: %s (sf_name=%r)",
            i + 1, len(watched_accounts), acct["account_name"], sf_name,
        )

        try:
            result = await n8n_client.extract_gong_calls(sf_name, start_date, end_date)

            status = "success" if result.success else "failed"
            progress.update_n8n_status(
                job_id,
                account_id,
                status,
                calls_found=result.total_calls_found,
                error=result.error,
            )

            # Persist N8N result to DB
            _update_account_result(
                job_id,
                account_id,
                n8n_status=status,
                n8n_calls_found=result.total_calls_found,
                n8n_calls_processed=result.calls_processed,
                n8n_files_created=result.files_created,
                n8n_response=(
                    json.dumps(result.raw_response) if result.raw_response else None
                ),
                n8n_error=result.error,
                n8n_duration_seconds=result.duration_seconds,
            )

        except Exception as e:
            logger.warning("N8N call failed for %s: %s", sf_name, e)
            progress.update_n8n_status(job_id, account_id, "failed", error=str(e))
            _update_account_result(
                job_id, account_id,
                n8n_status="failed",
                n8n_error=str(e),
            )

        # Delay between requests (skip after last account or if cancelled)
        if (
            i < len(watched_accounts) - 1
            and not progress.is_sync_cancelled(job_id)
        ):
            await asyncio.sleep(N8N_INTER_REQUEST_DELAY)

    # Record N8N phase duration in DB
    n8n_duration = time.time() - n8n_start
    _update_job_field(job_id, "n8n_phase_seconds", n8n_duration)
    logger.info("N8N extraction phase complete in %.1fs", n8n_duration)


async def _phase_drive_sync_wait(job_id: str) -> None:
    """Phase 2: Poll Drive folder until file count stabilizes.

    Stability = same file count AND total size for N8N_DRIVE_STABILITY_CHECKS
    consecutive polls. Gives up after N8N_DRIVE_POLL_MAX_WAIT seconds and
    proceeds to import anyway.
    """
    progress.set_phase(job_id, "waiting_for_drive")

    drive_path = GOOGLE_DRIVE_TRANSCRIPTS_PATH
    if not drive_path or not Path(drive_path).exists():
        logger.warning(
            "Drive path not configured or does not exist: %r — skipping Drive poll",
            drive_path,
        )
        return

    prev_count = _count_drive_files(drive_path)
    prev_size = _total_drive_size(drive_path)
    stable_checks = 0
    elapsed = 0

    logger.info(
        "Drive poll starting: path=%r initial_files=%d max_wait=%ds",
        drive_path, prev_count, N8N_DRIVE_POLL_MAX_WAIT,
    )

    while elapsed < N8N_DRIVE_POLL_MAX_WAIT:
        if progress.is_sync_cancelled(job_id):
            break

        await asyncio.sleep(N8N_DRIVE_POLL_INTERVAL)
        elapsed += N8N_DRIVE_POLL_INTERVAL

        current_count = _count_drive_files(drive_path)
        current_size = _total_drive_size(drive_path)

        progress.update_drive_poll_status(
            job_id,
            elapsed,
            N8N_DRIVE_POLL_MAX_WAIT,
            current_count,
            stable_checks,
        )

        if current_count == prev_count and current_size == prev_size:
            stable_checks += 1
            logger.debug(
                "Drive stable check %d/%d: files=%d",
                stable_checks, N8N_DRIVE_STABILITY_CHECKS, current_count,
            )
            if stable_checks >= N8N_DRIVE_STABILITY_CHECKS:
                logger.info(
                    "Drive synced: %d files, stable after %ds",
                    current_count, elapsed,
                )
                break
        else:
            logger.debug(
                "Drive changed: files %d→%d, size %d→%d — resetting stable counter",
                prev_count, current_count, prev_size, current_size,
            )
            stable_checks = 0
            prev_count = current_count
            prev_size = current_size
    else:
        logger.warning(
            "Drive poll timed out after %ds — proceeding to import anyway",
            elapsed,
        )


async def _phase_scan_and_import(
    job_id: str,
    watched_accounts: list[dict],
) -> None:
    """Phase 3: Parse and import new calls from the Drive folder.

    Performs a single Drive scan then matches each watched account against
    the scanned files using case-insensitive slug matching.
    """
    progress.set_phase(job_id, "importing")

    drive_path = GOOGLE_DRIVE_TRANSCRIPTS_PATH
    if not drive_path or not Path(drive_path).exists():
        logger.warning(
            "Drive path not configured or does not exist: %r — skipping import",
            drive_path,
        )
        for acct in watched_accounts:
            progress.update_import_status(job_id, acct["account_id"], "skipped")
        return

    # Lazy imports to avoid circular dependencies
    from sis.services.gdrive_service import (
        download_and_parse_calls,
        upload_calls_to_db,
        _get_meta_files,
        _group_by_account,
    )

    # Single Drive scan: all meta files grouped by account slug
    all_meta_files = _get_meta_files(Path(drive_path))
    account_groups = _group_by_account(all_meta_files)

    # Build case-insensitive slug lookup: lowercase_slug → original_slug
    slug_lookup: dict[str, str] = {slug.lower(): slug for slug in account_groups}

    logger.info(
        "Drive scan found %d account slug(s) across %d meta files",
        len(account_groups),
        len(all_meta_files),
    )

    for acct in watched_accounts:
        if progress.is_sync_cancelled(job_id):
            break

        account_id = acct["account_id"]
        account_name = acct["account_name"]

        # Attempt multiple name normalizations to find a Drive match
        name_lower = account_name.lower().replace(" ", "-")
        sf_lower = acct.get("sf_account_name", "").lower().replace(" ", "-")

        matching_slug = slug_lookup.get(name_lower) or slug_lookup.get(sf_lower)

        # Fallback: try underscore-separated variants
        if not matching_slug:
            name_under = account_name.lower().replace(" ", "_")
            sf_under = acct.get("sf_account_name", "").lower().replace(" ", "_")
            matching_slug = slug_lookup.get(name_under) or slug_lookup.get(sf_under)

        # Last resort: partial slug match
        if not matching_slug:
            for slug_key in slug_lookup:
                if name_lower in slug_key or slug_key in name_lower:
                    matching_slug = slug_lookup[slug_key]
                    break

        if not matching_slug:
            logger.info(
                "No Drive files found for account %r — marking as skipped",
                account_name,
            )
            progress.update_import_status(job_id, account_id, "skipped")
            _update_account_result(job_id, account_id, import_status="skipped")
            continue

        try:
            logger.info(
                "Importing calls for account %r (Drive slug=%r)",
                account_name, matching_slug,
            )

            # Parse calls for this account from Drive (no artificial limit for sync)
            parsed_calls = download_and_parse_calls(
                drive_path, max_calls=50, account_name=matching_slug
            )

            if not parsed_calls:
                progress.update_import_status(
                    job_id, account_id, "done", imported=0, skipped=0
                )
                _update_account_result(job_id, account_id, import_status="done")
                continue

            # Upload with built-in dedup
            result = upload_calls_to_db(parsed_calls, account_id)
            imported = len(result.get("imported", []))
            skipped = len(result.get("skipped", []))

            progress.update_import_status(
                job_id, account_id, "done",
                imported=imported,
                skipped=skipped,
            )
            _update_account_result(
                job_id,
                account_id,
                import_status="done",
                new_files_found=len(parsed_calls),
                calls_imported=imported,
                calls_skipped=skipped,
                has_new_data=1 if imported > 0 else 0,
            )

            logger.info(
                "Import done for %r: imported=%d skipped=%d",
                account_name, imported, skipped,
            )

        except Exception as e:
            logger.warning(
                "Import failed for %r: %s",
                account_name, e, exc_info=True,
            )
            progress.update_import_status(job_id, account_id, "failed")
            _update_account_result(
                job_id, account_id,
                import_status="failed",
                import_error=str(e),
            )


def _phase_finalize(
    job_id: str,
    watched_accounts: list[dict],
    sync_start: float,
) -> None:
    """Phase 4: Compute has_new_calls flags and persist final summary."""
    logger.info("Finalizing sync job %s — computing has_new_calls flags", job_id)

    # Compute has_new_calls for every watched account
    for acct in watched_accounts:
        try:
            watchlist_service.compute_new_calls_flag(acct["account_id"])
        except Exception as e:
            logger.warning(
                "Failed to compute new_calls_flag for %s: %s",
                acct["account_name"], e,
            )

    total_seconds = time.time() - sync_start

    # Aggregate final stats from DB
    with get_session() as session:
        results = (
            session.query(SyncAccountResult)
            .filter_by(sync_job_id=job_id)
            .all()
        )
        total_imported = sum(r.calls_imported or 0 for r in results)
        total_skipped = sum(r.calls_skipped or 0 for r in results)
        n8n_succeeded = sum(1 for r in results if r.n8n_status == "success")
        n8n_failed = sum(1 for r in results if r.n8n_status == "failed")
        accounts_with_new = sum(1 for r in results if r.has_new_data)

        job = session.query(SyncJob).filter_by(id=job_id).first()
        if job:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.calls_imported = total_imported
            job.calls_skipped = total_skipped
            job.n8n_calls_succeeded = n8n_succeeded
            job.n8n_calls_failed = n8n_failed
            job.total_seconds = total_seconds

    summary = {
        "total_accounts": len(watched_accounts),
        "calls_imported": total_imported,
        "calls_skipped": total_skipped,
        "n8n_succeeded": n8n_succeeded,
        "n8n_failed": n8n_failed,
        "accounts_with_new_data": accounts_with_new,
        "total_seconds": round(total_seconds, 1),
    }

    progress.mark_sync_completed(job_id, summary)
    logger.info("Sync job %s completed: %s", job_id, summary)


# ── Drive filesystem helpers ──────────────────────────────────────────────


def _count_drive_files(drive_path: str) -> int:
    """Count non-hidden files in the Drive folder (not recursive)."""
    p = Path(drive_path)
    if not p.exists():
        return 0
    return sum(1 for f in p.iterdir() if f.is_file() and not f.name.startswith("."))


def _total_drive_size(drive_path: str) -> int:
    """Total size in bytes of all non-hidden files in the Drive folder."""
    p = Path(drive_path)
    if not p.exists():
        return 0
    return sum(
        f.stat().st_size
        for f in p.iterdir()
        if f.is_file() and not f.name.startswith(".")
    )


# ── DB update helpers ─────────────────────────────────────────────────────


def _update_job_status(
    job_id: str,
    status: str,
    error: str | None = None,
) -> None:
    """Update SyncJob.status in DB. Sets completed_at for terminal statuses."""
    with get_session() as session:
        job = session.query(SyncJob).filter_by(id=job_id).first()
        if job:
            job.status = status
            if error:
                job.error_log = json.dumps([error])
            if status in ("completed", "failed", "cancelled"):
                job.completed_at = datetime.now(timezone.utc).isoformat()


def _update_job_field(job_id: str, field: str, value: object) -> None:
    """Set a single field on SyncJob by name."""
    with get_session() as session:
        job = session.query(SyncJob).filter_by(id=job_id).first()
        if job:
            setattr(job, field, value)


def _update_account_result(job_id: str, account_id: str, **fields: object) -> None:
    """Update fields on SyncAccountResult for a given account in a job."""
    with get_session() as session:
        result = (
            session.query(SyncAccountResult)
            .filter_by(sync_job_id=job_id, account_id=account_id)
            .first()
        )
        if result:
            for k, v in fields.items():
                setattr(result, k, v)


def _finalize_cancelled(job_id: str) -> None:
    """Persist cancelled status and update progress store."""
    _update_job_status(job_id, "cancelled")
    progress.cancel_sync(job_id)
    logger.info("Sync job %s cancelled", job_id)

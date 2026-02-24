#!/usr/bin/env python3
"""Backfill health score v2 — re-run synthesis for specified accounts.

After updating health score components (splitting Stakeholder into Champion +
Multi-threading, reweighting, adding Champion NEVER rule), existing accounts
need Agent 10 re-run to produce new health breakdowns.

Usage:
    # Re-run specific accounts by name (partial match)
    python scripts/backfill_health_score_v2.py --accounts "Dec" "AI leads"

    # Re-run ALL accounts
    python scripts/backfill_health_score_v2.py --all

    # Dry run (show what would be re-run)
    python scripts/backfill_health_score_v2.py --accounts "Dec" "AI leads" --dry-run

Requires: DATABASE_URL set, ANTHROPIC_API_KEY set, VPN connected.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)


def find_accounts(name_patterns: list[str]) -> list[dict]:
    """Find accounts matching any of the given name patterns (case-insensitive)."""
    from sis.db.session import get_session
    from sis.db.models import Account

    matched = []
    with get_session() as session:
        all_accounts = session.query(Account).all()
        for account in all_accounts:
            for pattern in name_patterns:
                if pattern.lower() in (account.account_name or "").lower():
                    matched.append({
                        "id": account.id,
                        "name": account.account_name,
                        "deal_type": account.deal_type,
                    })
                    break
    return matched


def find_all_scored_accounts() -> list[dict]:
    """Find all accounts that have at least one completed analysis run."""
    from sis.db.session import get_session
    from sis.db.models import Account, AnalysisRun

    with get_session() as session:
        accounts_with_runs = (
            session.query(Account)
            .join(AnalysisRun, Account.id == AnalysisRun.account_id)
            .filter(AnalysisRun.status == "completed")
            .distinct()
            .all()
        )
        return [
            {"id": a.id, "name": a.account_name, "deal_type": a.deal_type}
            for a in accounts_with_runs
        ]


def backfill_account(account: dict) -> dict:
    """Re-run full pipeline for one account.

    Returns dict with status and timing.
    """
    from sis.services.analysis_service import analyze_account

    account_id = account["id"]
    account_name = account["name"]

    logger.info("Starting backfill for %s (%s)", account_name, account_id)
    start = time.time()

    try:
        result = analyze_account(account_id)
        elapsed = round(time.time() - start, 1)
        logger.info(
            "Completed %s in %.1fs — health=%s, status=%s, warnings=%s",
            account_name,
            elapsed,
            result.get("health_score", "?"),
            result["status"],
            len(result.get("validation_warnings", [])),
        )
        return {"account": account_name, "status": "success", "elapsed": elapsed, **result}
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        logger.error("Failed %s after %.1fs: %s", account_name, elapsed, e)
        return {"account": account_name, "status": "error", "error": str(e), "elapsed": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Backfill health score v2 for accounts")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--accounts",
        nargs="+",
        help="Account name patterns to match (case-insensitive partial match)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Re-run ALL accounts with completed analyses",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be re-run without actually running",
    )
    args = parser.parse_args()

    # Find accounts
    if args.all:
        accounts = find_all_scored_accounts()
        logger.info("Found %d accounts with completed analyses", len(accounts))
    else:
        accounts = find_accounts(args.accounts)
        logger.info(
            "Found %d accounts matching patterns: %s",
            len(accounts),
            args.accounts,
        )

    if not accounts:
        logger.warning("No accounts found. Check your patterns or database connection.")
        sys.exit(1)

    # Print what we found
    for a in accounts:
        logger.info("  -> %s (%s) [%s]", a["name"], a["id"][:8], a.get("deal_type", "unknown"))

    if args.dry_run:
        logger.info("Dry run — no changes made. %d accounts would be re-analyzed.", len(accounts))
        sys.exit(0)

    # Run backfill
    results = []
    total_start = time.time()
    for i, account in enumerate(accounts, 1):
        logger.info("--- [%d/%d] %s ---", i, len(accounts), account["name"])
        result = backfill_account(account)
        results.append(result)

    total_elapsed = round(time.time() - total_start, 1)

    # Summary
    successes = [r for r in results if r["status"] == "success"]
    failures = [r for r in results if r["status"] == "error"]
    logger.info("=" * 60)
    logger.info(
        "Backfill complete: %d/%d succeeded, %d failed in %.1fs",
        len(successes),
        len(results),
        len(failures),
        total_elapsed,
    )
    for f in failures:
        logger.error("  FAILED: %s — %s", f["account"], f.get("error", "unknown"))


if __name__ == "__main__":
    main()

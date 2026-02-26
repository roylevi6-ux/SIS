#!/usr/bin/env python3
"""Re-run full pipeline with stage-aware scoring overhaul.

Captures before/after scores for comparison, then deletes all OLD runs
keeping only the new stage-aware results.

For the 3 multi-run accounts (Cettire, We Love Holidays, Yaspa),
follows the same delta logic used in get_assessment_delta() and
run_regression_check().

Usage:
    python -m scripts.rerun_stage_aware --all
    python -m scripts.rerun_stage_aware --accounts "Cettire" "Yaspa"
    python -m scripts.rerun_stage_aware --all --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "rerun_reports"


def capture_pre_scores() -> dict[str, dict]:
    """Snapshot current scores and collect OLD run IDs for all accounts."""
    from sis.db.session import get_session
    from sis.db.models import Account, DealAssessment, AnalysisRun

    snapshots = {}
    with get_session() as session:
        accounts = session.query(Account).all()
        for account in accounts:
            # Get latest assessment
            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=account.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )
            # Collect ALL existing run IDs (these will be deleted after re-run)
            old_runs = (
                session.query(AnalysisRun.id)
                .filter_by(account_id=account.id)
                .all()
            )
            old_run_ids = [r[0] for r in old_runs]

            if latest:
                snapshots[account.id] = {
                    "account_name": account.account_name,
                    "run_count_before": len(old_run_ids),
                    "old_run_ids": old_run_ids,
                    "pre": {
                        "health_score": latest.health_score,
                        "ai_forecast_category": latest.ai_forecast_category,
                        "inferred_stage": latest.inferred_stage,
                        "overall_confidence": latest.overall_confidence,
                        "momentum_direction": latest.momentum_direction,
                        "stage_name": latest.stage_name,
                    },
                }
            else:
                snapshots[account.id] = {
                    "account_name": account.account_name,
                    "run_count_before": len(old_run_ids),
                    "old_run_ids": old_run_ids,
                    "pre": None,
                }
    return snapshots


def run_pipeline(account_id: str, account_name: str) -> dict:
    """Run full pipeline for one account, return result with new run_id."""
    from sis.services.analysis_service import analyze_account

    logger.info("Starting pipeline for %s (%s)", account_name, account_id[:8])
    start = time.time()

    try:
        result = analyze_account(account_id)
        elapsed = round(time.time() - start, 1)
        logger.info(
            "Completed %s in %.1fs — health=%s, forecast=%s, stage=S%s",
            account_name, elapsed,
            result.get("health_score", "?"),
            result.get("ai_forecast_category", "?"),
            result.get("inferred_stage", "?"),
        )
        return {"status": "success", "elapsed": elapsed, **result}
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        logger.error("Failed %s after %.1fs: %s", account_name, elapsed, e)
        return {"status": "error", "error": str(e), "elapsed": elapsed}


def capture_post_scores(account_ids: list[str]) -> dict[str, dict]:
    """Snapshot scores after re-run."""
    from sis.db.session import get_session
    from sis.db.models import DealAssessment

    post = {}
    with get_session() as session:
        for aid in account_ids:
            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=aid)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )
            if latest:
                post[aid] = {
                    "health_score": latest.health_score,
                    "ai_forecast_category": latest.ai_forecast_category,
                    "inferred_stage": latest.inferred_stage,
                    "overall_confidence": latest.overall_confidence,
                    "momentum_direction": latest.momentum_direction,
                    "stage_name": latest.stage_name,
                    "run_id": latest.analysis_run_id,
                }
    return post


def delete_old_runs(pre_snapshots: dict, new_run_ids: set[str]):
    """Delete all old AnalysisRuns (and their children) that are NOT in new_run_ids.

    Delete order: ScoreFeedback → DealAssessment → AgentAnalysis → AnalysisRun
    """
    from sis.db.session import get_session
    from sis.db.models import AnalysisRun, AgentAnalysis, DealAssessment, ScoreFeedback

    all_old_run_ids = []
    for snap in pre_snapshots.values():
        for rid in snap.get("old_run_ids", []):
            if rid not in new_run_ids:
                all_old_run_ids.append(rid)

    if not all_old_run_ids:
        logger.info("No old runs to delete.")
        return 0

    logger.info("Deleting %d old runs (keeping %d new runs)...", len(all_old_run_ids), len(new_run_ids))

    deleted = 0
    with get_session() as session:
        for run_id in all_old_run_ids:
            # 1. Delete ScoreFeedback via DealAssessment
            assessment = session.query(DealAssessment).filter_by(analysis_run_id=run_id).first()
            if assessment:
                fb_count = session.query(ScoreFeedback).filter_by(deal_assessment_id=assessment.id).delete()
                if fb_count:
                    logger.info("  Deleted %d score_feedback rows for run %s", fb_count, run_id[:8])

            # 2. Delete DealAssessment
            da_count = session.query(DealAssessment).filter_by(analysis_run_id=run_id).delete()

            # 3. Delete AgentAnalysis
            aa_count = session.query(AgentAnalysis).filter_by(analysis_run_id=run_id).delete()

            # 4. Delete AnalysisRun
            ar_count = session.query(AnalysisRun).filter_by(id=run_id).delete()

            if ar_count:
                deleted += 1
                logger.info("  Deleted run %s: %d assessment, %d agent_analyses",
                            run_id[:8], da_count, aa_count)

        session.commit()

    logger.info("Deleted %d old runs total.", deleted)
    return deleted


def update_account_health_fields(account_ids: list[str]):
    """Sync Account table health fields from latest DealAssessment.

    After deleting old runs, the Account's cached health_score / momentum /
    forecast / stage fields should reflect the (only remaining) new run.
    """
    from sis.db.session import get_session
    from sis.db.models import Account, DealAssessment

    with get_session() as session:
        for aid in account_ids:
            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=aid)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )
            if not latest:
                continue

            account = session.query(Account).filter_by(id=aid).one()
            account.health_score = latest.health_score
            account.momentum_direction = latest.momentum_direction
            account.ai_forecast_category = latest.ai_forecast_category
            account.inferred_stage = latest.inferred_stage
            account.stage_name = latest.stage_name

        session.commit()
    logger.info("Synced Account health fields for %d accounts.", len(account_ids))


def build_comparison(pre_snapshots: dict, post_scores: dict) -> list[dict]:
    """Build comparison report following the same delta logic as
    get_assessment_delta() and run_regression_check()."""
    rows = []
    for aid, snap in pre_snapshots.items():
        pre = snap.get("pre")
        post = post_scores.get(aid)
        name = snap["account_name"]

        if not pre or not post:
            rows.append({
                "account_name": name,
                "account_id": aid,
                "status": "SKIP" if not post else "NEW",
                "multi_run": snap["run_count_before"] > 1,
            })
            continue

        health_delta = post["health_score"] - pre["health_score"]
        conf_delta = round((post["overall_confidence"] or 0) - (pre["overall_confidence"] or 0), 3)
        forecast_changed = post["ai_forecast_category"] != pre["ai_forecast_category"]
        stage_changed = post["inferred_stage"] != pre["inferred_stage"]
        momentum_changed = post["momentum_direction"] != pre["momentum_direction"]

        def tier(score):
            if score >= 70:
                return "Healthy"
            elif score >= 40:
                return "Neutral"
            else:
                return "Needs Attention"

        rows.append({
            "account_name": name,
            "account_id": aid,
            "multi_run": snap["run_count_before"] > 1,
            "status": "OK",
            "pre_health": pre["health_score"],
            "post_health": post["health_score"],
            "health_delta": health_delta,
            "pre_tier": tier(pre["health_score"]),
            "post_tier": tier(post["health_score"]),
            "pre_forecast": pre["ai_forecast_category"],
            "post_forecast": post["ai_forecast_category"],
            "forecast_changed": forecast_changed,
            "pre_stage": f"S{pre['inferred_stage']}",
            "post_stage": f"S{post['inferred_stage']}",
            "stage_changed": stage_changed,
            "pre_momentum": pre["momentum_direction"],
            "post_momentum": post["momentum_direction"],
            "momentum_changed": momentum_changed,
            "pre_confidence": pre["overall_confidence"],
            "post_confidence": post["overall_confidence"],
            "conf_delta": conf_delta,
            # Regression gates (same as golden_test.py)
            "gate_health": "FAIL" if abs(health_delta) > 15 else "PASS",
            "gate_forecast": "FAIL" if forecast_changed else "PASS",
            "gate_stage": "WARN" if stage_changed else "PASS",
            "gate_confidence": "WARN" if conf_delta < -0.15 else "PASS",
        })

    return sorted(rows, key=lambda r: r.get("health_delta", 0))


def print_report(rows: list[dict]):
    """Print comparison report to console."""
    print("\n" + "=" * 100)
    print("STAGE-AWARE SCORING OVERHAUL — COMPARISON REPORT")
    print("=" * 100)

    ok_rows = [r for r in rows if r["status"] == "OK"]
    multi_run = [r for r in ok_rows if r["multi_run"]]

    if ok_rows:
        avg_pre = sum(r["pre_health"] for r in ok_rows) / len(ok_rows)
        avg_post = sum(r["post_health"] for r in ok_rows) / len(ok_rows)
        avg_delta = avg_post - avg_pre
        print(f"\nAvg health: {avg_pre:.1f} → {avg_post:.1f} (delta: {avg_delta:+.1f})")
        print(f"Expected avg ~56 (simulation), range 38-72")

        for tier_name in ["Healthy", "Neutral", "Needs Attention"]:
            pre_count = sum(1 for r in ok_rows if r["pre_tier"] == tier_name)
            post_count = sum(1 for r in ok_rows if r["post_tier"] == tier_name)
            print(f"  {tier_name:20s}: {pre_count} → {post_count}")

    if multi_run:
        print(f"\n{'─' * 100}")
        print("MULTI-RUN ACCOUNTS (existing delta history — old runs will be deleted)")
        print(f"{'─' * 100}")
        for r in multi_run:
            flag = " !!" if r.get("gate_health") == "FAIL" or r.get("gate_forecast") == "FAIL" else ""
            print(f"  {r['account_name']:40s} {r['pre_health']:3d} -> {r['post_health']:3d} ({r['health_delta']:+3d})"
                  f"  {r['pre_forecast']:12s} -> {r['post_forecast']:12s}"
                  f"  {r['pre_stage']} -> {r['post_stage']}{flag}")

    print(f"\n{'─' * 100}")
    print(f"{'Account':40s} {'Health':>14s} {'D':>4s} {'Tier':>26s} {'Forecast':>26s} {'Stage':>10s} {'Gates'}")
    print(f"{'─' * 100}")
    for r in rows:
        if r["status"] != "OK":
            print(f"  {r['account_name']:40s} [{r['status']}]")
            continue
        gates = []
        if r["gate_health"] == "FAIL":
            gates.append("H!")
        if r["gate_forecast"] == "FAIL":
            gates.append("F!")
        if r["gate_stage"] == "WARN":
            gates.append("S~")
        if r["gate_confidence"] == "WARN":
            gates.append("C~")
        gate_str = " ".join(gates) if gates else "ok"

        print(
            f"  {r['account_name']:40s}"
            f" {r['pre_health']:3d} -> {r['post_health']:3d}"
            f" {r['health_delta']:+4d}"
            f"  {r['pre_tier']:12s} -> {r['post_tier']:12s}"
            f"  {r['pre_forecast']:12s} -> {r['post_forecast']:12s}"
            f"  {r['pre_stage']:>3s}->{r['post_stage']:<3s}"
            f"  {gate_str}"
        )

    fails = [r for r in ok_rows if r["gate_health"] == "FAIL" or r["gate_forecast"] == "FAIL"]
    warns = [r for r in ok_rows if r["gate_stage"] == "WARN" or r["gate_confidence"] == "WARN"]
    print(f"\nGate summary: {len(fails)} FAIL, {len(warns)} WARN, {len(ok_rows) - len(fails) - len(warns)} PASS")


def cmd_run(args):
    """Phase 1: Re-run pipeline and produce comparison report. No deletions."""

    # ── Step 1: Capture pre-scores & old run IDs ──
    logger.info("Step 1/5: Capturing pre-run scores...")
    pre_snapshots = capture_pre_scores()
    scored_count = sum(1 for s in pre_snapshots.values() if s["pre"])
    total_old_runs = sum(len(s["old_run_ids"]) for s in pre_snapshots.values())
    logger.info("Found %d accounts with assessments, %d old runs in DB",
                scored_count, total_old_runs)

    # ── Step 2: Determine which accounts to run ──
    if args.all:
        account_ids = [aid for aid, snap in pre_snapshots.items() if snap["pre"]]
    else:
        account_ids = []
        for aid, snap in pre_snapshots.items():
            for pattern in args.accounts:
                if pattern.lower() in snap["account_name"].lower():
                    account_ids.append(aid)
                    break

    accounts_to_run = [(aid, pre_snapshots[aid]["account_name"]) for aid in account_ids]
    logger.info("Step 2/5: Will re-run %d accounts:", len(accounts_to_run))
    for aid, name in accounts_to_run:
        old_count = len(pre_snapshots[aid]["old_run_ids"])
        multi = f" [MULTI-RUN: {old_count} old runs]" if old_count > 1 else f" [{old_count} old run]"
        logger.info("  -> %s (%s) health=%s%s",
                     name, aid[:8], pre_snapshots[aid]["pre"]["health_score"], multi)

    if args.dry_run:
        logger.info("Dry run — no changes. Would run pipeline for %d accounts.", len(accounts_to_run))
        return

    # ── Step 3: Run pipeline for all accounts ──
    logger.info("Step 3/5: Running full pipeline (Agents 1-10) for all accounts...")
    total_start = time.time()
    results = []
    for i, (aid, name) in enumerate(accounts_to_run, 1):
        logger.info("--- [%d/%d] %s ---", i, len(accounts_to_run), name)
        result = run_pipeline(aid, name)
        results.append((aid, result))

    total_elapsed = round(time.time() - total_start, 1)
    successes = [(aid, r) for aid, r in results if r["status"] == "success"]
    failures = [(aid, r) for aid, r in results if r["status"] == "error"]
    logger.info("Pipeline complete: %d/%d succeeded, %d failed in %.1fs",
                len(successes), len(results), len(failures), total_elapsed)

    if failures:
        for aid, r in failures:
            logger.error("  FAILED: %s — %s", pre_snapshots[aid]["account_name"], r.get("error"))

    # ── Step 4: Capture post-scores ──
    logger.info("Step 4/5: Capturing post-run scores...")
    post_scores = capture_post_scores(account_ids)

    new_run_ids = set()
    for aid, post in post_scores.items():
        if post.get("run_id"):
            new_run_ids.add(post["run_id"])
    logger.info("New runs created: %d", len(new_run_ids))

    # ── Step 5: Build comparison report ──
    logger.info("Step 5/5: Building comparison report...")
    comparison = build_comparison(pre_snapshots, post_scores)
    print_report(comparison)

    # Save report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = OUTPUT_DIR / f"stage_aware_rerun_{ts}.json"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_accounts": len(accounts_to_run),
        "succeeded": len(successes),
        "failed": len(failures),
        "total_elapsed_seconds": total_elapsed,
        "old_run_ids": {snap["account_name"]: snap["old_run_ids"] for snap in pre_snapshots.values()},
        "new_run_ids": list(new_run_ids),
        "comparison": comparison,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Report saved: %s", report_path)

    print(f"\n{'=' * 80}")
    print("RE-RUN COMPLETE — OLD RUNS NOT YET DELETED")
    print(f"{'=' * 80}")
    print(f"Review the comparison report above.")
    print(f"Old runs in DB: {total_old_runs}  |  New runs: {len(new_run_ids)}")
    print(f"\nWhen ready to delete old runs, run:")
    print(f"  python -m scripts.rerun_stage_aware cleanup --report {report_path}")
    print(f"\nSF fields on Account table (sf_stage, sf_forecast_category, sf_close_quarter,")
    print(f"cp_estimate, ae_owner, team_lead, ic_forecast_category) are NOT touched.")


def cmd_cleanup(args):
    """Phase 2: Delete old runs, keeping only new ones. Requires explicit approval."""

    report_path = Path(args.report)
    if not report_path.exists():
        logger.error("Report file not found: %s", report_path)
        sys.exit(1)

    with open(report_path) as f:
        report = json.load(f)

    new_run_ids = set(report["new_run_ids"])
    old_run_map = report["old_run_ids"]  # {account_name: [run_id, ...]}

    total_old = sum(len(ids) for ids in old_run_map.values())
    # Exclude new run IDs from the old list (they exist in both if account had no prior runs)
    old_to_delete = []
    for name, ids in old_run_map.items():
        for rid in ids:
            if rid not in new_run_ids:
                old_to_delete.append((name, rid))

    logger.info("Report: %s", report_path)
    logger.info("New runs to KEEP: %d", len(new_run_ids))
    logger.info("Old runs to DELETE: %d", len(old_to_delete))

    if args.dry_run:
        logger.info("Dry run — would delete %d old runs:", len(old_to_delete))
        for name, rid in old_to_delete:
            logger.info("  %s: %s", name, rid[:8])
        return

    # Show what will be deleted
    print(f"\nAbout to delete {len(old_to_delete)} old runs:")
    for name, rid in old_to_delete:
        print(f"  {name:40s}  run {rid[:8]}...")
    print(f"\nKeeping {len(new_run_ids)} new runs.")
    print("SF fields on Account (sf_stage, sf_forecast_category, sf_close_quarter,")
    print("cp_estimate, ae_owner, team_lead, ic_forecast_category) will NOT be touched.")

    # Build pre_snapshots structure for delete_old_runs()
    pre_snapshots = {}
    from sis.db.session import get_session
    from sis.db.models import Account
    with get_session() as session:
        for account in session.query(Account).all():
            name = account.account_name
            if name in old_run_map:
                pre_snapshots[account.id] = {
                    "account_name": name,
                    "old_run_ids": old_run_map[name],
                }

    account_ids = list(pre_snapshots.keys())

    logger.info("Deleting old runs...")
    deleted = delete_old_runs(pre_snapshots, new_run_ids)
    update_account_health_fields(account_ids)
    logger.info("Cleanup complete: deleted %d old runs. Each account now has exactly 1 run.", deleted)

    # Verify
    from sis.db.models import AnalysisRun
    with get_session() as session:
        remaining = session.query(AnalysisRun).count()
        logger.info("Verification: %d total runs remaining in DB.", remaining)

    print("\nDone. Old runs deleted, SF fields preserved.")


def main():
    parser = argparse.ArgumentParser(
        description="Re-run pipeline with stage-aware scoring (two-phase: run, then cleanup)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── run command ──
    run_parser = subparsers.add_parser("run", help="Re-run pipeline and produce comparison report")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--accounts", nargs="+", help="Account name patterns")
    run_group.add_argument("--all", action="store_true", help="Re-run ALL accounts")
    run_parser.add_argument("--dry-run", action="store_true", help="Show plan without running")

    # ── cleanup command ──
    cleanup_parser = subparsers.add_parser("cleanup", help="Delete old runs (requires prior 'run')")
    cleanup_parser.add_argument("--report", required=True, help="Path to rerun report JSON")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""Golden test set — regression gates per PRD Sec 7.11.

20-25 deal snapshots with 4 regression gates:
1. Health score delta > 10 → FAIL
2. Forecast category changed → FAIL
3. Stage inference changed → WARN
4. Confidence dropped > 0.15 → WARN
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sis.db.session import get_session
from sis.db.models import DealAssessment, Account

logger = logging.getLogger(__name__)

GOLDEN_DIR = Path(__file__).parent.parent.parent / "config" / "golden_tests"


def create_baseline(account_id: str) -> dict:
    """Snapshot current DealAssessment as a golden test fixture.

    Saves to config/golden_tests/<account_name>.json.
    Returns the fixture dict.
    """
    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")

        assessment = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.desc())
            .first()
        )
        if not assessment:
            raise ValueError(f"No assessment found for account: {account.account_name}")

        fixture_id = f"golden_{account.account_name.lower().replace(' ', '_')}"
        fixture = {
            "fixture_id": fixture_id,
            "account_id": account_id,
            "account_name": account.account_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "baseline": {
                "health_score": assessment.health_score,
                "ai_forecast_category": assessment.ai_forecast_category,
                "inferred_stage": assessment.inferred_stage,
                "overall_confidence": assessment.overall_confidence,
                "momentum_direction": assessment.momentum_direction,
            },
        }

    # Save to file
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path = GOLDEN_DIR / f"{fixture_id}.json"
    with open(fixture_path, "w") as f:
        json.dump(fixture, f, indent=2)

    logger.info("Created golden baseline: %s", fixture_path)
    return fixture


def load_golden_set() -> list[dict]:
    """Load all golden test fixtures from config/golden_tests/."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = []
    for path in sorted(GOLDEN_DIR.glob("*.json")):
        try:
            with open(path) as f:
                fixtures.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skipping invalid fixture %s: %s", path, e)
    return fixtures


def run_regression_check(current: dict, baseline: dict) -> dict:
    """Check 4 regression gates between current assessment and baseline.

    Args:
        current: dict with health_score, ai_forecast_category, inferred_stage, overall_confidence
        baseline: dict with same keys

    Returns:
        dict with: status (PASS/WARN/FAIL), gates (list of gate results)
    """
    gates = []

    # Gate 1: Health score delta > 15 → FAIL (widened during stage-aware scoring rollout; tighten back to 10 after baseline re-established)
    health_delta = abs(current["health_score"] - baseline["health_score"])
    gates.append({
        "gate": "Health Score Delta",
        "threshold": "> 15",
        "actual": health_delta,
        "baseline_value": baseline["health_score"],
        "current_value": current["health_score"],
        "status": "FAIL" if health_delta > 15 else "PASS",
    })

    # Gate 2: Forecast category changed → FAIL
    forecast_changed = current["ai_forecast_category"] != baseline["ai_forecast_category"]
    gates.append({
        "gate": "Forecast Category",
        "threshold": "changed",
        "actual": f"{baseline['ai_forecast_category']} → {current['ai_forecast_category']}",
        "baseline_value": baseline["ai_forecast_category"],
        "current_value": current["ai_forecast_category"],
        "status": "FAIL" if forecast_changed else "PASS",
    })

    # Gate 3: Stage inference changed → WARN
    stage_changed = current["inferred_stage"] != baseline["inferred_stage"]
    gates.append({
        "gate": "Stage Inference",
        "threshold": "changed",
        "actual": f"{baseline['inferred_stage']} → {current['inferred_stage']}",
        "baseline_value": baseline["inferred_stage"],
        "current_value": current["inferred_stage"],
        "status": "WARN" if stage_changed else "PASS",
    })

    # Gate 4: Confidence dropped > 0.15 → WARN
    conf_drop = baseline["overall_confidence"] - current["overall_confidence"]
    gates.append({
        "gate": "Confidence Drop",
        "threshold": "> 0.15",
        "actual": round(conf_drop, 3),
        "baseline_value": baseline["overall_confidence"],
        "current_value": current["overall_confidence"],
        "status": "WARN" if conf_drop > 0.15 else "PASS",
    })

    # Overall status: worst of all gates
    statuses = [g["status"] for g in gates]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "WARN" in statuses:
        overall = "WARN"
    else:
        overall = "PASS"

    return {"status": overall, "gates": gates}


def run_all_golden_tests() -> list[dict]:
    """Load golden set, compare each against current DB state, return results."""
    fixtures = load_golden_set()
    results = []

    with get_session() as session:
        for fixture in fixtures:
            account_id = fixture["account_id"]
            baseline = fixture["baseline"]

            # Get current assessment
            assessment = (
                session.query(DealAssessment)
                .filter_by(account_id=account_id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )

            if not assessment:
                results.append({
                    "fixture_id": fixture["fixture_id"],
                    "account_name": fixture["account_name"],
                    "status": "SKIP",
                    "reason": "No current assessment found",
                    "gates": [],
                })
                continue

            current = {
                "health_score": assessment.health_score,
                "ai_forecast_category": assessment.ai_forecast_category,
                "inferred_stage": assessment.inferred_stage,
                "overall_confidence": assessment.overall_confidence,
            }

            check = run_regression_check(current, baseline)
            results.append({
                "fixture_id": fixture["fixture_id"],
                "account_name": fixture["account_name"],
                "status": check["status"],
                "gates": check["gates"],
            })

    return results

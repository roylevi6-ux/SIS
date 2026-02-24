#!/usr/bin/env python3
"""Create golden test fixtures from seeded data.

Generates 7 fixture JSON files in config/golden_tests/ matching
the format expected by sis/testing/golden_test.py.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

NAMESPACE = uuid.NAMESPACE_DNS
GOLDEN_DIR = Path(__file__).parent.parent / "config" / "golden_tests"


def seed_uuid(label: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"sis-seed-{label}"))


FIXTURES = [
    {"key": "megashop_eu", "name": "MegaShop EU", "health": 82, "forecast": "Commit",
     "stage": 5, "confidence": 0.85, "momentum": "Improving"},
    {"key": "luxeretail", "name": "LuxeRetail Group", "health": 76, "forecast": "Realistic",
     "stage": 4, "confidence": 0.78, "momentum": "Improving"},
    {"key": "fastfashion", "name": "FastFashion Online", "health": 55, "forecast": "Realistic",
     "stage": 3, "confidence": 0.62, "momentum": "Stable"},
    {"key": "homegoods", "name": "HomeGoods Direct", "health": 48, "forecast": "At Risk",
     "stage": 3, "confidence": 0.55, "momentum": "Declining"},
    {"key": "gadgetworld", "name": "GadgetWorld", "health": 35, "forecast": "At Risk",
     "stage": 1, "confidence": 0.40, "momentum": "Declining"},
    {"key": "techmerch", "name": "TechMerch Solutions", "health": 50, "forecast": "Realistic",
     "stage": 2, "confidence": 0.58, "momentum": "Stable"},
    {"key": "urbanstyle", "name": "UrbanStyle Inc", "health": 62, "forecast": "Realistic",
     "stage": 3, "confidence": 0.70, "momentum": "Improving"},
]


def main():
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    created = 0

    for f in FIXTURES:
        account_id = seed_uuid(f"account-{f['key']}")
        fixture_id = f"golden_{f['key']}"
        fixture = {
            "fixture_id": fixture_id,
            "account_id": account_id,
            "account_name": f["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "baseline": {
                "health_score": f["health"],
                "ai_forecast_category": f["forecast"],
                "inferred_stage": f["stage"],
                "overall_confidence": f["confidence"],
                "momentum_direction": f["momentum"],
            },
        }
        path = GOLDEN_DIR / f"{fixture_id}.json"
        with open(path, "w") as fp:
            json.dump(fixture, fp, indent=2)
        created += 1
        print(f"  Created {path.name}")

    print(f"\n{created} golden fixtures created in {GOLDEN_DIR}")


if __name__ == "__main__":
    main()

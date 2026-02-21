"""Test golden test fixtures — regression check, fixture loading."""

import json
from pathlib import Path

from sis.testing.golden_test import load_golden_set, run_regression_check, GOLDEN_DIR


class TestGoldenFixtures:
    def test_golden_dir_exists(self):
        assert GOLDEN_DIR.exists()

    def test_load_golden_set(self):
        fixtures = load_golden_set()
        assert len(fixtures) == 7
        fixture_ids = {f["fixture_id"] for f in fixtures}
        assert "golden_megashop_eu" in fixture_ids
        assert "golden_gadgetworld" in fixture_ids

    def test_fixture_format(self):
        fixtures = load_golden_set()
        for f in fixtures:
            assert "fixture_id" in f
            assert "account_id" in f
            assert "account_name" in f
            assert "baseline" in f
            baseline = f["baseline"]
            assert "health_score" in baseline
            assert "ai_forecast_category" in baseline
            assert "inferred_stage" in baseline
            assert "overall_confidence" in baseline
            assert "momentum_direction" in baseline

    def test_regression_check_pass(self):
        current = {
            "health_score": 80,
            "ai_forecast_category": "Commit",
            "inferred_stage": 5,
            "overall_confidence": 0.85,
        }
        baseline = {
            "health_score": 82,
            "ai_forecast_category": "Commit",
            "inferred_stage": 5,
            "overall_confidence": 0.85,
        }
        result = run_regression_check(current, baseline)
        assert result["status"] == "PASS"

    def test_regression_check_health_fail(self):
        current = {"health_score": 60, "ai_forecast_category": "Commit",
                    "inferred_stage": 5, "overall_confidence": 0.85}
        baseline = {"health_score": 82, "ai_forecast_category": "Commit",
                     "inferred_stage": 5, "overall_confidence": 0.85}
        result = run_regression_check(current, baseline)
        assert result["status"] == "FAIL"
        assert any(g["gate"] == "Health Score Delta" and g["status"] == "FAIL"
                    for g in result["gates"])

    def test_regression_check_forecast_fail(self):
        current = {"health_score": 82, "ai_forecast_category": "At Risk",
                    "inferred_stage": 5, "overall_confidence": 0.85}
        baseline = {"health_score": 82, "ai_forecast_category": "Commit",
                     "inferred_stage": 5, "overall_confidence": 0.85}
        result = run_regression_check(current, baseline)
        assert result["status"] == "FAIL"

    def test_regression_check_stage_warn(self):
        current = {"health_score": 82, "ai_forecast_category": "Commit",
                    "inferred_stage": 4, "overall_confidence": 0.85}
        baseline = {"health_score": 82, "ai_forecast_category": "Commit",
                     "inferred_stage": 5, "overall_confidence": 0.85}
        result = run_regression_check(current, baseline)
        assert result["status"] == "WARN"

    def test_regression_check_confidence_warn(self):
        current = {"health_score": 82, "ai_forecast_category": "Commit",
                    "inferred_stage": 5, "overall_confidence": 0.60}
        baseline = {"health_score": 82, "ai_forecast_category": "Commit",
                     "inferred_stage": 5, "overall_confidence": 0.85}
        result = run_regression_check(current, baseline)
        assert result["status"] == "WARN"

"""Test validate_synthesis_output — boundary values and all checks."""

from __future__ import annotations

from sis.validation import validate_synthesis_output


def _valid_synthesis() -> dict:
    """Return a minimal valid synthesis output."""
    return {
        "deal_memo": "A" * 150,  # > 100 chars
        "inferred_stage": 3,
        "inferred_stage_name": "Scope",
        "health_score": 72,
        "health_score_breakdown": [{"dimension": "eb", "score": 70}],
        "momentum_direction": "Improving",
        "forecast_category": "Commit",
        "top_positive_signals": [{"signal": "Good"}],
        "top_risks": [{"risk": "Budget"}],
        "recommended_actions": [{"action": "Call"}],
        "confidence_interval": {"overall_confidence": 0.75},
    }


class TestRequiredFields:
    def test_clean_output_no_warnings(self):
        warnings = validate_synthesis_output(_valid_synthesis())
        assert len(warnings) == 0

    def test_missing_deal_memo(self):
        s = _valid_synthesis()
        s["deal_memo"] = None
        warnings = validate_synthesis_output(s)
        assert any("deal_memo" in w and "None" in w for w in warnings)

    def test_empty_string_field(self):
        s = _valid_synthesis()
        s["deal_memo"] = "   "
        warnings = validate_synthesis_output(s)
        assert any("EMPTY_FIELD" in w for w in warnings)


class TestHealthScore:
    def test_health_at_zero(self):
        s = _valid_synthesis()
        s["health_score"] = 0
        warnings = validate_synthesis_output(s)
        assert not any("INVALID_HEALTH" in w for w in warnings)

    def test_health_at_100(self):
        s = _valid_synthesis()
        s["health_score"] = 100
        warnings = validate_synthesis_output(s)
        assert not any("INVALID_HEALTH" in w for w in warnings)

    def test_health_negative(self):
        s = _valid_synthesis()
        s["health_score"] = -1
        warnings = validate_synthesis_output(s)
        assert any("INVALID_HEALTH" in w for w in warnings)

    def test_health_over_100(self):
        s = _valid_synthesis()
        s["health_score"] = 101
        warnings = validate_synthesis_output(s)
        assert any("INVALID_HEALTH" in w for w in warnings)

    def test_health_string_type(self):
        s = _valid_synthesis()
        s["health_score"] = "high"
        warnings = validate_synthesis_output(s)
        assert any("INVALID_HEALTH" in w for w in warnings)


class TestStage:
    def test_stage_at_1(self):
        s = _valid_synthesis()
        s["inferred_stage"] = 1
        warnings = validate_synthesis_output(s)
        assert not any("INVALID_STAGE" in w for w in warnings)

    def test_stage_at_7(self):
        s = _valid_synthesis()
        s["inferred_stage"] = 7
        warnings = validate_synthesis_output(s)
        assert not any("INVALID_STAGE" in w for w in warnings)

    def test_stage_zero(self):
        s = _valid_synthesis()
        s["inferred_stage"] = 0
        warnings = validate_synthesis_output(s)
        assert any("INVALID_STAGE" in w for w in warnings)

    def test_stage_eight(self):
        s = _valid_synthesis()
        s["inferred_stage"] = 8
        warnings = validate_synthesis_output(s)
        assert any("INVALID_STAGE" in w for w in warnings)


class TestConfidence:
    def test_confidence_at_zero(self):
        s = _valid_synthesis()
        s["confidence_interval"] = {"overall_confidence": 0.0}
        warnings = validate_synthesis_output(s)
        assert not any("INVALID_CONFIDENCE" in w for w in warnings)

    def test_confidence_at_one(self):
        s = _valid_synthesis()
        s["confidence_interval"] = {"overall_confidence": 1.0}
        warnings = validate_synthesis_output(s)
        assert not any("INVALID_CONFIDENCE" in w for w in warnings)

    def test_confidence_negative(self):
        s = _valid_synthesis()
        s["confidence_interval"] = {"overall_confidence": -0.1}
        warnings = validate_synthesis_output(s)
        assert any("INVALID_CONFIDENCE" in w for w in warnings)

    def test_confidence_over_one(self):
        s = _valid_synthesis()
        s["confidence_interval"] = {"overall_confidence": 1.5}
        warnings = validate_synthesis_output(s)
        assert any("INVALID_CONFIDENCE" in w for w in warnings)


class TestMomentum:
    def test_valid_momentum_values(self):
        for direction in ["Improving", "Stable", "Declining", "Unknown"]:
            s = _valid_synthesis()
            s["momentum_direction"] = direction
            warnings = validate_synthesis_output(s)
            assert not any("INVALID_MOMENTUM" in w for w in warnings)

    def test_invalid_momentum(self):
        s = _valid_synthesis()
        s["momentum_direction"] = "Going Up"
        warnings = validate_synthesis_output(s)
        assert any("INVALID_MOMENTUM" in w for w in warnings)


class TestForecastCategory:
    def test_valid_categories(self):
        for cat in ["Commit", "Realistic", "Upside", "At Risk"]:
            s = _valid_synthesis()
            s["forecast_category"] = cat
            warnings = validate_synthesis_output(s)
            assert not any("INVALID_FORECAST" in w for w in warnings)

    def test_invalid_category(self):
        s = _valid_synthesis()
        s["forecast_category"] = "Maybe"
        warnings = validate_synthesis_output(s)
        assert any("INVALID_FORECAST" in w for w in warnings)


class TestDealMemoLength:
    def test_short_memo(self):
        s = _valid_synthesis()
        s["deal_memo"] = "Too short"
        warnings = validate_synthesis_output(s)
        assert any("SHORT_MEMO" in w for w in warnings)

    def test_adequate_memo(self):
        s = _valid_synthesis()
        s["deal_memo"] = "X" * 100
        warnings = validate_synthesis_output(s)
        assert not any("SHORT_MEMO" in w for w in warnings)


class TestNeverRulesIntegration:
    def test_never_rules_run_with_agent_outputs(self):
        s = _valid_synthesis()
        s["health_score"] = 85
        agent_outputs = {
            "agent_2": {"findings": {"champion": {"identified": False}}},
            "agent_6": {"findings": {"eb_identified": False}},
            "agent_9": {"findings": {"adversarial_challenges": [{"c": "test"}]}},
        }
        warnings = validate_synthesis_output(s, agent_outputs=agent_outputs)
        assert any("NEVER_RULE" in w for w in warnings)

    def test_never_rules_skipped_without_agent_outputs(self):
        s = _valid_synthesis()
        s["health_score"] = 85
        warnings = validate_synthesis_output(s, agent_outputs=None)
        assert not any("NEVER_RULE" in w for w in warnings)

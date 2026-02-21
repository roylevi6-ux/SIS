"""Test validation — validate_agent_output() + apply_confidence_penalties()."""

from sis.validation import validate_agent_output, apply_confidence_penalties


class TestValidateAgentOutput:
    def test_clean_output(self):
        output = {
            "agent_id": "agent_1",
            "narrative": "This is a sufficiently long narrative for validation purposes that exceeds minimum.",
            "evidence": [
                {"quote": "Quote 1", "interpretation": "Interp 1"},
                {"quote": "Quote 2", "interpretation": "Interp 2"},
                {"quote": "Quote 3", "interpretation": "Interp 3"},
            ],
            "confidence": {"overall": 0.80},
            "sparse_data_flag": False,
        }
        warnings = validate_agent_output(output)
        assert len(warnings) == 0

    def test_missing_evidence(self):
        output = {
            "agent_id": "agent_1",
            "narrative": "This is a sufficiently long narrative for validation to pass length check.",
            "evidence": [],
            "confidence": {"overall": 0.50},
        }
        warnings = validate_agent_output(output)
        assert any("UNVERIFIED" in w for w in warnings)

    def test_high_confidence_low_evidence(self):
        output = {
            "agent_id": "agent_1",
            "narrative": "This is a sufficiently long narrative for validation to pass length check.",
            "evidence": [{"quote": "one"}],
            "confidence": {"overall": 0.80},
        }
        warnings = validate_agent_output(output)
        assert any("3+" in w for w in warnings)

    def test_sparse_data_high_confidence(self):
        output = {
            "agent_id": "agent_1",
            "narrative": "This is a sufficiently long narrative for validation to pass length check.",
            "evidence": [{"quote": "a"}, {"quote": "b"}, {"quote": "c"}],
            "confidence": {"overall": 0.80},
            "sparse_data_flag": True,
        }
        warnings = validate_agent_output(output)
        assert any("sparse_data_flag" in w for w in warnings)

    def test_missing_agent_id(self):
        output = {
            "narrative": "This is a sufficiently long narrative for validation to pass length check.",
            "evidence": [{"quote": "a"}],
            "confidence": {"overall": 0.50},
        }
        warnings = validate_agent_output(output)
        assert any("agent_id" in w for w in warnings)

    def test_short_narrative(self):
        output = {
            "agent_id": "agent_1",
            "narrative": "Too short",
            "evidence": [{"quote": "a"}],
            "confidence": {"overall": 0.50},
        }
        warnings = validate_agent_output(output)
        assert any("Narrative" in w for w in warnings)


class TestApplyConfidencePenalties:
    def test_no_penalties(self):
        adjusted, reasons = apply_confidence_penalties(0.80, transcript_count=3)
        assert adjusted == 0.80
        assert len(reasons) == 0

    def test_single_transcript_penalty(self):
        adjusted, reasons = apply_confidence_penalties(0.80, transcript_count=1)
        assert adjusted == 0.65
        assert any("-0.15" in r for r in reasons)

    def test_key_stakeholder_absent(self):
        adjusted, reasons = apply_confidence_penalties(
            0.80, transcript_count=3, key_stakeholder_absent=True
        )
        assert abs(adjusted - 0.70) < 0.001
        assert any("stakeholder" in r.lower() for r in reasons)

    def test_contradicting_evidence(self):
        adjusted, reasons = apply_confidence_penalties(
            0.80, transcript_count=3, contradicting_evidence=True
        )
        assert abs(adjusted - 0.70) < 0.001

    def test_stale_data(self):
        adjusted, reasons = apply_confidence_penalties(
            0.80, transcript_count=3, most_recent_transcript_age_days=45
        )
        assert adjusted == 0.75

    def test_sparse_data_ceiling(self):
        adjusted, reasons = apply_confidence_penalties(
            0.90, transcript_count=3, sparse_data_flag=True
        )
        assert adjusted == 0.75
        assert any("ceiling" in r.lower() for r in reasons)

    def test_multiple_penalties_stack(self):
        adjusted, reasons = apply_confidence_penalties(
            0.90, transcript_count=1,
            key_stakeholder_absent=True, contradicting_evidence=True,
            most_recent_transcript_age_days=45,
        )
        # 0.90 - 0.15 - 0.10 - 0.10 - 0.05 = 0.50
        assert adjusted == 0.50
        assert len(reasons) == 4

    def test_floor_at_zero(self):
        adjusted, reasons = apply_confidence_penalties(
            0.20, transcript_count=1,
            key_stakeholder_absent=True, contradicting_evidence=True,
        )
        assert adjusted == 0.0

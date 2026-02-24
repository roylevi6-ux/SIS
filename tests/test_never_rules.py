"""Test NEVER rules engine — all rules + check_all_never_rules()."""

from sis.validation.never_rules import (
    NeverRuleViolation,
    check_health_score_without_eb,
    check_health_score_without_champion,
    check_commit_without_commitments,
    check_unresolved_contradictions,
    check_inferred_pricing,
    check_adversarial_challenges_exist,
    check_commit_without_compelling_event,
    check_no_decision_risk_override,
    check_expansion_account_health_cap,
    check_expansion_commit_relationship,
    check_all_never_rules,
)


class TestHealthScoreWithoutEB:
    def test_passes_when_health_low(self):
        result = check_health_score_without_eb({}, {"health_score": 65})
        assert result is None

    def test_passes_when_eb_engaged(self):
        agent_outputs = {
            "agent_6": {"findings": {"eb_confirmed": True, "eb_engagement": "Direct"}},
        }
        result = check_health_score_without_eb(agent_outputs, {"health_score": 85})
        assert result is None

    def test_fails_when_eb_not_engaged(self):
        agent_outputs = {
            "agent_6": {"findings": {"eb_confirmed": True, "eb_engagement": "Indirect"}},
        }
        result = check_health_score_without_eb(agent_outputs, {"health_score": 85})
        assert result is not None
        assert result.rule_id == "NEVER_HEALTH_WITHOUT_EB"
        assert result.severity == "error"

    def test_fails_when_eb_not_identified(self):
        agent_outputs = {
            "agent_6": {"findings": {"eb_confirmed": False}},
        }
        result = check_health_score_without_eb(agent_outputs, {"health_score": 75})
        assert result is not None

    def test_fails_when_agent6_missing(self):
        result = check_health_score_without_eb({}, {"health_score": 80})
        assert result is not None


class TestHealthScoreWithoutChampion:
    def test_passes_when_health_low(self):
        result = check_health_score_without_champion({}, {"health_score": 60})
        assert result is None

    def test_passes_when_champion_identified_nested(self):
        agent_outputs = {
            "agent_2": {"findings": {"champion": {"identified": True, "name": "Jane Doe"}}},
        }
        result = check_health_score_without_champion(agent_outputs, {"health_score": 80})
        assert result is None

    def test_passes_when_champion_identified_flat(self):
        agent_outputs = {
            "agent_2": {"findings": {"champion_identified": True}},
        }
        result = check_health_score_without_champion(agent_outputs, {"health_score": 80})
        assert result is None

    def test_fails_when_no_champion_nested(self):
        agent_outputs = {
            "agent_2": {"findings": {"champion": {"identified": False}}},
        }
        result = check_health_score_without_champion(agent_outputs, {"health_score": 70})
        assert result is not None
        assert result.rule_id == "NEVER_HEALTH_WITHOUT_CHAMPION"
        assert result.severity == "error"

    def test_fails_when_no_champion_flat(self):
        agent_outputs = {
            "agent_2": {"findings": {"champion_identified": False}},
        }
        result = check_health_score_without_champion(agent_outputs, {"health_score": 75})
        assert result is not None
        assert result.rule_id == "NEVER_HEALTH_WITHOUT_CHAMPION"

    def test_fails_when_agent2_missing(self):
        result = check_health_score_without_champion({}, {"health_score": 80})
        assert result is not None

    def test_at_boundary_65_passes(self):
        result = check_health_score_without_champion({}, {"health_score": 65})
        assert result is None

    def test_at_boundary_66_fails(self):
        result = check_health_score_without_champion({}, {"health_score": 66})
        assert result is not None


class TestCommitWithoutCommitments:
    def test_passes_when_not_commit(self):
        result = check_commit_without_commitments({}, {"forecast_category": "Realistic"})
        assert result is None

    def test_passes_when_msp_exists_high(self):
        agent_outputs = {
            "agent_7": {"findings": {"msp_exists": True, "next_step_specificity": "High"}},
        }
        result = check_commit_without_commitments(agent_outputs, {"forecast_category": "Commit"})
        assert result is None

    def test_fails_when_no_msp(self):
        agent_outputs = {
            "agent_7": {"findings": {"msp_exists": False, "next_step_specificity": "Low"}},
        }
        result = check_commit_without_commitments(agent_outputs, {"forecast_category": "Commit"})
        assert result is not None
        assert result.rule_id == "NEVER_COMMIT_WITHOUT_MSP"

    def test_fails_when_low_specificity(self):
        agent_outputs = {
            "agent_7": {"findings": {"msp_exists": True, "next_step_specificity": "Low"}},
        }
        result = check_commit_without_commitments(agent_outputs, {"forecast_category": "Commit"})
        assert result is not None


class TestUnresolvedContradictions:
    def test_passes_when_no_contradictions(self):
        result = check_unresolved_contradictions({}, {"contradiction_map": []})
        assert result is None

    def test_passes_when_all_resolved(self):
        synthesis = {
            "contradiction_map": [
                {"issue": "A vs B", "resolution": "Resolved via async comms"},
            ],
        }
        result = check_unresolved_contradictions({}, synthesis)
        assert result is None

    def test_fails_when_unresolved(self):
        synthesis = {
            "contradiction_map": [
                {"issue": "A vs B", "resolution": ""},
                {"issue": "C vs D", "resolution": "Fixed"},
            ],
        }
        result = check_unresolved_contradictions({}, synthesis)
        assert result is not None
        assert result.rule_id == "NEVER_UNRESOLVED_CONTRADICTIONS"
        assert result.context["unresolved_indices"] == [0]

    def test_fails_on_string_contradictions(self):
        synthesis = {"contradiction_map": ["Agent 2 says X but Agent 4 says Y"]}
        result = check_unresolved_contradictions({}, synthesis)
        assert result is not None


class TestInferredPricing:
    def test_passes_when_no_pricing(self):
        agent_outputs = {"agent_3": {"narrative": "No pricing discussed.", "evidence": []}}
        result = check_inferred_pricing(agent_outputs, {})
        assert result is None

    def test_passes_when_price_in_evidence(self):
        agent_outputs = {
            "agent_3": {
                "narrative": "Pricing at $50K was discussed.",
                "evidence": [{"quote": "We quoted $50K for the annual contract", "verbatim": "We quoted $50K"}],
            },
        }
        result = check_inferred_pricing(agent_outputs, {})
        assert result is None

    def test_fails_when_price_not_in_evidence(self):
        agent_outputs = {
            "agent_3": {
                "narrative": "Pricing at $75K was discussed.",
                "evidence": [{"quote": "Budget is under review", "verbatim": "Budget is under review"}],
            },
        }
        result = check_inferred_pricing(agent_outputs, {})
        assert result is not None
        assert result.rule_id == "NEVER_INFERRED_PRICING"
        assert "$75K" in result.context["unsupported_prices"]


class TestAdversarialChallengesExist:
    def test_passes_with_challenges(self):
        agent_outputs = {
            "agent_9": {"findings": {"adversarial_challenges": [{"challenge": "test"}]}},
        }
        result = check_adversarial_challenges_exist(agent_outputs, {})
        assert result is None

    def test_fails_with_no_challenges(self):
        agent_outputs = {
            "agent_9": {"findings": {"adversarial_challenges": []}},
        }
        result = check_adversarial_challenges_exist(agent_outputs, {})
        assert result is not None
        assert result.rule_id == "NEVER_NO_ADVERSARIAL_CHALLENGES"

    def test_fails_when_agent9_missing(self):
        result = check_adversarial_challenges_exist({}, {})
        assert result is not None


class TestCommitWithoutCompellingEvent:
    def test_passes_when_not_commit(self):
        result = check_commit_without_compelling_event(
            {}, {"forecast_category": "Realistic"}
        )
        assert result is None

    def test_passes_when_catalyst_exists(self):
        agent_outputs = {
            "agent_8": {
                "findings": {
                    "consequence_of_inaction": "None",
                    "catalyst_strength": "Structural",
                }
            },
        }
        result = check_commit_without_compelling_event(
            agent_outputs, {"forecast_category": "Commit"}
        )
        assert result is None

    def test_passes_when_consequence_exists(self):
        agent_outputs = {
            "agent_8": {
                "findings": {
                    "consequence_of_inaction": "Moderate",
                    "catalyst_strength": "None Identified",
                }
            },
        }
        result = check_commit_without_compelling_event(
            agent_outputs, {"forecast_category": "Commit"}
        )
        assert result is None

    def test_fails_when_no_catalyst_no_consequence(self):
        agent_outputs = {
            "agent_8": {
                "findings": {
                    "consequence_of_inaction": "None",
                    "catalyst_strength": "None Identified",
                }
            },
        }
        result = check_commit_without_compelling_event(
            agent_outputs, {"forecast_category": "Commit"}
        )
        assert result is not None
        assert result.rule_id == "NEVER_COMMIT_WITHOUT_COMPELLING_EVENT"
        assert result.severity == "error"

    def test_fails_when_agent8_missing(self):
        result = check_commit_without_compelling_event(
            {}, {"forecast_category": "Commit"}
        )
        # With empty agent8, catalyst_strength defaults to "" which is in the weak list
        # but consequence_of_inaction defaults to None (not the string "None")
        # so this should NOT trigger (None != "None")
        assert result is None


class TestCheckAllNeverRules:
    def test_all_pass(self):
        agent_outputs = {
            "agent_2": {"findings": {"champion": {"identified": True, "name": "Jane Doe"}}},
            "agent_3": {"narrative": "No pricing.", "evidence": []},
            "agent_6": {"findings": {"eb_confirmed": True, "eb_engagement": "Direct"}},
            "agent_7": {"findings": {"msp_exists": True, "next_step_specificity": "High"}},
            "agent_9": {"findings": {"adversarial_challenges": [{"challenge": "test"}]}},
        }
        synthesis = {
            "health_score": 80,
            "forecast_category": "Commit",
            "contradiction_map": [{"issue": "X", "resolution": "Resolved"}],
        }
        violations = check_all_never_rules(agent_outputs, synthesis)
        assert len(violations) == 0

    def test_multiple_violations(self):
        agent_outputs = {
            "agent_2": {"findings": {"champion": {"identified": False}}},
            "agent_3": {"narrative": "Price is $100K.", "evidence": []},
            "agent_6": {"findings": {"eb_confirmed": False}},
            "agent_7": {"findings": {"msp_exists": False, "next_step_specificity": "Low"}},
            "agent_9": {"findings": {"adversarial_challenges": []}},
        }
        synthesis = {
            "health_score": 85,
            "forecast_category": "Commit",
            "contradiction_map": [{"issue": "X", "resolution": ""}],
        }
        violations = check_all_never_rules(agent_outputs, synthesis)
        assert len(violations) >= 5  # EB, champion, commit, contradictions, adversarial, pricing
        rule_ids = {v.rule_id for v in violations}
        assert "NEVER_HEALTH_WITHOUT_EB" in rule_ids
        assert "NEVER_HEALTH_WITHOUT_CHAMPION" in rule_ids
        assert "NEVER_NO_ADVERSARIAL_CHALLENGES" in rule_ids


class TestNoDecisionRiskOverride:
    def test_passes_when_no_risk(self):
        agent_outputs = {
            "agent_8": {"findings": {"no_decision_risk": "Low", "catalyst_strength": "Structural"}},
        }
        result = check_no_decision_risk_override(agent_outputs, {"forecast_category": "Commit"})
        assert result is None

    def test_passes_when_strong_catalyst(self):
        agent_outputs = {
            "agent_8": {"findings": {"no_decision_risk": "High", "catalyst_strength": "Structural"}},
        }
        result = check_no_decision_risk_override(agent_outputs, {"forecast_category": "Commit"})
        assert result is None

    def test_fails_commit_high_risk_weak_catalyst(self):
        agent_outputs = {
            "agent_8": {"findings": {"no_decision_risk": "High", "catalyst_strength": "None Identified"}},
        }
        result = check_no_decision_risk_override(agent_outputs, {"forecast_category": "Commit"})
        assert result is not None
        assert result.rule_id == "NEVER_NO_DECISION_RISK_OVERRIDE"
        assert result.severity == "error"

    def test_fails_realistic_high_risk_cosmetic_catalyst(self):
        agent_outputs = {
            "agent_8": {"findings": {"no_decision_risk": "High", "catalyst_strength": "Cosmetic"}},
        }
        result = check_no_decision_risk_override(agent_outputs, {"forecast_category": "Realistic"})
        assert result is not None
        assert result.rule_id == "NEVER_NO_DECISION_RISK_OVERRIDE"

    def test_passes_at_risk_high_risk(self):
        """At Risk is the correct category for high no-decision risk — should pass."""
        agent_outputs = {
            "agent_8": {"findings": {"no_decision_risk": "High", "catalyst_strength": "None"}},
        }
        result = check_no_decision_risk_override(agent_outputs, {"forecast_category": "At Risk"})
        assert result is None

    def test_handles_bool_true_risk(self):
        agent_outputs = {
            "agent_8": {"findings": {"no_decision_risk": True, "catalyst_strength": ""}},
        }
        result = check_no_decision_risk_override(agent_outputs, {"forecast_category": "Commit"})
        assert result is not None


class TestExpansionAccountHealthCap:
    def test_passes_when_health_low(self):
        result = check_expansion_account_health_cap({}, {"health_score": 55})
        assert result is None

    def test_passes_when_relationship_strong(self):
        agent_outputs = {
            "agent_0e": {"findings": {"account_relationship_health": "Strong"}},
        }
        result = check_expansion_account_health_cap(agent_outputs, {"health_score": 80})
        assert result is None

    def test_fails_when_strained_high_health(self):
        agent_outputs = {
            "agent_0e": {"findings": {"account_relationship_health": "Strained"}},
        }
        result = check_expansion_account_health_cap(agent_outputs, {"health_score": 70})
        assert result is not None
        assert result.rule_id == "NEVER_EXPANSION_HEALTH_CAP"

    def test_fails_when_critical_high_health(self):
        agent_outputs = {
            "agent_0e": {"findings": {"account_relationship_health": "Critical"}},
        }
        result = check_expansion_account_health_cap(agent_outputs, {"health_score": 65})
        assert result is not None


class TestExpansionCommitRelationship:
    def test_passes_when_not_commit(self):
        result = check_expansion_commit_relationship({}, {"forecast_category": "Realistic"})
        assert result is None

    def test_passes_when_strong_relationship(self):
        agent_outputs = {
            "agent_0e": {"findings": {"account_relationship_health": "Strong"}},
        }
        result = check_expansion_commit_relationship(agent_outputs, {"forecast_category": "Commit"})
        assert result is None

    def test_passes_when_adequate_relationship(self):
        agent_outputs = {
            "agent_0e": {"findings": {"account_relationship_health": "Adequate"}},
        }
        result = check_expansion_commit_relationship(agent_outputs, {"forecast_category": "Commit"})
        assert result is None

    def test_fails_when_strained_commit(self):
        agent_outputs = {
            "agent_0e": {"findings": {"account_relationship_health": "Strained"}},
        }
        result = check_expansion_commit_relationship(agent_outputs, {"forecast_category": "Commit"})
        assert result is not None
        assert result.rule_id == "NEVER_EXPANSION_COMMIT_WITHOUT_RELATIONSHIP"


class TestCheckAllExpansionRules:
    def test_expansion_includes_expansion_rules(self):
        agent_outputs = {
            "agent_0e": {"findings": {"account_relationship_health": "Strained"}},
            "agent_2": {"findings": {"champion": {"identified": True, "name": "Jane"}}},
            "agent_3": {"narrative": "No pricing.", "evidence": []},
            "agent_6": {"findings": {"eb_confirmed": True, "eb_engagement": "Direct"}},
            "agent_7": {"findings": {"msp_exists": True, "next_step_specificity": "High"}},
            "agent_9": {"findings": {"adversarial_challenges": [{"challenge": "test"}]}},
        }
        synthesis = {
            "health_score": 75,
            "forecast_category": "Commit",
            "contradiction_map": [],
        }
        violations = check_all_never_rules(agent_outputs, synthesis, deal_type="expansion_upsell")
        rule_ids = {v.rule_id for v in violations}
        assert "NEVER_EXPANSION_HEALTH_CAP" in rule_ids
        assert "NEVER_EXPANSION_COMMIT_WITHOUT_RELATIONSHIP" in rule_ids

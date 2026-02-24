"""Test urgency-related schema additions across agents 4, 7, 8, 9, 10."""

from sis.agents.momentum import UrgencyImpact, MomentumFindings
from sis.agents.msp_next_steps import CompellingDeadline, NextStep, MSPNextStepsFindings
from sis.agents.competitive import CompetitiveFindings
from sis.agents.open_discovery import UrgencyAudit, OpenDiscoveryFindings


class TestUrgencyImpactSchema:
    """Agent 4: UrgencyImpact model."""

    def test_urgency_impact_creation(self):
        ui = UrgencyImpact(
            urgency_detected=True,
            urgency_behavioral_match="Aligned",
            urgency_trend="Increasing",
            urgency_evidence="Buyer pulled in VP to meet the Q2 deadline.",
        )
        assert ui.urgency_detected is True
        assert ui.urgency_behavioral_match == "Aligned"
        assert ui.urgency_trend == "Increasing"

    def test_momentum_findings_urgency_optional(self):
        """urgency_impact defaults to None when not provided."""
        findings = MomentumFindings(
            momentum_direction="Improving",
            call_cadence_assessment="Regular",
            meeting_initiation="Buyer-initiated",
            buyer_engagement_quality="High",
            topic_evolution="Narrowing",
            next_step_specificity="High",
            structural_advancement="Strong",
        )
        assert findings.urgency_impact is None

    def test_momentum_findings_with_urgency(self):
        ui = UrgencyImpact(
            urgency_detected=False,
            urgency_behavioral_match="Ambiguous",
            urgency_trend="None",
            urgency_evidence="No urgency signals detected.",
        )
        findings = MomentumFindings(
            momentum_direction="Stable",
            call_cadence_assessment="Regular",
            meeting_initiation="Mutual",
            buyer_engagement_quality="Medium",
            topic_evolution="Stable",
            urgency_impact=ui,
        )
        assert findings.urgency_impact is not None
        assert findings.urgency_impact.urgency_detected is False


class TestCompellingDeadlineSchema:
    """Agent 7: CompellingDeadline + supports_deadline."""

    def test_compelling_deadline_creation(self):
        cd = CompellingDeadline(
            event_type="Contract Expiry",
            description="Forter contract ends March 31, must have replacement live.",
            date_if_stated="2026-03-31",
            firmness="Hard",
            source="Buyer-stated",
            stability="Stable",
        )
        assert cd.firmness == "Hard"
        assert cd.date_if_stated == "2026-03-31"

    def test_compelling_deadline_no_date(self):
        cd = CompellingDeadline(
            event_type="Executive Mandate",
            description="Board approved fraud initiative for H2.",
            firmness="Firm",
            source="Buyer-stated",
            stability="New",
        )
        assert cd.date_if_stated is None

    def test_next_step_supports_deadline(self):
        ns = NextStep(
            action="Send integration spec",
            owner="Seller",
            specificity="High",
            initiated_by="Buyer",
            confirmed_by_buyer=True,
            status="Pending",
            evidence="Buyer asked for spec by Friday.",
            supports_deadline=True,
        )
        assert ns.supports_deadline is True

    def test_next_step_supports_deadline_default(self):
        ns = NextStep(
            action="Follow up",
            owner="Seller",
            specificity="Low",
            initiated_by="Seller",
            confirmed_by_buyer=False,
            status="Pending",
            evidence="AE said they'd follow up.",
        )
        assert ns.supports_deadline is False

    def test_msp_findings_compelling_deadline_optional(self):
        findings = MSPNextStepsFindings(
            msp_exists=False,
            go_live_date_confirmed=False,
            next_step_specificity="Low",
            structural_advancement="Weak",
        )
        assert findings.compelling_deadline is None


class TestCompetitiveUrgencyFields:
    """Agent 8: consequence_of_inaction, catalyst_time_horizon, urgency_source."""

    def test_defaults(self):
        findings = CompetitiveFindings(
            status_quo_embeddedness="Unknown",
            displacement_readiness="Unknown",
            catalyst_strength="None Identified",
            buying_dynamic="Unknown",
            no_decision_risk="Unknown",
        )
        assert findings.consequence_of_inaction is None
        assert findings.catalyst_time_horizon is None
        assert findings.urgency_source == "None Identified"

    def test_populated(self):
        findings = CompetitiveFindings(
            status_quo_embeddedness="Deep",
            displacement_readiness="High",
            catalyst_strength="Existential",
            buying_dynamic="Replacement",
            no_decision_risk="Low",
            consequence_of_inaction="Severe",
            catalyst_time_horizon="Immediate",
            urgency_source="Customer-initiated",
        )
        assert findings.consequence_of_inaction == "Severe"
        assert findings.catalyst_time_horizon == "Immediate"
        assert findings.urgency_source == "Customer-initiated"


class TestUrgencyAuditSchema:
    """Agent 9: UrgencyAudit (always populated)."""

    def test_urgency_audit_creation(self):
        ua = UrgencyAudit(
            urgency_credibility="Credible",
            assessment="Buyer behavior matches stated urgency across all calls.",
            cross_agent_consistency="Consistent",
            consistency_detail="Agents 4, 7, 8 all show aligned urgency signals.",
        )
        assert ua.urgency_credibility == "Credible"

    def test_urgency_audit_insufficient(self):
        ua = UrgencyAudit(
            urgency_credibility="Insufficient Evidence",
            assessment="No urgency signals detected in any agent output.",
            cross_agent_consistency="Insufficient Data",
            consistency_detail="No urgency fields populated across agents.",
        )
        assert ua.urgency_credibility == "Insufficient Evidence"

    def test_open_discovery_findings_requires_urgency_audit(self):
        ua = UrgencyAudit(
            urgency_credibility="Insufficient Evidence",
            assessment="No urgency.",
            cross_agent_consistency="Insufficient Data",
            consistency_detail="No data.",
        )
        findings = OpenDiscoveryFindings(
            adversarial_challenges=[],
            no_additional_signals=True,
            urgency_audit=ua,
        )
        assert findings.urgency_audit is not None
        assert findings.urgency_audit.urgency_credibility == "Insufficient Evidence"


class TestHealthScoreWeightsSum:
    """Verify health score weights sum to 100."""

    def test_new_logo_weights_sum(self):
        from sis.config import _default_calibration_config

        config = _default_calibration_config()
        weights = config["new_logo"]["synthesis_agent_10"]["health_score_weights"]
        total = sum(weights.values())
        assert total == 100, f"New logo weights sum to {total}, expected 100"
        assert "urgency_compelling_event" in weights

    def test_expansion_weights_sum(self):
        from sis.config import _default_calibration_config

        config = _default_calibration_config()
        weights = config["expansion"]["synthesis_agent_10"]["health_score_weights"]
        total = sum(weights.values())
        assert total == 100, f"Expansion weights sum to {total}, expected 100"
        assert "urgency_compelling_event" in weights

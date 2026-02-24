# Compelling Event Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add compelling event / urgency detection across 5 SIS pipeline agents so managers get a unified "Why Now?" answer and deals without a compelling event can never be Commit.

**Architecture:** Distributed enhancement — Agents 4, 7, 8 get new urgency fields (run in parallel), Agent 9 cross-validates them (sequential), Agent 10 synthesizes into a health score component + deal memo paragraph + forecast guardrail. No new agents, no architecture changes.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, SQLAlchemy 2.0, Sonnet model

**Design Doc:** `docs/plans/2026-02-24-compelling-event-detection-design.md`

---

## Task 1: Agent 4 (Momentum) — Add UrgencyImpact Schema

**Files:**
- Modify: `sis/agents/momentum.py:24-51` (add UrgencyImpact class, update MomentumFindings)
- Test: `tests/test_urgency_schemas.py` (new)

**Step 1: Write the failing test**

```python
# tests/test_urgency_schemas.py
"""Tests for compelling event / urgency schema additions across agents."""

import pytest
from pydantic import ValidationError


class TestUrgencyImpactSchema:
    """Agent 4: UrgencyImpact sub-model."""

    def test_valid_urgency_impact(self):
        from sis.agents.momentum import UrgencyImpact

        ui = UrgencyImpact(
            urgency_detected=True,
            urgency_behavioral_match="Aligned",
            urgency_trend="Increasing",
            urgency_evidence="Buyer pulled in CTO to meet Q3 deadline",
        )
        assert ui.urgency_detected is True
        assert ui.urgency_behavioral_match == "Aligned"

    def test_urgency_impact_in_findings(self):
        from sis.agents.momentum import MomentumFindings, UrgencyImpact

        findings = MomentumFindings(
            momentum_direction="Improving",
            call_cadence_assessment="Accelerating",
            meeting_initiation="Buyer-initiated",
            buyer_engagement_quality="High",
            topic_evolution="Narrowing",
            manager_insight="Deal accelerating.",
            urgency_impact=UrgencyImpact(
                urgency_detected=True,
                urgency_behavioral_match="Mismatched",
                urgency_trend="Fading",
                urgency_evidence="Buyer says urgent but cancelled last 2 meetings",
            ),
        )
        assert findings.urgency_impact is not None
        assert findings.urgency_impact.urgency_behavioral_match == "Mismatched"

    def test_urgency_impact_optional_default_none(self):
        from sis.agents.momentum import MomentumFindings

        findings = MomentumFindings(
            momentum_direction="Stable",
            call_cadence_assessment="Regular",
            meeting_initiation="Mutual",
            buyer_engagement_quality="Medium",
            topic_evolution="Stable",
            manager_insight="Steady engagement.",
        )
        assert findings.urgency_impact is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestUrgencyImpactSchema -v`
Expected: FAIL — `UrgencyImpact` does not exist yet

**Step 3: Implement the schema**

In `sis/agents/momentum.py`, add the `UrgencyImpact` class after `EngagementSignal` (after line 29), and add `urgency_impact` field to `MomentumFindings`:

```python
class UrgencyImpact(BaseModel):
    """Behavioral validation of buyer-stated urgency."""

    urgency_detected: bool = Field(description="Did the buyer express any time pressure?")
    urgency_behavioral_match: str = Field(
        description="Aligned (behavior matches stated urgency), "
        "Mismatched (says urgent, acts slow), or Ambiguous"
    )
    urgency_trend: str = Field(
        description="Increasing, Stable, Fading, or None"
    )
    urgency_evidence: str = Field(
        description="One sentence: the strongest behavioral signal "
        "supporting or contradicting urgency"
    )
```

Add to `MomentumFindings` (before `data_quality_notes`):

```python
    urgency_impact: Optional[UrgencyImpact] = Field(
        default=None,
        description="Urgency behavioral validation. Populate only when "
        "buyer expresses time pressure.",
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestUrgencyImpactSchema -v`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add sis/agents/momentum.py tests/test_urgency_schemas.py
git commit -m "feat(agent4): add UrgencyImpact schema to MomentumFindings"
```

---

## Task 2: Agent 4 (Momentum) — Add Urgency Prompt Sections

**Files:**
- Modify: `sis/agents/momentum.py:69-116` (SYSTEM_PROMPT string)

**Step 1: No test for prompt text — this is a prompt-only change**

Prompt changes are validated by pipeline integration tests, not unit tests.

**Step 2: Add prompt sections**

In `sis/agents/momentum.py`, insert the following after the "Analysis Rules" section (before the closing `"""` and fragment append at line 116):

```python
## Urgency & Deal Velocity
When a buyer mentions timelines, deadlines, or business events:
- Assess whether their BEHAVIOR matches the stated urgency
- A buyer who says "urgent" but responds slowly, delays meetings, or won't pull in stakeholders = Mismatched urgency
- Track urgency trajectory across calls: is the time pressure increasing (approaching deadline) or fading (deadline passed or deprioritized)?
- Urgency that isn't backed by buyer behavior is a forecast risk
- A buyer who says "this is urgent" is stating intent, not proving urgency. Only their ACTIONS prove it.

## Urgency Trend Heuristics
- "Increasing": deadline mentioned with more specificity in recent calls than earlier ones, OR new stakeholders pulled in to meet timeline, OR buyer proactively compresses schedule
- "Fading": deadline mentioned in earlier calls but absent from recent ones, OR buyer language shifted from specific dates to "sometime in Q3", OR previously urgent items now described as "when we get to it"
- "Stable": same deadline referenced consistently across calls with no change in urgency level
- "None": urgency was never mentioned, OR only mentioned once with no follow-through

If fewer than 3 transcripts are available, set urgency_trend to "None" -- a single call cannot establish a trajectory.
If no urgency or time pressure is mentioned, set urgency_impact to null.
```

**Step 3: Verify existing tests still pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short -q`
Expected: All existing tests PASS (prompt changes don't break schema tests)

**Step 4: Commit**

```bash
git add sis/agents/momentum.py
git commit -m "feat(agent4): add urgency detection prompt sections"
```

---

## Task 3: Agent 7 (MSP) — Add CompellingDeadline Schema

**Files:**
- Modify: `sis/agents/msp_next_steps.py:24-58` (add CompellingDeadline, update NextStep + MSPNextStepsFindings)
- Modify: `tests/test_urgency_schemas.py` (add tests)

**Step 1: Write the failing test**

Append to `tests/test_urgency_schemas.py`:

```python
class TestCompellingDeadlineSchema:
    """Agent 7: CompellingDeadline sub-model."""

    def test_valid_compelling_deadline(self):
        from sis.agents.msp_next_steps import CompellingDeadline

        cd = CompellingDeadline(
            event_type="Contract Expiry",
            description="Forter contract expires March 31, must have replacement live",
            date_if_stated="2026-03-31",
            firmness="Hard",
            source="Buyer-stated",
            stability="Stable",
        )
        assert cd.firmness == "Hard"
        assert cd.stability == "Stable"

    def test_compelling_deadline_optional_in_findings(self):
        from sis.agents.msp_next_steps import MSPNextStepsFindings

        findings = MSPNextStepsFindings(
            msp_exists=False,
            go_live_date_confirmed=False,
            next_step_specificity="Low",
            structural_advancement="Weak",
            manager_insight="No clear timeline.",
        )
        assert findings.compelling_deadline is None

    def test_next_step_supports_deadline(self):
        from sis.agents.msp_next_steps import NextStep

        ns = NextStep(
            action="Send data export",
            owner="Buyer",
            specificity="High",
            initiated_by="Buyer",
            confirmed_by_buyer=True,
            status="Pending",
            evidence="We'll have the data ready by Friday",
            supports_deadline=True,
        )
        assert ns.supports_deadline is True

    def test_next_step_supports_deadline_defaults_false(self):
        from sis.agents.msp_next_steps import NextStep

        ns = NextStep(
            action="Let's reconnect",
            owner="Seller",
            specificity="Low",
            initiated_by="Seller",
            confirmed_by_buyer=False,
            status="Pending",
            evidence="Let's circle back next month",
        )
        assert ns.supports_deadline is False
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestCompellingDeadlineSchema -v`
Expected: FAIL — `CompellingDeadline` does not exist yet

**Step 3: Implement the schema**

In `sis/agents/msp_next_steps.py`:

Add `CompellingDeadline` class after the `NextStep` class (after line 34):

```python
class CompellingDeadline(BaseModel):
    """A firm business deadline anchoring the deal timeline."""

    event_type: str = Field(
        description="Contract Expiry | Regulatory/Compliance | Fiscal Year/Budget | "
        "Executive Mandate | Seasonal/Business Cycle | Integration Dependency | Other"
    )
    description: str = Field(
        description="One sentence: what is the deadline and why it matters"
    )
    date_if_stated: Optional[str] = Field(
        default=None,
        description="The actual date/quarter if buyer stated one",
    )
    firmness: str = Field(
        description="Hard (external, immovable) | Firm (internal, committed) | Soft (aspirational)"
    )
    source: str = Field(
        description="Buyer-stated (buyer said date + reason) | Inferred from context"
    )
    stability: str = Field(
        description="Stable (consistent across calls) | Shifted (moved once) | "
        "Repeatedly Moved (red flag) | New (latest call only)"
    )
```

Add to `NextStep` (before `evidence` field):

```python
    supports_deadline: bool = Field(
        default=False,
        description="True if this action is on the critical path to the compelling deadline",
    )
```

Add to `MSPNextStepsFindings` (before `data_quality_notes`):

```python
    compelling_deadline: Optional[CompellingDeadline] = Field(
        default=None,
        description="Populate only when a firm business deadline exists. "
        "Null if no deadline identified.",
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestCompellingDeadlineSchema -v`
Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add sis/agents/msp_next_steps.py tests/test_urgency_schemas.py
git commit -m "feat(agent7): add CompellingDeadline schema and supports_deadline to NextStep"
```

---

## Task 4: Agent 7 (MSP) — Add Deadline Driver Prompt Sections

**Files:**
- Modify: `sis/agents/msp_next_steps.py:76-121` (SYSTEM_PROMPT string)

**Step 1: Add prompt sections**

In `sis/agents/msp_next_steps.py`, insert the following after the "Analysis Rules" section (before the closing `"""` and fragment append at line 121):

```python
## Deadline Drivers
When a go-live date or timeline is mentioned:
- Identify WHAT business event anchors it (contract expiry, regulatory deadline, fiscal year, board mandate, seasonal peak, integration dependency)
- Assess firmness: Hard = externally imposed, immovable (regulatory, contract). Firm = internally committed, has consequences if missed. Soft = aspirational, movable without consequence.
- "Hard" deadlines anchored to external events are the strongest signals of a real deal timeline
- If NO business event anchors any stated timeline, set compelling_deadline to null. Do NOT fabricate deadline drivers from generic "let's aim for Q3" language.

## Scope Boundary: Catalyst vs. Deadline
Agent 8 handles WHY the buyer is considering change (the switching catalyst). Your job is different: you handle WHEN the buyer must act and what makes the timeline stick. A "platform migration" is a catalyst (Agent 8's domain). A "platform migration completing Q3 2026 that requires a new fraud vendor integrated before launch" is a deadline driver (YOUR domain). Focus on the DATE ANCHOR, not the motivation.

## Firmness Examples (Riskified-specific)
- Hard: "We need fraud prevention live before Black Friday" (seasonal, immovable)
- Hard: "Our Forter contract ends March 31" (contractual, external)
- Firm: "Our board approved the fraud initiative for H2 and it's in the 2026 plan" (internal, committed)
- Soft: "We'd like to have something in place by end of year" (aspirational, no consequence stated)

## Source Calibration
"Buyer-stated" = buyer explicitly said a date AND a reason (e.g., "our contract expires in March, so we need to be live by then"). "Inferred from context" = date stated but reason assembled from multiple signals across calls. NEVER infer a compelling deadline from seller-stated timelines alone.

## Deadline + Next Steps
For each next step, assess whether it is on the critical path to the compelling deadline (supports_deadline=true). Most operational next steps (send data, schedule meeting) are NOT on the critical path unless they directly enable meeting the deadline.
```

**Step 2: Verify existing tests still pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add sis/agents/msp_next_steps.py
git commit -m "feat(agent7): add deadline driver prompt sections"
```

---

## Task 5: Agent 8 (Competitive) — Add Consequence + Time Horizon + Source Schema

**Files:**
- Modify: `sis/agents/competitive.py:35-53` (add 3 fields to CompetitiveFindings)
- Modify: `tests/test_urgency_schemas.py` (add tests)

**Step 1: Write the failing test**

Append to `tests/test_urgency_schemas.py`:

```python
class TestCompetitiveUrgencyFields:
    """Agent 8: consequence_of_inaction, catalyst_time_horizon, urgency_source."""

    def test_new_fields_in_competitive_findings(self):
        from sis.agents.competitive import CompetitiveFindings

        findings = CompetitiveFindings(
            status_quo_embeddedness="Deep",
            displacement_readiness="High",
            catalyst_strength="Existential",
            switching_catalyst="Chargeback spike threatening processor relationship",
            buying_dynamic="Replacement",
            no_decision_risk="Low",
            manager_insight="Must act now.",
            consequence_of_inaction="Severe",
            catalyst_time_horizon="Immediate",
            urgency_source="Customer-initiated",
        )
        assert findings.consequence_of_inaction == "Severe"
        assert findings.catalyst_time_horizon == "Immediate"
        assert findings.urgency_source == "Customer-initiated"

    def test_new_fields_default_values(self):
        from sis.agents.competitive import CompetitiveFindings

        findings = CompetitiveFindings(
            status_quo_embeddedness="Unknown",
            displacement_readiness="Unknown",
            catalyst_strength="None Identified",
            buying_dynamic="Unknown",
            no_decision_risk="Unknown",
            manager_insight="Early stage.",
        )
        assert findings.consequence_of_inaction is None
        assert findings.catalyst_time_horizon is None
        assert findings.urgency_source == "None Identified"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestCompetitiveUrgencyFields -v`
Expected: FAIL — fields don't exist yet

**Step 3: Implement the schema**

In `sis/agents/competitive.py`, add three fields to `CompetitiveFindings` after `recommended_catalyst_actions` (before `data_quality_notes`):

```python
    consequence_of_inaction: Optional[str] = Field(
        default=None,
        description="What happens if the buyer does nothing? "
        "Severe (business viability at risk), Moderate (measurable ongoing cost), "
        "Mild (growth limited but no immediate pain), or None (buyer can delay indefinitely)",
    )
    catalyst_time_horizon: Optional[str] = Field(
        default=None,
        description="When must the buyer act? "
        "Immediate (days-weeks) | Near-term (1-3 months) | "
        "Medium-term (3-6 months) | Long-term (6+ months) | No Timeline",
    )
    urgency_source: str = Field(
        default="None Identified",
        description="Customer-initiated | Seller-created | Market/External | None Identified. "
        "Choose the PRIMARY source if multiple exist.",
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestCompetitiveUrgencyFields -v`
Expected: 2 tests PASS

**Step 5: Commit**

```bash
git add sis/agents/competitive.py tests/test_urgency_schemas.py
git commit -m "feat(agent8): add consequence_of_inaction, catalyst_time_horizon, urgency_source"
```

---

## Task 6: Agent 8 (Competitive) — Add Urgency Prompt Sections

**Files:**
- Modify: `sis/agents/competitive.py:71-115` (SYSTEM_PROMPT string)

**Step 1: Add prompt sections**

In `sis/agents/competitive.py`, insert after the existing "Catalyst Types" section (after line 100) and before the NEVER rules:

```python
## Catalyst vs. Consequence: How They Differ
The switching catalyst is the EVENT that might force a decision (chargeback spike, platform migration). Catalyst strength rates how compelling that event is. Consequence of inaction rates what happens to the buyer's BUSINESS if they ignore the catalyst. These can diverge: a strong catalyst (platform migration) might have only a mild consequence (the old platform still works, just costs more).

## Consequence of Inaction
Every deal has a "do nothing" option. Assess what happens if the buyer stays with the status quo:
- Severe: business viability threatened (fraud losses accelerating, processor termination)
- Moderate: measurable ongoing cost (contract renewal at higher rate, manual review costs)
- Mild: growth limited, competitive disadvantage persists
- None: buyer can delay indefinitely with no pain
The strength of the consequence directly predicts whether the deal will close on time or slip.
If no transcript evidence exists for consequence of inaction, output null and note the gap in data_quality_notes. Do NOT infer consequence from catalyst alone.

## Urgency Source
- Customer-initiated: the buyer raised the timeline due to their own business needs
- Seller-created: the sales team introduced urgency (end-of-quarter pricing, competitive framing)
- Market/External: external event driving timeline (regulatory change, industry shift)
Note: Seller-created urgency is tracked for visibility, not as a negative signal. Choose the PRIMARY source if multiple exist.
urgency_source MUST be one of: "Customer-initiated", "Seller-created", "Market/External", "None Identified". Do not use any other values.
If catalyst_strength is "None Identified", set catalyst_time_horizon to "No Timeline".
```

**Step 2: Verify existing tests still pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add sis/agents/competitive.py
git commit -m "feat(agent8): add consequence, time horizon, and urgency source prompt sections"
```

---

## Task 7: Agent 9 (Open Discovery) — Add UrgencyAudit Schema

**Files:**
- Modify: `sis/agents/open_discovery.py:55-77` (add UrgencyAudit, update OpenDiscoveryFindings)
- Modify: `tests/test_urgency_schemas.py` (add tests)

**Step 1: Write the failing test**

Append to `tests/test_urgency_schemas.py`:

```python
class TestUrgencyAuditSchema:
    """Agent 9: UrgencyAudit sub-model."""

    def test_valid_urgency_audit(self):
        from sis.agents.open_discovery import UrgencyAudit

        ua = UrgencyAudit(
            urgency_credibility="Credible",
            assessment="Strong alignment: buyer states Q3 deadline and behavior matches",
            cross_agent_consistency="Consistent",
            consistency_detail="Agent 4 shows Aligned behavior, Agent 7 has Hard deadline, Agent 8 has Structural catalyst",
        )
        assert ua.urgency_credibility == "Credible"
        assert ua.cross_agent_consistency == "Consistent"

    def test_urgency_audit_insufficient_evidence(self):
        from sis.agents.open_discovery import UrgencyAudit

        ua = UrgencyAudit(
            urgency_credibility="Insufficient Evidence",
            assessment="No urgency signals detected across agents 4, 7, 8",
            cross_agent_consistency="Insufficient Data",
            consistency_detail="No urgency fields populated by upstream agents",
        )
        assert ua.urgency_credibility == "Insufficient Evidence"

    def test_urgency_audit_required_in_findings(self):
        from sis.agents.open_discovery import OpenDiscoveryFindings, UrgencyAudit

        findings = OpenDiscoveryFindings(
            adversarial_challenges=[],
            no_additional_signals=True,
            manager_insight="No new findings.",
            urgency_audit=UrgencyAudit(
                urgency_credibility="Insufficient Evidence",
                assessment="No signals.",
                cross_agent_consistency="Insufficient Data",
                consistency_detail="No upstream urgency data.",
            ),
        )
        assert findings.urgency_audit.urgency_credibility == "Insufficient Evidence"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestUrgencyAuditSchema -v`
Expected: FAIL — `UrgencyAudit` does not exist yet

**Step 3: Implement the schema**

In `sis/agents/open_discovery.py`, add `UrgencyAudit` class before `OpenDiscoveryFindings` (after line 53):

```python
class UrgencyAudit(BaseModel):
    """Cross-agent urgency credibility assessment."""

    urgency_credibility: str = Field(
        description="Credible | Questionable | Insufficient Evidence"
    )
    assessment: str = Field(
        description="1-2 sentences: is the urgency real? Why or why not?"
    )
    cross_agent_consistency: str = Field(
        description="Consistent | Partially Consistent | Inconsistent | Insufficient Data"
    )
    consistency_detail: str = Field(
        description="1-2 sentences explaining the consistency assessment across agents"
    )
```

Add to `OpenDiscoveryFindings` (before `data_quality_notes`):

```python
    urgency_audit: UrgencyAudit = Field(
        description="Always populated. Cross-agent urgency credibility assessment. "
        "Use urgency_credibility='Insufficient Evidence' when no urgency signals exist.",
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestUrgencyAuditSchema -v`
Expected: 3 tests PASS

**Step 5: Fix any existing tests that construct OpenDiscoveryFindings without urgency_audit**

Search for test files constructing `OpenDiscoveryFindings` — they will now fail because `urgency_audit` is required. Add the field to those test fixtures.

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short -q`
Fix any failures by adding `urgency_audit` to existing test fixtures.

**Step 6: Commit**

```bash
git add sis/agents/open_discovery.py tests/test_urgency_schemas.py
git commit -m "feat(agent9): add UrgencyAudit schema to OpenDiscoveryFindings"
```

---

## Task 8: Agent 9 (Open Discovery) — Add Urgency Audit Prompt Section

**Files:**
- Modify: `sis/agents/open_discovery.py:95-152` (SYSTEM_PROMPT string)

**Step 1: Add prompt section**

In `sis/agents/open_discovery.py`, insert after the "Adversarial Validation Process" section (after line 121) and before the "Evidence-Aware Validation" section:

```python
## Urgency Audit
Cross-reference urgency signals from upstream agents:
- Agent 4 findings.urgency_impact: Is buyer BEHAVING urgently? (urgency_behavioral_match, urgency_trend)
- Agent 7 findings.compelling_deadline: Is there a HARD deadline with a business anchor? (firmness, stability)
- Agent 8 findings: Is there a real CATALYST with painful consequences? (catalyst_strength, consequence_of_inaction, urgency_source)

Flag inconsistencies:
- Agent 8 catalyst_strength "Existential"/"Structural" but Agent 4 urgency_behavioral_match "Mismatched" = questionable
- Agent 7 firmness "Hard" but Agent 4 urgency_trend "Fading" = deadline may not stick
- Agent 8 urgency_source "Seller-created" without Agent 4 urgency_behavioral_match "Aligned" = note for visibility
- All three agents show weak/no urgency signals = not a red flag, just note "no compelling event identified"

This is NOT a negative signal by default -- just a credibility assessment for the manager.
ALWAYS populate urgency_audit. Use urgency_credibility="Insufficient Evidence" when no upstream urgency signals exist.
```

Also update the JSON output example (lines 139-151) to include `urgency_audit` in the findings object:

```json
"urgency_audit": {
    "urgency_credibility": "Credible",
    "assessment": "...",
    "cross_agent_consistency": "Consistent",
    "consistency_detail": "..."
}
```

**Step 2: Verify existing tests still pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add sis/agents/open_discovery.py
git commit -m "feat(agent9): add urgency audit prompt section"
```

---

## Task 9: Agent 10 (Synthesis) — Update Health Score + Deal Memo + NEVER Rule

**Files:**
- Modify: `sis/agents/synthesis.py:93-228` (SynthesisOutput + SYSTEM_PROMPT)
- Modify: `tests/test_urgency_schemas.py` (add tests)

**Step 1: Write the failing test**

Append to `tests/test_urgency_schemas.py`:

```python
class TestSynthesisUrgencyUpdates:
    """Agent 10: Health score rebalancing and urgency component."""

    def test_health_score_description_updated(self):
        from sis.agents.synthesis import SynthesisOutput

        # The description should reference 9 components now
        field_info = SynthesisOutput.model_fields["health_score_breakdown"]
        assert "9" in field_info.description or "nine" in field_info.description.lower()

    def test_deal_memo_max_words_updated(self):
        from sis.agents.synthesis import SynthesisOutput

        field_info = SynthesisOutput.model_fields["deal_memo"]
        assert "1200" in field_info.description
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_urgency_schemas.py::TestSynthesisUrgencyUpdates -v`
Expected: FAIL — descriptions still reference old values

**Step 3: Update SynthesisOutput schema**

In `sis/agents/synthesis.py`, update these field descriptions:

- `health_score` description: `"Overall deal health score (sum of 9 components)"`
- `health_score_breakdown` description: `"9-component health score breakdown"`
- `deal_memo` description: Update max words from 1000 to 1200 and paragraph count from 7-8 to 8-9

**Step 4: Update SYSTEM_PROMPT**

In `sis/agents/synthesis.py`, make these changes to the SYSTEM_PROMPT:

**4a. Update Health Score Components table** (lines 196-207). Replace with:

```
## Health Score Components (total = 100)

| Component | Max | Source Agent(s) |
|-----------|-----|----------------|
| Economic buyer engagement | 20 | Agent 6 |
| Stage appropriateness | 15 | Agent 1 |
| Momentum quality | 15 | Agent 4 |
| Urgency & compelling event | 10 | Agents 4, 7, 8, 9 |
| Technical path clarity | 10 | Agent 5 |
| Competitive position | 8 | Agent 8 |
| Stakeholder completeness | 10 | Agent 2 |
| Commitment quality | 8 | Agent 7 |
| Commercial clarity | 10 | Agent 3 |
```

**4b. Add urgency scoring rubric** after the Health Score Components table:

```
## Urgency & Compelling Event Scoring (10 points max)
- 9-10: Hard deadline (Agent 7 firmness=Hard, stability=Stable) + Existential/Structural catalyst (Agent 8) + Aligned urgency behavior (Agent 4) + Credible (Agent 9)
- 6-8: Firm deadline OR strong catalyst, with consistent behavioral signals across agents
- 3-5: Soft deadline or weak catalyst, OR urgency signals inconsistent across agents
- 0-2: No compelling event identified, OR Agent 9 flags urgency as "Questionable"
Stage awareness: For Stage 1-3 deals, scoring 0-2 on urgency is expected and should not be treated as a red flag.
```

**4c. Insert "Why Now?" paragraph** in the deal memo structure (between current paragraphs 4 and 5). Update paragraph numbering:

```
5. **Why Now?** — What compelling event drives this deal? Is the urgency customer-initiated or seller-created? How firm is the deadline? What happens if the buyer does nothing? (Agents 4, 7, 8, 9)
6. **Momentum & Structural Advancement** — Buying energy, next step quality, MSP status, cadence (Agents 4, 7).
7. **Technical & Integration** — Hidden blockers, integration readiness, POC status (Agent 5).
8. **Red Flags & Silence Signals** — Agent 9's adversarial challenges, what's NOT being discussed that should be, cross-agent contradictions.
9. **(If expansion deal)** **Expansion Dynamics** — Account health, renewal risk, leverage detection (Agent 0E).
```

Update the deal_memo field description to say "8-9 paragraph" and "Max 1200 words."

**4d. Add the new NEVER rule** (after existing NEVER rules at line 213):

```
- NEVER produce Commit forecast if Agent 8 consequence_of_inaction is "None" AND Agent 8 catalyst_strength is "None Identified". A deal with no pain of inaction and no catalyst is not committable.
```

**4e. Add cross-agent synthesis guidance** (after the No-Decision Risk Override at line 225):

```
## Cross-Agent Urgency Synthesis
When urgency_source (Agent 8) says "Seller-created" but meeting_initiation (Agent 4) says "Buyer-initiated", the buyer may be engaged but the urgency is artificial. Weight catalyst_strength and consequence_of_inaction more heavily than urgency_source in this case.

Agent 7 compelling_deadline with firmness "Hard" and stability "Stable" is a strong positive signal for commitment quality scoring. Cap commitment quality at 6/8 if no compelling deadline exists in stage 5+ deals.

Agent 9 urgency_audit.urgency_credibility="Questionable" should reduce the urgency component score to 0-3 regardless of what Agents 4, 7, 8 report individually.
```

**Step 5: Run all tests**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add sis/agents/synthesis.py tests/test_urgency_schemas.py
git commit -m "feat(agent10): add urgency health component, Why Now paragraph, and Commit guardrail"
```

---

## Task 10: NEVER Rule — Add Commit-Without-Compelling-Event Rule

**Files:**
- Modify: `sis/validation/never_rules.py:323-384` (add new rule function + register)
- Modify: `tests/test_never_rules.py` (add tests)

**Step 1: Write the failing test**

Append to `tests/test_never_rules.py`:

```python
from sis.validation.never_rules import check_commit_without_compelling_event


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
                    "catalyst_strength": "Structural",
                    "consequence_of_inaction": "Moderate",
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
                    "catalyst_strength": "None Identified",
                    "consequence_of_inaction": "None",
                }
            },
        }
        result = check_commit_without_compelling_event(
            agent_outputs, {"forecast_category": "Commit"}
        )
        assert result is not None
        assert result.rule_id == "NEVER_COMMIT_WITHOUT_COMPELLING_EVENT"
        assert result.severity == "error"

    def test_fails_when_no_consequence_null(self):
        agent_outputs = {
            "agent_8": {
                "findings": {
                    "catalyst_strength": "None Identified",
                    "consequence_of_inaction": None,
                }
            },
        }
        result = check_commit_without_compelling_event(
            agent_outputs, {"forecast_category": "Commit"}
        )
        assert result is not None

    def test_passes_when_catalyst_exists_but_no_consequence(self):
        """Catalyst alone is enough -- consequence is supplementary."""
        agent_outputs = {
            "agent_8": {
                "findings": {
                    "catalyst_strength": "Existential",
                    "consequence_of_inaction": None,
                }
            },
        }
        result = check_commit_without_compelling_event(
            agent_outputs, {"forecast_category": "Commit"}
        )
        assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_never_rules.py::TestCommitWithoutCompellingEvent -v`
Expected: FAIL — `check_commit_without_compelling_event` does not exist

**Step 3: Implement the rule**

In `sis/validation/never_rules.py`, add after `check_expansion_commit_relationship` (after line 320):

```python
def check_commit_without_compelling_event(
    agent_outputs: dict, synthesis_output: dict
) -> NeverRuleViolation | None:
    """Rule 7: Commit forecast requires a compelling event.

    A 'Commit' forecast requires Agent 8 to report either a real catalyst
    (not "None Identified") OR a consequence of inaction (not "None"/null).
    Deals with no pain and no catalyst are not committable.
    """
    forecast = synthesis_output.get("forecast_category", "")
    if forecast != "Commit":
        return None

    agent8 = agent_outputs.get("agent_8", {})
    findings = agent8.get("findings", {})

    catalyst_strength = findings.get("catalyst_strength", "None Identified")
    consequence = findings.get("consequence_of_inaction")

    has_catalyst = catalyst_strength not in ("None Identified", "None", "", None)
    has_consequence = consequence not in ("None", None, "")

    if not has_catalyst and not has_consequence:
        return NeverRuleViolation(
            rule_id="NEVER_COMMIT_WITHOUT_COMPELLING_EVENT",
            agent_id="agent_10",
            severity="error",
            description=(
                f"Forecast is 'Commit' but Agent 8 reports "
                f"catalyst_strength='{catalyst_strength}' and "
                f"consequence_of_inaction='{consequence}'. "
                f"No compelling event = not committable."
            ),
            context={
                "forecast": forecast,
                "catalyst_strength": catalyst_strength,
                "consequence_of_inaction": consequence,
            },
        )
    return None
```

Register the rule in `_COMMON_RULE_CHECKERS` (line 326):

```python
_COMMON_RULE_CHECKERS = [
    check_unresolved_contradictions,
    check_inferred_pricing,
    check_adversarial_challenges_exist,
    check_no_decision_risk_override,
    check_commit_without_compelling_event,  # NEW
]
```

Also add to the legacy `_RULE_CHECKERS` list and update the import in the test file.

**Step 4: Run test to verify it passes**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/test_never_rules.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add sis/validation/never_rules.py tests/test_never_rules.py
git commit -m "feat(rules): add NEVER_COMMIT_WITHOUT_COMPELLING_EVENT guardrail"
```

---

## Task 11: Update Calibration Config

**Files:**
- Modify: `sis/config.py:117-177` (_default_calibration_config)
- Modify: `config/calibration/current.yml`

**Step 1: Update _default_calibration_config in config.py**

In `sis/config.py`, update the `health_score_weights` dict in both `new_logo` and `expansion` sections:

**new_logo** (replace the weights dict):
```python
"health_score_weights": {
    "economic_buyer_engagement": 20,
    "stage_appropriateness": 15,
    "momentum_quality": 15,
    "urgency_compelling_event": 10,
    "technical_path_clarity": 10,
    "competitive_position": 8,
    "stakeholder_completeness": 10,
    "commitment_quality": 8,
    "commercial_clarity": 10,
},
```

**expansion** (replace the weights dict):
```python
"health_score_weights": {
    "account_relationship_health": 15,
    "economic_buyer_engagement": 15,
    "stage_appropriateness": 10,
    "momentum_quality": 15,
    "urgency_compelling_event": 8,
    "technical_path_clarity": 8,
    "competitive_position": 5,
    "stakeholder_completeness": 8,
    "commitment_quality": 8,
    "commercial_clarity": 8,
},
```

Note: expansion weights must also sum to 100. Current sum without urgency: 94 (15+15+10+15+8+5+8+8+8 = 92, need to verify exact current totals). Adjust as needed.

**Step 2: Update config/calibration/current.yml**

Add `urgency_compelling_event: 10` to the health_score_weights section (after line 23):

```yaml
synthesis_agent_10:
  health_score_weights:
    economic_buyer_engagement: 20
    stage_appropriateness: 15
    momentum_quality: 15
    urgency_compelling_event: 10
    technical_path_clarity: 10
    competitive_position: 8
    stakeholder_completeness: 10
    commitment_quality: 8
    commercial_clarity: 10
```

**Step 3: Verify tests pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add sis/config.py config/calibration/current.yml
git commit -m "feat(config): add urgency_compelling_event weights to calibration config"
```

---

## Task 12: Integration Smoke Test

**Files:**
- No new files — verify the full pipeline works end-to-end

**Step 1: Run the full test suite**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -m pytest tests/ -v --tb=long
```

Expected: All tests PASS. If any test fails due to changed schema (e.g., tests constructing agent output dicts without new fields), fix those fixtures.

**Step 2: Verify schema coherence**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "
from sis.agents.momentum import MomentumFindings, UrgencyImpact
from sis.agents.msp_next_steps import MSPNextStepsFindings, CompellingDeadline, NextStep
from sis.agents.competitive import CompetitiveFindings
from sis.agents.open_discovery import OpenDiscoveryFindings, UrgencyAudit
from sis.agents.synthesis import SynthesisOutput
print('All urgency schemas import successfully')
print(f'MomentumFindings fields: {list(MomentumFindings.model_fields.keys())}')
print(f'MSPNextStepsFindings fields: {list(MSPNextStepsFindings.model_fields.keys())}')
print(f'CompetitiveFindings fields: {list(CompetitiveFindings.model_fields.keys())}')
print(f'OpenDiscoveryFindings fields: {list(OpenDiscoveryFindings.model_fields.keys())}')
"
```

Expected: All imports succeed, new fields visible in model_fields

**Step 3: Verify NEVER rules**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "
from sis.validation.never_rules import check_all_never_rules
violations = check_all_never_rules(
    {'agent_8': {'findings': {'catalyst_strength': 'None Identified', 'consequence_of_inaction': 'None', 'no_decision_risk': 'High'}}},
    {'forecast_category': 'Commit', 'health_score': 80, 'contradiction_map': []},
)
print(f'Violations for Commit without compelling event: {len(violations)}')
for v in violations:
    print(f'  - {v.rule_id}: {v.description}')
"
```

Expected: At least 1 violation with `NEVER_COMMIT_WITHOUT_COMPELLING_EVENT`

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: fix any remaining test fixtures for urgency schema changes"
```

(Only if Step 1 required fixes.)

---

## Summary

| Task | Agent | What | Est. Complexity |
|------|-------|------|----------------|
| 1 | Agent 4 | UrgencyImpact schema | Low |
| 2 | Agent 4 | Urgency prompt sections | Low |
| 3 | Agent 7 | CompellingDeadline schema | Medium |
| 4 | Agent 7 | Deadline driver prompt | Low |
| 5 | Agent 8 | 3 new schema fields | Low |
| 6 | Agent 8 | Urgency prompt sections | Low |
| 7 | Agent 9 | UrgencyAudit schema | Medium |
| 8 | Agent 9 | Urgency audit prompt | Low |
| 9 | Agent 10 | Health score + deal memo + NEVER rule | High |
| 10 | Rules | NEVER_COMMIT_WITHOUT_COMPELLING_EVENT | Medium |
| 11 | Config | Calibration weights | Low |
| 12 | All | Integration smoke test | Low |

**Parallelization note:** Tasks 1-2 (Agent 4), 3-4 (Agent 7), 5-6 (Agent 8) can all be done in parallel since these agents are independent. Tasks 7-8 (Agent 9) depend on schema being finalized for agents 4/7/8. Task 9 (Agent 10) depends on all upstream agents. Task 10 (NEVER rule) can be done in parallel with Task 9. Task 11 (config) can be done anytime. Task 12 is last.

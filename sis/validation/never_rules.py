"""NEVER rules engine — hard guardrails per PRD Section 7.3.

5 rules that catch outputs violating absolute constraints.
Standalone module — does not modify sis/validation/__init__.py.
Pipeline can optionally call check_all_never_rules() after synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NeverRuleViolation:
    """A single NEVER rule violation."""

    rule_id: str
    agent_id: str
    severity: str  # "error" or "warning"
    description: str
    context: dict


def check_health_score_without_eb(
    agent_outputs: dict, synthesis_output: dict
) -> NeverRuleViolation | None:
    """Rule 1: Health > 70 requires Agent 6 EB direct engagement.

    If synthesis health_score exceeds 70, Agent 6 must show direct EB engagement
    (not just secondhand mentions).
    """
    health_score = synthesis_output.get("health_score", 0)
    if health_score <= 70:
        return None

    agent6 = agent_outputs.get("agent_6", {})
    findings = agent6.get("findings", {})

    # Check for EB direct engagement signals
    eb_identified = findings.get("eb_identified", False)
    eb_engaged = findings.get("eb_directly_engaged", findings.get("direct_engagement", False))

    if not eb_identified or not eb_engaged:
        return NeverRuleViolation(
            rule_id="NEVER_HEALTH_WITHOUT_EB",
            agent_id="agent_10",
            severity="error",
            description=(
                f"Health score {health_score} exceeds 70 but Agent 6 shows no direct "
                f"Economic Buyer engagement. EB identified: {eb_identified}, "
                f"EB directly engaged: {eb_engaged}."
            ),
            context={
                "health_score": health_score,
                "eb_identified": eb_identified,
                "eb_engaged": eb_engaged,
            },
        )
    return None


def check_commit_without_commitments(
    agent_outputs: dict, synthesis_output: dict
) -> NeverRuleViolation | None:
    """Rule 2: Commit forecast requires Agent 7 MSP + High specificity.

    A 'Commit' forecast must be backed by a mutual success plan with
    high next-step specificity from Agent 7.
    """
    forecast = synthesis_output.get("ai_forecast_category", "")
    if forecast != "Commit":
        return None

    agent7 = agent_outputs.get("agent_7", {})
    findings = agent7.get("findings", {})

    has_msp = findings.get("msp_exists", findings.get("mutual_plan_exists", False))
    specificity = findings.get("next_step_specificity", findings.get("specificity_level", ""))

    if not has_msp or specificity not in ("High", "high"):
        return NeverRuleViolation(
            rule_id="NEVER_COMMIT_WITHOUT_MSP",
            agent_id="agent_10",
            severity="error",
            description=(
                f"Forecast is 'Commit' but Agent 7 shows MSP exists: {has_msp}, "
                f"specificity: '{specificity}'. Commit requires MSP + High specificity."
            ),
            context={
                "forecast": forecast,
                "msp_exists": has_msp,
                "specificity": specificity,
            },
        )
    return None


def check_unresolved_contradictions(
    agent_outputs: dict, synthesis_output: dict
) -> NeverRuleViolation | None:
    """Rule 3: All contradiction_map entries must have resolution.

    Agent 10's contradiction map entries must each include a resolution field.
    """
    contradiction_map = synthesis_output.get("contradiction_map", [])
    if not contradiction_map:
        return None

    unresolved = []
    for i, entry in enumerate(contradiction_map):
        if isinstance(entry, dict):
            resolution = entry.get("resolution", "")
            if not resolution or resolution.strip() == "":
                unresolved.append(i)
        elif isinstance(entry, str):
            # String-format contradictions have no resolution field
            unresolved.append(i)

    if unresolved:
        return NeverRuleViolation(
            rule_id="NEVER_UNRESOLVED_CONTRADICTIONS",
            agent_id="agent_10",
            severity="error",
            description=(
                f"{len(unresolved)} of {len(contradiction_map)} contradiction(s) "
                f"have no resolution. Indices: {unresolved}."
            ),
            context={
                "total_contradictions": len(contradiction_map),
                "unresolved_indices": unresolved,
            },
        )
    return None


def check_inferred_pricing(
    agent_outputs: dict, synthesis_output: dict
) -> NeverRuleViolation | None:
    """Rule 4: Pricing numbers in Agent 3 narrative must appear in verbatim evidence.

    Any dollar amounts mentioned in the Commercial agent's narrative must be
    traceable to verbatim transcript evidence.
    """
    import re

    agent3 = agent_outputs.get("agent_3", {})
    narrative = agent3.get("narrative", "")
    evidence_list = agent3.get("evidence", [])

    if not narrative:
        return None

    # Extract dollar amounts from narrative
    price_pattern = re.compile(r"\$[\d,]+(?:\.\d{1,2})?(?:\s*[KkMmBb])?")
    narrative_prices = set(price_pattern.findall(narrative))
    if not narrative_prices:
        return None

    # Collect all text from evidence citations
    evidence_text = ""
    for ev in evidence_list:
        if isinstance(ev, dict):
            evidence_text += " " + ev.get("quote", "") + " " + ev.get("verbatim", "")
        elif isinstance(ev, str):
            evidence_text += " " + ev

    # Check each price appears in evidence
    unsupported = []
    for price in narrative_prices:
        if price not in evidence_text:
            unsupported.append(price)

    if unsupported:
        return NeverRuleViolation(
            rule_id="NEVER_INFERRED_PRICING",
            agent_id="agent_3",
            severity="error",
            description=(
                f"Pricing figures in narrative not found in verbatim evidence: "
                f"{', '.join(unsupported)}."
            ),
            context={
                "unsupported_prices": unsupported,
                "narrative_prices": list(narrative_prices),
            },
        )
    return None


def check_adversarial_challenges_exist(
    agent_outputs: dict, synthesis_output: dict
) -> NeverRuleViolation | None:
    """Rule 5: Agent 9 must produce at least 1 adversarial challenge.

    The Open Discovery / Adversarial Validator must raise at least one
    challenge to upstream agent conclusions.
    """
    agent9 = agent_outputs.get("agent_9", {})
    findings = agent9.get("findings", {})

    challenges = findings.get(
        "adversarial_challenges",
        findings.get("challenges", []),
    )

    if not challenges:
        return NeverRuleViolation(
            rule_id="NEVER_NO_ADVERSARIAL_CHALLENGES",
            agent_id="agent_9",
            severity="error",
            description="Agent 9 produced zero adversarial challenges. At least 1 required.",
            context={"challenge_count": 0},
        )
    return None


# All rule checkers in execution order
_RULE_CHECKERS = [
    check_health_score_without_eb,
    check_commit_without_commitments,
    check_unresolved_contradictions,
    check_inferred_pricing,
    check_adversarial_challenges_exist,
]


def check_all_never_rules(
    agent_outputs: dict, synthesis_output: dict
) -> list[NeverRuleViolation]:
    """Run all 5 NEVER rules and return any violations.

    Args:
        agent_outputs: dict of agent_id -> output dict (agents 1-9)
        synthesis_output: Agent 10 synthesis output dict

    Returns:
        List of NeverRuleViolation. Empty list = all rules pass.
    """
    violations = []
    for checker in _RULE_CHECKERS:
        result = checker(agent_outputs, synthesis_output)
        if result is not None:
            violations.append(result)
    return violations

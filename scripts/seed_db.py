#!/usr/bin/env python3
"""Seed database with realistic Riskified-domain mock data.

Populates all 12 DB tables with 10 accounts across 3 teams.
Deterministic UUIDs via uuid5 for idempotency.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sis.db import init_db, get_session
from sis.db.models import (
    Account, Transcript, AnalysisRun, AgentAnalysis, DealAssessment,
    ScoreFeedback, CoachingEntry, CalibrationLog, PromptVersion,
    ChatSession, ChatMessage, UsageEvent,
)

NAMESPACE = uuid.NAMESPACE_DNS


def seed_uuid(label: str) -> str:
    """Deterministic UUID from label."""
    return str(uuid.uuid5(NAMESPACE, f"sis-seed-{label}"))


def iso_date(days_ago: int) -> str:
    """ISO 8601 date N days ago."""
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def iso_now(days_ago: int = 0) -> str:
    """ISO 8601 datetime N days ago."""
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


# ── Account definitions ────────────────────────────────────────────────

ACCOUNTS = [
    {"key": "megashop_eu", "name": "MegaShop EU", "team": "Enterprise EMEA",
     "tl": "Sarah Cohen", "ae": "David Levi", "mrr": 85000.0, "ic_forecast": "Commit",
     "health": 82, "forecast": "Commit", "momentum": "Improving", "stage": 6,
     "confidence": 0.85, "divergent": False},
    {"key": "luxeretail", "name": "LuxeRetail Group", "team": "Enterprise EMEA",
     "tl": "Sarah Cohen", "ae": "Rachel Stern", "mrr": 62000.0, "ic_forecast": "Realistic",
     "health": 76, "forecast": "Realistic", "momentum": "Improving", "stage": 4,
     "confidence": 0.78, "divergent": False},
    {"key": "fastfashion", "name": "FastFashion Online", "team": "Enterprise EMEA",
     "tl": "Sarah Cohen", "ae": "David Levi", "mrr": 35000.0, "ic_forecast": "Realistic",
     "health": 55, "forecast": "Realistic", "momentum": "Stable", "stage": 3,
     "confidence": 0.62, "divergent": False},
    {"key": "homegoods", "name": "HomeGoods Direct", "team": "Enterprise EMEA",
     "tl": "Sarah Cohen", "ae": "Rachel Stern", "mrr": 28000.0, "ic_forecast": "Commit",
     "health": 38, "forecast": "At Risk", "momentum": "Declining", "stage": 3,
     "confidence": 0.55, "divergent": True},
    {"key": "urbanstyle", "name": "UrbanStyle Inc", "team": "Mid-Market NA",
     "tl": "Mike Torres", "ae": "Jenny Park", "mrr": 18000.0, "ic_forecast": "Realistic",
     "health": 62, "forecast": "Realistic", "momentum": "Improving", "stage": 3,
     "confidence": 0.70, "divergent": False},
    {"key": "techmerch", "name": "TechMerch Solutions", "team": "Mid-Market NA",
     "tl": "Mike Torres", "ae": "Chris Nguyen", "mrr": 15000.0, "ic_forecast": "Realistic",
     "health": 50, "forecast": "Realistic", "momentum": "Stable", "stage": 2,
     "confidence": 0.58, "divergent": False},
    {"key": "gadgetworld", "name": "GadgetWorld", "team": "Mid-Market NA",
     "tl": "Mike Torres", "ae": "Jenny Park", "mrr": 12000.0, "ic_forecast": "At Risk",
     "health": 35, "forecast": "At Risk", "momentum": "Declining", "stage": 1,
     "confidence": 0.40, "divergent": False},
    {"key": "shopasia", "name": "ShopAsia Pacific", "team": "Growth APAC",
     "tl": "Yuki Tanaka", "ae": "Li Wei", "mrr": 22000.0, "ic_forecast": "Realistic",
     "health": 52, "forecast": "Realistic", "momentum": "Stable", "stage": 2,
     "confidence": 0.60, "divergent": False},
    {"key": "markethub", "name": "MarketHub APAC", "team": "Growth APAC",
     "tl": "Yuki Tanaka", "ae": "Priya Sharma", "mrr": 30000.0, "ic_forecast": "Commit",
     "health": 72, "forecast": "Commit", "momentum": "Improving", "stage": 7,
     "confidence": 0.75, "divergent": False},
    {"key": "ecomtrend", "name": "EcomTrend Japan", "team": "Growth APAC",
     "tl": "Yuki Tanaka", "ae": "Li Wei", "mrr": 16000.0, "ic_forecast": "Realistic",
     "health": 42, "forecast": "At Risk", "momentum": "Declining", "stage": 2,
     "confidence": 0.48, "divergent": True},
]

STAGE_NAMES = {
    1: "Qualify", 2: "Establish Business Case", 3: "Scope",
    4: "Proposal", 5: "Negotiate", 6: "Contract", 7: "Implement",
}

AGENT_NAMES = {
    "agent_1": "Stage & Progress", "agent_2": "Relationship & Power Map",
    "agent_3": "Commercial & Risk", "agent_4": "Momentum & Engagement",
    "agent_5": "Technical Validation", "agent_6": "Economic Buyer",
    "agent_7": "MSP & Next Steps", "agent_8": "Competitive Displacement",
    "agent_9": "Open Discovery",
}

# ── Transcript templates ───────────────────────────────────────────────

def _make_transcript(acct_key: str, call_num: int, days_ago: int, ae: str) -> dict:
    """Generate a realistic Gong-style transcript."""
    buyer_names = {
        "megashop_eu": ["Hans Mueller (VP Fraud Ops)", "Claudia Fischer (Director Payments)"],
        "luxeretail": ["Marie Dupont (Head of Risk)", "Jean-Pierre Moreau (CTO)"],
        "fastfashion": ["Emma Thompson (Fraud Manager)", "Raj Patel (VP Engineering)"],
        "homegoods": ["Tom Bradley (Director Ops)", "Lisa Chen (Procurement)"],
        "urbanstyle": ["Alex Rivera (VP Digital)", "Sam Kim (Director Payments)"],
        "techmerch": ["Jordan Blake (CTO)", "Casey Morgan (Head of Risk)"],
        "gadgetworld": ["Pat Sullivan (Director IT)"],
        "shopasia": ["Mei Ling (VP Commerce)", "Akira Sato (CTO)"],
        "markethub": ["Ananya Gupta (VP Operations)", "Kenji Yamamoto (Director Risk)"],
        "ecomtrend": ["Takeshi Watanabe (Head of Fraud)", "Yui Nakamura (IT Lead)"],
    }
    buyers = buyer_names.get(acct_key, ["Buyer (Unknown)"])
    buyer = buyers[call_num % len(buyers)]

    topics = {
        1: ("discovery call", "integration requirements, current fraud solution, pain points"),
        2: ("technical deep-dive", "API integration, POC timeline, data requirements"),
        3: ("commercial discussion", "pricing model, ROI analysis, competitive comparison"),
        4: ("executive briefing", "business case, implementation timeline, budget approval"),
    }
    topic_label, topic_detail = topics.get(call_num, ("follow-up", "status update and next steps"))

    transcript_text = (
        f"[{topic_label.title()} — {iso_date(days_ago)}]\n\n"
        f"{ae} (Riskified): Thanks for joining today. I wanted to cover {topic_detail}.\n\n"
        f"{buyer}: Absolutely. We've been evaluating options and Riskified is on our shortlist.\n\n"
        f"{ae} (Riskified): Great to hear. Can you walk me through your current fraud workflow?\n\n"
        f"{buyer}: We're currently using a rules-based system that catches about 60% of fraud. "
        f"Our chargeback rate is around 0.8%, which is above our target of 0.5%.\n\n"
        f"{ae} (Riskified): That's a common challenge. Our ML models typically reduce "
        f"chargeback rates by 40-60% while approving 5-8% more legitimate orders.\n\n"
        f"{buyer}: That approval rate lift is key for us. What does the integration timeline look like?\n\n"
        f"{ae} (Riskified): Typically 4-6 weeks for a full integration. We'd start with "
        f"a parallel-run POC to validate performance against your current system.\n\n"
        f"{buyer}: We'll need to loop in our engineering team for the technical review. "
        f"Can we schedule that for next week?\n\n"
        f"{ae} (Riskified): Perfect. I'll send over the technical documentation today."
    )

    participants = [
        {"name": ae, "role": "AE", "company": "Riskified"},
        {"name": buyer.split(" (")[0], "role": buyer.split("(")[1].rstrip(")") if "(" in buyer else "Buyer",
         "company": acct_key.replace("_", " ").title()},
    ]

    return {
        "text": transcript_text,
        "date": iso_date(days_ago),
        "participants": participants,
        "duration": 30 + (call_num * 5),
    }


def _make_agent_analysis(acct: dict, agent_id: str, run_id: str) -> dict:
    """Generate plausible agent analysis data."""
    health = acct["health"]
    confidence_base = acct["confidence"]

    # Agent-specific findings
    findings_map = {
        "agent_1": {
            "inferred_stage": acct["stage"],
            "stage_name": STAGE_NAMES[acct["stage"]],
            "reasoning": f"Based on transcript signals, deal is in {STAGE_NAMES[acct['stage']]} stage.",
            "stage_signals": [f"Signal for stage {acct['stage']}"],
        },
        "agent_2": {
            "champion_identified": health > 60,
            "stakeholder_count": max(2, health // 20),
            "multithreading_depth": "deep" if health > 70 else "shallow" if health < 50 else "moderate",
            "power_map_complete": health > 65,
        },
        "agent_3": {
            "pricing_discussed": health > 50,
            "roi_framing": "strong" if health > 70 else "weak" if health < 50 else "moderate",
            "objections_identified": max(0, 3 - health // 30),
            "commercial_readiness": "high" if health > 70 else "low" if health < 45 else "medium",
        },
        "agent_4": {
            "call_cadence": "weekly" if health > 60 else "bi-weekly" if health > 40 else "irregular",
            "engagement_quality": "high" if health > 70 else "low" if health < 45 else "moderate",
            "momentum_direction": acct["momentum"],
            "last_call_days_ago": 5 if health > 60 else 15 if health > 40 else 35,
        },
        "agent_5": {
            "poc_status": "completed" if acct["stage"] >= 4 else "in_progress" if acct["stage"] >= 3 else "not_started",
            "integration_readiness": "high" if health > 70 else "low" if health < 45 else "medium",
            "technical_champion_exists": health > 55,
            "blockers": [] if health > 60 else ["Resource availability"],
        },
        "agent_6": {
            "eb_identified": health > 55,
            "eb_directly_engaged": health > 70,
            "direct_engagement": health > 70,
            "budget_status": "approved" if health > 75 else "pending" if health > 50 else "unknown",
            "decision_authority_clear": health > 65,
        },
        "agent_7": {
            "msp_exists": health > 70,
            "mutual_plan_exists": health > 70,
            "go_live_date_set": health > 75,
            "next_step_specificity": "High" if health > 75 else "Low" if health < 50 else "Medium",
            "specificity_level": "High" if health > 75 else "Low" if health < 50 else "Medium",
        },
        "agent_8": {
            "status_quo_identified": True,
            "displacement_readiness": "high" if health > 65 else "low" if health < 45 else "moderate",
            "no_decision_risk": health < 50,
            "competitor_mentioned": health < 70,
        },
        "agent_9": {
            "novel_findings": [f"Finding for {acct['name']}"],
            "adversarial_challenges": [
                {"challenge": f"Challenge for {acct['name']}: verify engagement depth",
                 "target_agent": "agent_2", "severity": "moderate"}
            ],
            "challenges": [
                {"challenge": f"Challenge for {acct['name']}: verify engagement depth",
                 "target_agent": "agent_2", "severity": "moderate"}
            ],
            "upstream_gaps": ["Gap in technical validation timeline"],
        },
    }

    evidence = [
        {"quote": f"[Call 1, {acct['ae']}]: Key quote about {agent_id.replace('_', ' ')} findings",
         "interpretation": "Supports the analysis conclusion",
         "verbatim": f"[Call 1, {acct['ae']}]: Key quote about {agent_id.replace('_', ' ')} findings"},
        {"quote": f"[Call 2, Buyer]: Relevant buyer statement",
         "interpretation": "Confirms signal strength",
         "verbatim": f"[Call 2, Buyer]: Relevant buyer statement"},
    ]

    # Vary confidence slightly by agent
    agent_num = int(agent_id.split("_")[1])
    conf = round(min(1.0, max(0.1, confidence_base + (agent_num - 5) * 0.02)), 2)

    return {
        "findings": findings_map.get(agent_id, {}),
        "evidence": evidence,
        "narrative": f"{AGENT_NAMES[agent_id]} analysis for {acct['name']}: {acct['momentum']} momentum with health indicators at {health}.",
        "confidence": {"overall": conf, "rationale": f"Based on {2 + agent_num % 3} transcript signals", "data_gaps": []},
        "sparse_data_flag": acct["stage"] < 2,
    }


def _make_health_breakdown(health: int) -> list:
    """Generate health score breakdown matching HealthScoreComponent schema.

    Output format: {component, score, max_score, rationale}
    Score is 0..max_score (integer points), not 0-100 percentage.
    """
    weights = [
        ("Buyer-Validated Pain & Commercial Clarity", 14),
        ("Momentum Quality", 13),
        ("Champion Strength", 12),
        ("Commitment Quality", 11),
        ("Economic Buyer Engagement", 11),
        ("Urgency & Compelling Event", 10),
        ("Stage Appropriateness", 9),
        ("Multi-threading & Stakeholder Coverage", 7),
        ("Competitive Position", 7),
        ("Technical Path Clarity", 6),
    ]
    breakdown = []
    for component_name, max_score in weights:
        # Generate a plausible score (0..max_score) based on overall health
        pct = min(100, max(10, health + (hash(component_name) % 20) - 10))
        score = round(pct * max_score / 100)
        breakdown.append({
            "component": component_name,
            "score": score,
            "max_score": max_score,
            "rationale": f"Scored {score}/{max_score} based on transcript evidence.",
        })
    return breakdown


def seed():
    """Main seed function."""
    init_db()

    with get_session() as session:
        # Check if already seeded
        existing = session.query(Account).count()
        if existing >= 10:
            print(f"Database already has {existing} accounts — skipping seed.")
            return

    print("Seeding database...")

    # 1. Create accounts
    account_ids = {}
    with get_session() as session:
        for acct in ACCOUNTS:
            acct_id = seed_uuid(f"account-{acct['key']}")
            account_ids[acct["key"]] = acct_id
            session.add(Account(
                id=acct_id,
                account_name=acct["name"],
                mrr_estimate=acct["mrr"],
                ic_forecast_category=acct["ic_forecast"],
                team_lead=acct["tl"],
                ae_owner=acct["ae"],
                team_name=acct["team"],
                created_at=iso_now(90),
                updated_at=iso_now(1),
            ))
    print(f"  Created {len(account_ids)} accounts")

    # 2. Create transcripts (2-4 per account)
    transcript_ids = {}  # acct_key -> [transcript_ids]
    with get_session() as session:
        for acct in ACCOUNTS:
            acct_id = account_ids[acct["key"]]
            num_transcripts = min(4, max(2, acct["stage"]))
            acct_transcripts = []
            for i in range(1, num_transcripts + 1):
                days_ago = 60 - (i * 12)
                t_data = _make_transcript(acct["key"], i, max(1, days_ago), acct["ae"])
                t_id = seed_uuid(f"transcript-{acct['key']}-{i}")
                session.add(Transcript(
                    id=t_id,
                    account_id=acct_id,
                    call_date=t_data["date"],
                    participants=json.dumps(t_data["participants"]),
                    duration_minutes=t_data["duration"],
                    raw_text=t_data["text"],
                    preprocessed_text=t_data["text"],
                    token_count=len(t_data["text"]) // 4,
                    upload_source="seed",
                    is_active=1,
                    created_at=iso_now(max(1, days_ago)),
                ))
                acct_transcripts.append(t_id)
            transcript_ids[acct["key"]] = acct_transcripts
    print(f"  Created transcripts for all accounts")

    # 3. Create analysis runs + agent analyses + deal assessments
    run_ids = {}
    with get_session() as session:
        for acct in ACCOUNTS:
            acct_id = account_ids[acct["key"]]
            run_id = seed_uuid(f"run-{acct['key']}")
            run_ids[acct["key"]] = run_id

            session.add(AnalysisRun(
                id=run_id,
                account_id=acct_id,
                started_at=iso_now(2),
                completed_at=iso_now(2),
                status="completed",
                trigger="seed",
                transcript_ids=json.dumps(transcript_ids[acct["key"]]),
                total_input_tokens=45000,
                total_output_tokens=12000,
                total_cost_usd=0.35,
                model_versions=json.dumps({
                    "agent_1": "anthropic/claude-haiku-4-5-20251001",
                    **{f"agent_{i}": "anthropic/claude-sonnet-4-20250514" for i in range(2, 10)},
                    "agent_10": "anthropic/claude-opus-4-20250514",
                }),
                prompt_config_version="v1.0",
            ))

            # 9 agent analyses (agents 1-9)
            for agent_num in range(1, 10):
                agent_id = f"agent_{agent_num}"
                analysis = _make_agent_analysis(acct, agent_id, run_id)
                aa_id = seed_uuid(f"aa-{acct['key']}-{agent_id}")
                session.add(AgentAnalysis(
                    id=aa_id,
                    analysis_run_id=run_id,
                    account_id=acct_id,
                    agent_id=agent_id,
                    agent_name=AGENT_NAMES[agent_id],
                    transcript_count_analyzed=len(transcript_ids[acct["key"]]),
                    narrative=analysis["narrative"],
                    findings=json.dumps(analysis["findings"]),
                    evidence=json.dumps(analysis["evidence"]),
                    confidence_overall=analysis["confidence"]["overall"],
                    confidence_rationale=analysis["confidence"]["rationale"],
                    data_gaps=json.dumps(analysis["confidence"]["data_gaps"]),
                    sparse_data_flag=1 if analysis["sparse_data_flag"] else 0,
                    input_tokens=5000 + agent_num * 100,
                    output_tokens=1200 + agent_num * 50,
                    cost_usd=0.03,
                    model_used="anthropic/claude-sonnet-4-20250514" if agent_num != 1
                        else "anthropic/claude-haiku-4-5-20251001",
                    retries=0,
                    status="completed",
                    created_at=iso_now(2),
                ))

            # Deal assessment
            da_id = seed_uuid(f"da-{acct['key']}")
            is_divergent = acct["divergent"]
            diverge_explanation = None
            if is_divergent:
                diverge_explanation = (
                    f"AI forecasts '{acct['forecast']}' but IC forecasts '{acct['ic_forecast']}'. "
                    f"AI rationale: Signals indicate {acct['momentum'].lower()} momentum."
                )

            session.add(DealAssessment(
                id=da_id,
                analysis_run_id=run_id,
                account_id=acct_id,
                deal_memo=f"Deal memo for {acct['name']}: {acct['momentum']} momentum, stage {acct['stage']} ({STAGE_NAMES[acct['stage']]}). Health score {acct['health']}.",
                contradiction_map=json.dumps([
                    {"agents": ["agent_2", "agent_4"], "issue": "Stakeholder engagement vs call cadence",
                     "resolution": "Engagement is deep but calls are less frequent due to async communication"},
                ]),
                inferred_stage=acct["stage"],
                stage_name=STAGE_NAMES[acct["stage"]],
                stage_confidence=round(acct["confidence"] + 0.05, 2),
                stage_reasoning=f"Transcript signals align with {STAGE_NAMES[acct['stage']]} stage indicators.",
                health_score=acct["health"],
                health_breakdown=json.dumps(_make_health_breakdown(acct["health"])),
                overall_confidence=acct["confidence"],
                confidence_rationale=f"Confidence based on {len(transcript_ids[acct['key']])} transcripts with {acct['momentum'].lower()} signals.",
                key_unknowns=json.dumps(["Budget approval timeline", "Competitive evaluation status"]),
                momentum_direction=acct["momentum"],
                momentum_trend=f"{acct['momentum']} over last 30 days",
                ai_forecast_category=acct["forecast"],
                forecast_confidence=acct["confidence"],
                forecast_rationale=f"Health {acct['health']} with {acct['momentum'].lower()} momentum supports {acct['forecast']} forecast.",
                top_positive_signals=json.dumps([
                    {"signal": "Active engagement from key stakeholders", "strength": "strong"},
                    {"signal": "Clear technical path forward", "strength": "moderate"},
                ]),
                top_risks=json.dumps([
                    {"risk": "Budget approval timeline uncertain", "severity": "medium"},
                    {"risk": "Competitive pressure from incumbent", "severity": "low"},
                ]),
                recommended_actions=json.dumps([
                    {"action": "Schedule executive briefing", "priority": "high", "owner": acct["ae"]},
                    {"action": "Send ROI analysis", "priority": "medium", "owner": acct["ae"]},
                ]),
                divergence_flag=1 if is_divergent else 0,
                divergence_explanation=diverge_explanation,
                created_at=iso_now(2),
            ))
    print(f"  Created analysis runs, agent analyses, and deal assessments")

    # 4. Score feedback (8-10 entries)
    with get_session() as session:
        feedback_data = [
            ("megashop_eu", "too_high", "off_channel", "Score doesn't reflect recent in-person meeting", True),
            ("luxeretail", "too_low", "recent_change", "New budget approval came through last week", False),
            ("fastfashion", "too_high", "stage_mismatch", "Still in early evaluation, score seems optimistic", False),
            ("homegoods", "too_high", "score_too_high", "Internal champion just left the company", False),
            ("urbanstyle", "too_low", "off_channel", "Had productive dinner meeting with CTO", True),
            ("gadgetworld", "too_low", "stakeholder_context", "New VP is very interested", False),
            ("markethub", "too_low", "recent_change", "Just signed POC agreement", False),
            ("ecomtrend", "too_high", "score_too_high", "Deal is stalling, no response in 2 weeks", False),
            ("techmerch", "too_high", "stage_mismatch", "Still doing basic discovery", False),
            ("shopasia", "too_low", "off_channel", "Active Slack channel with their team", True),
        ]
        for i, (acct_key, direction, reason, text, off_channel) in enumerate(feedback_data):
            sf_id = seed_uuid(f"feedback-{i}")
            acct_id = account_ids[acct_key]
            da_id = seed_uuid(f"da-{acct_key}")
            acct = next(a for a in ACCOUNTS if a["key"] == acct_key)
            session.add(ScoreFeedback(
                id=sf_id,
                account_id=acct_id,
                deal_assessment_id=da_id,
                author=acct["ae"],
                feedback_date=iso_now(5 + i),
                health_score_at_time=acct["health"],
                disagreement_direction=direction,
                reason_category=reason,
                free_text=text,
                off_channel_activity=1 if off_channel else 0,
                resolution="pending" if i % 3 == 0 else "accepted",
                resolution_notes=None if i % 3 == 0 else "Acknowledged and logged",
                resolved_at=None if i % 3 == 0 else iso_now(3),
                resolved_by=None if i % 3 == 0 else acct["tl"],
                created_at=iso_now(5 + i),
            ))
    print(f"  Created {len(feedback_data)} score feedback entries")

    # 5. Coaching entries (6-8 entries)
    with get_session() as session:
        coaching_data = [
            ("megashop_eu", "David Levi", "economic_buyer_engagement",
             "Strong EB engagement. Continue direct communication with VP Fraud Ops."),
            ("luxeretail", "Rachel Stern", "multithreading_stakeholder_coverage",
             "Need to multithread deeper. Identify additional technical stakeholders."),
            ("fastfashion", "David Levi", "buyer_validated_pain_commercial_clarity",
             "ROI narrative needs strengthening. Prepare quantified business case."),
            ("homegoods", "Rachel Stern", "momentum_quality",
             "Momentum declining. Re-engage with discovery questions to revive interest."),
            ("urbanstyle", "Jenny Park", "competitive_position",
             "Good competitive positioning. Highlight unique ML approach vs rules-based alternatives."),
            ("gadgetworld", "Jenny Park", "commitment_quality",
             "Very early stage. Focus on getting concrete next steps after each call."),
            ("markethub", "Priya Sharma", "technical_path_clarity",
             "Technical path is clear. Push for POC start date commitment."),
            ("ecomtrend", "Li Wei", "champion_strength",
             "No clear champion identified. Need to find and develop an internal advocate."),
        ]
        for i, (acct_key, rep, dimension, text) in enumerate(coaching_data):
            ce_id = seed_uuid(f"coaching-{i}")
            acct_id = account_ids[acct_key]
            acct = next(a for a in ACCOUNTS if a["key"] == acct_key)
            session.add(CoachingEntry(
                id=ce_id,
                account_id=acct_id,
                rep_name=rep,
                coach_name=acct["tl"],
                dimension=dimension,
                coaching_date=iso_now(10 + i * 2),
                feedback_text=text,
                dimension_score_at_time=max(20, acct["health"] - 10 + i * 3),
                health_score_at_time=acct["health"],
                incorporated=1 if i % 2 == 0 else 0,
                incorporated_at=iso_now(5) if i % 2 == 0 else None,
                incorporated_notes="Applied in next call" if i % 2 == 0 else None,
                created_at=iso_now(10 + i * 2),
            ))
    print(f"  Created {len(coaching_data)} coaching entries")

    # 6. Prompt versions (10 entries)
    with get_session() as session:
        for agent_num in range(1, 11):
            pv_id = seed_uuid(f"promptver-agent_{agent_num}")
            session.add(PromptVersion(
                id=pv_id,
                agent_id=f"agent_{agent_num}",
                version="v1.0",
                prompt_template=f"System prompt for agent {agent_num} — v1.0 baseline",
                calibration_config_version="v1.0",
                change_notes="Initial baseline prompt",
                is_active=1,
                created_at=iso_now(60),
            ))
    print(f"  Created 10 prompt versions")

    # 7. Chat sessions (2 sessions with messages)
    with get_session() as session:
        for s_num in range(1, 3):
            cs_id = seed_uuid(f"chat-session-{s_num}")
            session.add(ChatSession(
                id=cs_id,
                user_name=f"user_{s_num}",
                started_at=iso_now(3 * s_num),
                last_message_at=iso_now(3 * s_num - 1),
            ))
            messages = [
                ("user", "What's the health score for MegaShop EU?"),
                ("assistant", "MegaShop EU has a health score of 82, which is in the Commit forecast category with Improving momentum."),
                ("user", "What are the key risks?"),
                ("assistant", "The main risks are budget approval timeline uncertainty and competitive pressure from the incumbent solution."),
            ]
            for m_idx, (role, content) in enumerate(messages):
                cm_id = seed_uuid(f"chat-msg-{s_num}-{m_idx}")
                session.add(ChatMessage(
                    id=cm_id,
                    session_id=cs_id,
                    role=role,
                    content=content,
                    tokens_used=len(content) // 4,
                    model_used="anthropic/claude-sonnet-4-20250514" if role == "assistant" else None,
                    created_at=iso_now(3 * s_num - m_idx),
                ))
    print(f"  Created 2 chat sessions with messages")

    # 8. Usage events (20-30 entries)
    with get_session() as session:
        event_types = [
            "page_view", "page_view", "page_view",
            "chat_query", "chat_query",
            "brief_view", "brief_view", "brief_view",
            "feedback_submit", "feedback_submit",
            "analysis_run", "analysis_run",
            "export",
        ]
        pages = ["dashboard", "account_detail", "deal_brief", "chat", "feedback", "upload", "settings"]
        users = ["David Levi", "Rachel Stern", "Jenny Park", "Sarah Cohen", "Mike Torres"]

        for i in range(25):
            ue_id = seed_uuid(f"usage-{i}")
            et = event_types[i % len(event_types)]
            acct_key = ACCOUNTS[i % len(ACCOUNTS)]["key"]
            session.add(UsageEvent(
                id=ue_id,
                event_type=et,
                user_name=users[i % len(users)],
                account_id=account_ids[acct_key],
                page_name=pages[i % len(pages)],
                event_metadata=json.dumps({"source": "seed", "index": i}),
                created_at=iso_now(i),
            ))
    print(f"  Created 25 usage events")

    # 9. Calibration log (1 entry)
    with get_session() as session:
        cl_id = seed_uuid("calibration-log-1")
        session.add(CalibrationLog(
            id=cl_id,
            calibration_date=iso_now(30),
            config_version="v1.0",
            config_previous_version=None,
            feedback_items_reviewed=10,
            agent_prompt_changes=json.dumps({"agent_6": "Added EB engagement clarity rules"}),
            config_changes=json.dumps({"eb_absence_health_ceiling": {"before": 75, "after": 70}}),
            stage_weight_changes=None,
            golden_test_results=json.dumps({"total": 7, "passed": 7, "failed": 0}),
            tl_agreement_rates=json.dumps({"Sarah Cohen": 0.85, "Mike Torres": 0.80, "Yuki Tanaka": 0.78}),
            approved_by="VP Sales Ops",
            created_at=iso_now(30),
        ))
    print(f"  Created 1 calibration log")

    print("\nSeed complete! 10 accounts with full data across all 12 tables.")


if __name__ == "__main__":
    seed()

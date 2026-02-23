"""Export service — deal brief and forecast report export per Section 6.7.

Returns Markdown strings for POC. The spec signature is -> bytes for future
PDF support; we use -> str for now and will add PDF (weasyprint/reportlab)
post-POC.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment, AgentAnalysis
from sis.services.utils import safe_json as _safe_json


def export_deal_brief(account_id: str, format: str = "markdown") -> str:
    """Export a one-page deal brief for pipeline review prep.

    Supports three brief styles via format parameter:
      - "structured"  : Fixed template with sections (default one-pager)
      - "narrative"   : 3-5 paragraph prose + structured fields
      - "inspection"  : 3-5 inspection questions with evidence

    Args:
        account_id: The account to generate the brief for.
        format: One of "structured", "narrative", "inspection", "markdown".
                "markdown" is an alias for "structured".

    Returns:
        Markdown string of the deal brief.
    """
    if format == "markdown":
        format = "structured"

    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            return f"**Error:** Account `{account_id}` not found."

        assessment = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.desc())
            .first()
        )
        if not assessment:
            return f"**Error:** No assessment found for account `{account.account_name}`."

        health_breakdown = _safe_json(assessment.health_breakdown)
        top_risks = _safe_json(assessment.top_risks)
        top_signals = _safe_json(assessment.top_positive_signals)
        actions = _safe_json(assessment.recommended_actions)
        contradictions = _safe_json(assessment.contradiction_map)
        key_unknowns = _safe_json(assessment.key_unknowns)

        data = {
            "account_name": account.account_name,
            "mrr": account.mrr_estimate,
            "team_lead": account.team_lead,
            "ae_owner": account.ae_owner,
            "stage": assessment.inferred_stage,
            "stage_name": assessment.stage_name,
            "stage_confidence": assessment.stage_confidence,
            "health_score": assessment.health_score,
            "overall_confidence": assessment.overall_confidence,
            "confidence_rationale": assessment.confidence_rationale,
            "momentum": assessment.momentum_direction,
            "momentum_trend": assessment.momentum_trend,
            "ai_forecast": assessment.ai_forecast_category,
            "ic_forecast": account.ic_forecast_category,
            "forecast_rationale": assessment.forecast_rationale,
            "deal_memo": assessment.deal_memo,
            "health_breakdown": health_breakdown,
            "top_risks": top_risks[:3],
            "top_signals": top_signals[:3],
            "actions": actions,
            "contradictions": contradictions,
            "key_unknowns": key_unknowns,
            "created_at": assessment.created_at,
        }

    if format == "narrative":
        return _render_narrative_brief(data)
    elif format == "inspection":
        return _render_inspection_brief(data)
    else:
        return _render_structured_brief(data)


def _render_structured_brief(d: dict) -> str:
    """Structured one-pager with fixed template sections."""
    mrr_str = f"${d['mrr']:,.0f}" if d["mrr"] else "TBD"
    lines = [
        f"# Deal Brief: {d['account_name']}",
        f"*Generated {d['created_at']}*",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| MRR | {mrr_str} |",
        f"| Stage | {d['stage']} — {d['stage_name']} ({(d['stage_confidence'] or 0):.0%} conf) |",
        f"| Health Score | {d['health_score']}/100 ({(d['overall_confidence'] or 0):.0%} conf) |",
        f"| Momentum | {d['momentum']} |",
        f"| AI Forecast | {d['ai_forecast']} |",
        f"| IC Forecast | {d['ic_forecast'] or 'Not entered'} |",
        f"| Team | TL: {d['team_lead'] or 'N/A'}, AE: {d['ae_owner'] or 'N/A'} |",
        "",
    ]

    # Health breakdown
    if d["health_breakdown"]:
        lines.append("## Health Score Breakdown")
        for comp in d["health_breakdown"]:
            if isinstance(comp, dict):
                name = comp.get("component", "Unknown")
                score = comp.get("score", 0)
                max_s = comp.get("max_score", 20)
                rationale = comp.get("rationale", "")
                lines.append(f"- **{name}**: {score}/{max_s} — {rationale}")
        lines.append("")

    # Top signals
    if d["top_signals"]:
        lines.append("## Top Positive Signals")
        for s in d["top_signals"]:
            if isinstance(s, dict):
                lines.append(f"- {s.get('signal', str(s))}")
            else:
                lines.append(f"- {s}")
        lines.append("")

    # Top risks
    if d["top_risks"]:
        lines.append("## Top Risks")
        for r in d["top_risks"]:
            if isinstance(r, dict):
                severity = r.get("severity", "")
                risk = r.get("risk", str(r))
                lines.append(f"- **[{severity}]** {risk}")
            else:
                lines.append(f"- {r}")
        lines.append("")

    # Recommended actions
    if d["actions"]:
        lines.append("## Recommended Actions")
        for a in d["actions"]:
            if isinstance(a, dict):
                priority = a.get("priority", "")
                owner = a.get("owner", "TBD")
                action = a.get("action", str(a))
                lines.append(f"- **[{priority}]** {owner}: {action}")
            else:
                lines.append(f"- {a}")
        lines.append("")

    # Forecast rationale
    if d["forecast_rationale"]:
        lines.append("## Forecast Rationale")
        lines.append(d["forecast_rationale"])
        lines.append("")

    return "\n".join(lines)


def _render_narrative_brief(d: dict) -> str:
    """Narrative memo — 3-5 paragraphs + structured fields."""
    mrr_str = f"${d['mrr']:,.0f}" if d["mrr"] else "TBD"
    lines = [
        f"# Deal Memo: {d['account_name']}",
        f"*Generated {d['created_at']} | MRR: {mrr_str} | "
        f"Health: {d['health_score']}/100 | Momentum: {d['momentum']}*",
        "",
    ]

    # The deal memo IS the narrative
    if d["deal_memo"]:
        lines.append(d["deal_memo"])
        lines.append("")

    # Append structured summary
    lines.append("---")
    lines.append("")
    lines.append(f"**Stage:** {d['stage']} — {d['stage_name']} | "
                 f"**AI Forecast:** {d['ai_forecast']} | "
                 f"**IC Forecast:** {d['ic_forecast'] or 'Not entered'}")
    lines.append("")

    if d["top_risks"]:
        lines.append("**Key Risks:**")
        for r in d["top_risks"]:
            risk_text = r.get("risk", str(r)) if isinstance(r, dict) else str(r)
            lines.append(f"- {risk_text}")
        lines.append("")

    if d["actions"]:
        lines.append("**Next Actions:**")
        for a in d["actions"][:3]:
            if isinstance(a, dict):
                lines.append(f"- {a.get('owner', 'TBD')}: {a.get('action', str(a))}")
            else:
                lines.append(f"- {a}")
        lines.append("")

    return "\n".join(lines)


def _render_inspection_brief(d: dict) -> str:
    """Inspection-question format — 3-5 questions with evidence for TL review."""
    mrr_str = f"${d['mrr']:,.0f}" if d["mrr"] else "TBD"
    lines = [
        f"# Inspection Questions: {d['account_name']}",
        f"*Generated {d['created_at']} | MRR: {mrr_str} | "
        f"Health: {d['health_score']}/100 | Stage: {d['stage']} — {d['stage_name']}*",
        "",
    ]

    # Generate inspection questions from risks and contradictions
    question_num = 0

    # Questions from risks
    for r in d["top_risks"][:3]:
        question_num += 1
        if isinstance(r, dict):
            risk = r.get("risk", str(r))
            evidence = r.get("evidence", "")
            lines.append(f"### Q{question_num}: How are we addressing: {risk}?")
            if evidence:
                lines.append(f"*Evidence: {evidence}*")
        else:
            lines.append(f"### Q{question_num}: What is the status of: {r}?")
        lines.append("")

    # Questions from contradictions
    for c in d["contradictions"][:2]:
        question_num += 1
        if isinstance(c, dict):
            dimension = c.get("dimension", "")
            resolution = c.get("resolution", "")
            lines.append(f"### Q{question_num}: Conflicting signals on {dimension} — which is accurate?")
            if resolution:
                lines.append(f"*AI resolution: {resolution}*")
        lines.append("")

    # If we don't have enough questions, add from key unknowns
    for unknown in d["key_unknowns"]:
        if question_num >= 5:
            break
        question_num += 1
        lines.append(f"### Q{question_num}: {unknown}")
        lines.append("")

    # Summary footer
    lines.append("---")
    lines.append(f"**AI Forecast:** {d['ai_forecast']} | "
                 f"**IC Forecast:** {d['ic_forecast'] or 'Not entered'} | "
                 f"**Confidence:** {(d['overall_confidence'] or 0):.0%}")
    lines.append("")

    if d["forecast_rationale"]:
        lines.append(f"*{d['forecast_rationale']}*")

    return "\n".join(lines)


def export_forecast_report(team: Optional[str] = None, format: str = "markdown") -> str:
    """Export AI vs IC forecast comparison report.

    Per Section 6.7: board-presentable format showing weighted pipeline
    under both AI and IC models, by team and org.

    Args:
        team: Filter to a specific team. None = all teams.
        format: "markdown" (only option for POC).

    Returns:
        Markdown string of the forecast comparison report.
    """
    with get_session() as session:
        query = session.query(Account)
        if team:
            query = query.filter_by(team_name=team)
        accounts = query.all()

        rows = []
        for acct in accounts:
            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )
            if not latest:
                continue

            rows.append({
                "account_name": acct.account_name,
                "mrr": acct.mrr_estimate or 0,
                "team_name": acct.team_name or "Unassigned",
                "ai_forecast": latest.ai_forecast_category,
                "ic_forecast": acct.ic_forecast_category,
                "health_score": latest.health_score,
                "momentum": latest.momentum_direction,
                "divergence": bool(latest.divergence_flag),
            })

    if not rows:
        return "**No scored deals found.**"

    # Forecast category weights for weighted pipeline calculation
    category_weights = {
        "Commit": 0.90,
        "Best Case": 0.70,
        "Pipeline": 0.40,
        "Upside": 0.25,
        "At Risk": 0.15,
        "No Decision Risk": 0.05,
    }

    title = f"# Forecast Comparison Report{f' — {team}' if team else ''}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        title,
        f"*Generated {now}*",
        "",
        "## Deal-Level Comparison",
        "",
        "| Deal | MRR | Team | AI Forecast | IC Forecast | Health | Divergent |",
        "|------|-----|------|-------------|-------------|--------|-----------|",
    ]

    for r in sorted(rows, key=lambda x: -x["mrr"]):
        mrr_str = f"${r['mrr']:,.0f}"
        div_str = "!!!" if r["divergence"] else ""
        ic_str = r["ic_forecast"] or "—"
        lines.append(
            f"| {r['account_name']} | {mrr_str} | {r['team_name']} | "
            f"{r['ai_forecast']} | {ic_str} | {r['health_score']} | {div_str} |"
        )

    lines.append("")

    # Weighted pipeline summary
    ai_weighted = sum(r["mrr"] * category_weights.get(r["ai_forecast"], 0.25) for r in rows)
    ic_rows = [r for r in rows if r["ic_forecast"]]
    ic_weighted = sum(r["mrr"] * category_weights.get(r["ic_forecast"], 0.25) for r in ic_rows)
    total_mrr = sum(r["mrr"] for r in rows)

    lines.extend([
        "## Weighted Pipeline Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Pipeline MRR | ${total_mrr:,.0f} |",
        f"| AI Weighted Pipeline | ${ai_weighted:,.0f} |",
        f"| IC Weighted Pipeline | ${ic_weighted:,.0f} |",
        f"| Delta (AI - IC) | ${ai_weighted - ic_weighted:,.0f} |",
        f"| Deals with IC Forecast | {len(ic_rows)}/{len(rows)} |",
        f"| Divergent Deals | {sum(1 for r in rows if r['divergence'])} |",
        "",
    ])

    # Per-team breakdown
    teams = {}
    for r in rows:
        t = r["team_name"]
        if t not in teams:
            teams[t] = []
        teams[t].append(r)

    if len(teams) > 1:
        lines.extend([
            "## By Team",
            "",
            "| Team | Deals | MRR | AI Weighted | IC Weighted | Divergent |",
            "|------|-------|-----|-------------|-------------|-----------|",
        ])
        for t_name, t_rows in sorted(teams.items()):
            t_mrr = sum(r["mrr"] for r in t_rows)
            t_ai = sum(r["mrr"] * category_weights.get(r["ai_forecast"], 0.25) for r in t_rows)
            t_ic_rows = [r for r in t_rows if r["ic_forecast"]]
            t_ic = sum(r["mrr"] * category_weights.get(r["ic_forecast"], 0.25) for r in t_ic_rows)
            t_div = sum(1 for r in t_rows if r["divergence"])
            lines.append(
                f"| {t_name} | {len(t_rows)} | ${t_mrr:,.0f} | "
                f"${t_ai:,.0f} | ${t_ic:,.0f} | {t_div} |"
            )
        lines.append("")

    return "\n".join(lines)

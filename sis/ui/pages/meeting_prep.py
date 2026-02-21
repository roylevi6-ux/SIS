"""Meeting Prep Mode — pre-call brief per PRD P0-24.

Generates a preparation guide for upcoming prospect calls using
the latest deal assessment: topics, questions, risks, unresolved items.
"""

import streamlit as st

from sis.services.account_service import list_accounts, get_account_detail
from sis.ui.components.layout import (
    page_header, section_divider, metric_row, empty_state,
)


def render():
    page_header("Meeting Prep", "Pre-call brief for upcoming prospect meetings")

    accounts = list_accounts()
    if not accounts:
        empty_state(
            "No accounts yet",
            "📋",
            "Create one in Upload Transcript.",
        )
        return

    scored = [a for a in accounts if a.get("health_score") is not None]
    if not scored:
        empty_state(
            "No scored accounts",
            "📊",
            "Run analysis first.",
        )
        return

    names = [a["account_name"] for a in scored]
    selected = st.selectbox("Select Account", names)
    account = scored[names.index(selected)]
    detail = get_account_detail(account["id"])
    assessment = detail.get("assessment")

    if not assessment:
        st.warning(f"No assessment for {account['account_name']}.")
        return

    section_divider()

    # Header metrics
    metric_row([
        {"label": "Health Score", "value": f"{assessment['health_score']}/100"},
        {"label": "Stage", "value": f"{assessment['inferred_stage']} — {assessment['stage_name']}"},
        {"label": "Momentum", "value": assessment["momentum_direction"]},
    ])

    section_divider()

    # 1. Key Topics to Raise (from low-scoring health components)
    st.subheader("Key Topics to Raise")
    breakdown = assessment.get("health_breakdown", [])
    if isinstance(breakdown, list):
        weak = [c for c in breakdown if isinstance(c, dict) and c.get("score", 100) < c.get("max_score", 20) * 0.5]
        if weak:
            for comp in weak:
                st.markdown(f"- **{comp.get('component', 'Unknown')}** "
                           f"({comp.get('score', 0)}/{comp.get('max_score', 20)}): "
                           f"{comp.get('rationale', '')}")
        else:
            st.markdown("No weak components identified.")

    # 2. Questions to Ask (from key unknowns + risk flags)
    st.subheader("Questions to Ask")
    unknowns = assessment.get("key_unknowns", [])
    risks = assessment.get("top_risks", [])
    questions = []
    for u in unknowns:
        questions.append(f"Clarify: {u}")
    for r in risks[:3]:
        if isinstance(r, dict):
            questions.append(f"Probe risk: {r.get('risk', str(r))}")
        else:
            questions.append(f"Probe: {r}")

    if questions:
        for q in questions:
            st.markdown(f"- {q}")
    else:
        st.markdown("No specific questions identified from the analysis.")

    # 3. Risks to Watch
    st.subheader("Risks to Watch During Call")
    if risks:
        for r in risks:
            if isinstance(r, dict):
                sev = r.get("severity", "")
                risk_text = r.get("risk", str(r))
                st.markdown(f"- **[{sev}]** {risk_text}")
            else:
                st.markdown(f"- {r}")
    else:
        st.markdown("No significant risks flagged.")

    # 4. Recommended Actions
    st.subheader("Actions to Follow Up On")
    actions = assessment.get("recommended_actions", [])
    if actions:
        for a in actions:
            if isinstance(a, dict):
                st.markdown(f"- **{a.get('owner', 'TBD')}**: {a.get('action', str(a))}")
            else:
                st.markdown(f"- {a}")
    else:
        st.markdown("No pending actions.")

    # 5. Positive signals to leverage
    st.subheader("Positive Signals to Leverage")
    signals = assessment.get("top_positive_signals", [])
    if signals:
        for s in signals[:3]:
            if isinstance(s, dict):
                st.markdown(f"- {s.get('signal', str(s))}")
            else:
                st.markdown(f"- {s}")
    else:
        st.markdown("No strong positive signals detected.")

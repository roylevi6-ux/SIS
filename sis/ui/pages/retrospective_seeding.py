"""Retrospective Seeding — batch pipeline runs on historical deals per PRD Sec 7.11.

Tags accounts with known outcomes (won/lost/stalled), runs pipeline,
and compares AI health scores against actual outcomes for calibration.
"""

import streamlit as st

from sis.services.account_service import list_accounts
from sis.ui.components.layout import page_header, section_divider, metric_row, empty_state


OUTCOME_OPTIONS = ["Unknown", "Won", "Lost", "Stalled"]


def render():
    page_header("Retrospective Seeding", "Tag historical deal outcomes and compare against AI assessments")

    accounts = list_accounts()
    if not accounts:
        empty_state(
            "No accounts in the system",
            "\U0001f4c1",
            "Upload transcripts and run analysis first.",
        )
        return

    # Initialize outcome store in session state
    if "retro_outcomes" not in st.session_state:
        st.session_state.retro_outcomes = {}

    # --- Outcome Tagging ---
    st.subheader("Tag Account Outcomes")
    st.caption("Set known outcomes for closed deals to evaluate AI accuracy")

    scored = [a for a in accounts if a.get("health_score") is not None]
    unscored = [a for a in accounts if a.get("health_score") is None]

    if scored:
        for a in scored:
            current_outcome = st.session_state.retro_outcomes.get(a["id"], "Unknown")
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(a["account_name"])
            with col2:
                outcome = st.selectbox(
                    "Outcome",
                    OUTCOME_OPTIONS,
                    index=OUTCOME_OPTIONS.index(current_outcome),
                    key=f"retro_outcome_{a['id']}",
                    label_visibility="collapsed",
                )
            with col3:
                if st.button("Set", key=f"retro_set_{a['id']}"):
                    st.session_state.retro_outcomes[a["id"]] = outcome
                    st.toast(f"Set {a['account_name']} → {outcome}")
    else:
        empty_state(
            "No scored accounts",
            "\U0001f3af",
            "Run analysis on accounts first.",
        )

    section_divider()

    # --- Results Comparison ---
    st.subheader("AI Score vs Known Outcome")

    tagged = {
        aid: outcome
        for aid, outcome in st.session_state.retro_outcomes.items()
        if outcome != "Unknown"
    }

    if not tagged:
        empty_state(
            "Tag account outcomes above to see accuracy comparison",
            "\U0001f50d",
        )
        return

    # Build comparison table
    comparison = []
    for a in scored:
        outcome = tagged.get(a["id"])
        if outcome:
            comparison.append({
                "Account": a["account_name"],
                "Health Score": a["health_score"],
                "AI Forecast": a.get("ai_forecast_category", "N/A"),
                "Known Outcome": outcome,
                "Aligned": _check_alignment(a["health_score"], outcome),
            })

    if comparison:
        st.dataframe(comparison, use_container_width=True, hide_index=True)

        # --- Accuracy Summary ---
        section_divider()
        st.subheader("Accuracy Summary")

        won_deals = [c for c in comparison if c["Known Outcome"] == "Won"]
        lost_deals = [c for c in comparison if c["Known Outcome"] == "Lost"]

        won_value = "N/A"
        if won_deals:
            won_high = sum(1 for d in won_deals if d["Health Score"] >= 60)
            pct = won_high / len(won_deals) * 100
            won_value = f"{pct:.0f}%"

        lost_value = "N/A"
        if lost_deals:
            lost_low = sum(1 for d in lost_deals if d["Health Score"] < 50)
            pct = lost_low / len(lost_deals) * 100
            lost_value = f"{pct:.0f}%"

        aligned = sum(1 for c in comparison if c["Aligned"] == "Yes")
        total = len(comparison)
        alignment_value = f"{aligned}/{total}"

        metric_row([
            {"label": "Won Deals with Score >= 60", "value": won_value},
            {"label": "Lost Deals with Score < 50", "value": lost_value},
            {"label": "Overall Alignment", "value": alignment_value},
        ])

        # Export for calibration
        section_divider()
        export_lines = ["Account,Health Score,AI Forecast,Known Outcome,Aligned"]
        for c in comparison:
            export_lines.append(
                f"{c['Account']},{c['Health Score']},{c['AI Forecast']},{c['Known Outcome']},{c['Aligned']}"
            )
        csv_data = "\n".join(export_lines)
        st.download_button(
            "Export for Calibration Review",
            data=csv_data,
            file_name="retrospective_comparison.csv",
            mime="text/csv",
        )


def _check_alignment(health_score: int, outcome: str) -> str:
    """Check if AI health score aligns with known outcome."""
    if outcome == "Won" and health_score >= 60:
        return "Yes"
    if outcome == "Lost" and health_score < 50:
        return "Yes"
    if outcome == "Stalled" and 40 <= health_score <= 65:
        return "Yes"
    if outcome in ("Won", "Lost", "Stalled"):
        return "No"
    return "N/A"

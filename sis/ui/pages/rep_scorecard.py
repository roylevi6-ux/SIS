"""Rep Scorecard — behavioral dimension scoring per PRD P0-22.

Shows 4 behavioral dimensions per rep with team-level aggregates
and per-account drill-down.
"""

import streamlit as st

from sis.services.rep_scorecard_service import get_rep_scorecard, DIMENSIONS


def _dimension_color(score: float | None) -> str:
    if score is None:
        return "#6b7280"
    if score >= 70:
        return "#22c55e"
    if score >= 45:
        return "#f59e0b"
    return "#ef4444"


def render():
    st.title("Rep Performance Scorecard")
    st.caption("Behavioral dimensions: stakeholder engagement, objection handling, commercial progression, next-step setting")

    scorecards = get_rep_scorecard()

    if not scorecards:
        st.info("No rep data available. Run analysis on accounts first.")
        return

    # Rep filter
    rep_names = ["All Reps"] + [s["rep_name"] for s in scorecards]
    selected_rep = st.selectbox("Filter by Rep", rep_names, key="rep_scorecard_filter")
    if selected_rep != "All Reps":
        scorecards = [s for s in scorecards if s["rep_name"] == selected_rep]

    # --- Team-level aggregate ---
    all_scored = [s for s in scorecards if s["overall_score"] is not None]
    if all_scored and selected_rep == "All Reps":
        st.subheader("Team Aggregate")
        team_dims = {}
        for dim in DIMENSIONS:
            vals = [s["dimensions"][dim] for s in all_scored if s["dimensions"].get(dim) is not None]
            team_dims[dim] = round(sum(vals) / len(vals), 1) if vals else None

        cols = st.columns(len(DIMENSIONS))
        for i, dim in enumerate(DIMENSIONS):
            val = team_dims[dim]
            color = _dimension_color(val)
            with cols[i]:
                st.markdown(
                    f'<div style="text-align:center;padding:12px;border-radius:8px;'
                    f'background:{color}15;border:1px solid {color}">'
                    f'<div style="font-size:11px;color:#666">{dim}</div>'
                    f'<div style="font-size:28px;font-weight:bold;color:{color}">'
                    f'{val:.0f}</div></div>' if val is not None else
                    f'<div style="text-align:center;padding:12px;border-radius:8px;'
                    f'background:#f3f4f6;border:1px solid #d1d5db">'
                    f'<div style="font-size:11px;color:#666">{dim}</div>'
                    f'<div style="font-size:28px;color:#9ca3af">--</div></div>',
                    unsafe_allow_html=True,
                )
        st.divider()

    # --- Per-rep cards ---
    for sc in scorecards:
        with st.container(border=True):
            header_col, score_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"### {sc['rep_name']}")
                st.caption(f"{sc['scored_accounts']}/{sc['total_accounts']} accounts scored")
            with score_col:
                overall = sc["overall_score"]
                color = _dimension_color(overall)
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="font-size:11px;color:#666">Overall</div>'
                    f'<div style="font-size:32px;font-weight:bold;color:{color}">'
                    f'{overall:.0f}</div></div>' if overall is not None else
                    f'<div style="text-align:center;color:#9ca3af">--</div>',
                    unsafe_allow_html=True,
                )

            # Dimension scores
            dim_cols = st.columns(len(DIMENSIONS))
            for i, dim in enumerate(DIMENSIONS):
                val = sc["dimensions"].get(dim)
                color = _dimension_color(val)
                with dim_cols[i]:
                    st.markdown(
                        f'<div style="text-align:center;padding:8px;border-radius:6px;'
                        f'background:{color}10">'
                        f'<div style="font-size:10px;color:#888">{dim}</div>'
                        f'<div style="font-size:22px;font-weight:bold;color:{color}">'
                        f'{val:.0f}</div></div>' if val is not None else
                        f'<div style="text-align:center;padding:8px">'
                        f'<div style="font-size:10px;color:#888">{dim}</div>'
                        f'<div style="color:#9ca3af">--</div></div>',
                        unsafe_allow_html=True,
                    )

            # Expandable per-account detail
            scored_accounts = [a for a in sc["accounts"] if a.get("scored")]
            if scored_accounts:
                with st.expander(f"Account Details ({len(scored_accounts)})"):
                    for acct in scored_accounts:
                        acct_cols = st.columns([2] + [1] * len(DIMENSIONS))
                        with acct_cols[0]:
                            if st.button(acct["account_name"], key=f"rep_acct_{sc['rep_name']}_{acct['account_id']}"):
                                st.session_state["selected_account_id"] = acct["account_id"]
                                st.rerun()
                            st.caption(f"Health: {acct.get('health_score', '--')}")
                        for j, dim in enumerate(DIMENSIONS):
                            with acct_cols[j + 1]:
                                val = acct.get("dimensions", {}).get(dim)
                                color = _dimension_color(val)
                                st.markdown(
                                    f'<span style="color:{color};font-weight:bold">'
                                    f'{val:.0f}</span>' if val is not None else "--",
                                    unsafe_allow_html=True,
                                )

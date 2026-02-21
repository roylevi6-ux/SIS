"""Rep Scorecard — behavioral dimension scoring per PRD P0-22.

Shows 4 behavioral dimensions per rep with team-level aggregates
and per-account drill-down.
"""

from __future__ import annotations

import hashlib
import html

import streamlit as st

from sis.services.rep_scorecard_service import get_rep_scorecard, DIMENSIONS
from sis.services import coaching_service
from sis.ui.components.layout import (
    page_header, section_divider, status_badge, empty_state,
)
from sis.ui.theme import Colors, Typography


def render():
    page_header(
        "Rep Performance Scorecard",
        "Behavioral dimensions: stakeholder engagement, objection handling, commercial progression, next-step setting",
    )

    scorecards = get_rep_scorecard()

    if not scorecards:
        empty_state(
            "No rep data available",
            "📊",
            "Run analysis on accounts first.",
        )
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
            color = Colors.status_color(val)
            with cols[i]:
                st.markdown(
                    f'<div style="text-align:center;padding:12px;border-radius:8px;'
                    f'background:{Colors.with_alpha(color)};border:1px solid {color}">'
                    f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">{dim}</div>'
                    f'<div style="font-size:28px;font-weight:bold;color:{color}">'
                    f'{val:.0f}</div></div>' if val is not None else
                    f'<div style="text-align:center;padding:12px;border-radius:8px;'
                    f'background:{Colors.BG_SECONDARY};border:1px solid {Colors.BORDER}">'
                    f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">{dim}</div>'
                    f'<div style="font-size:28px;color:{Colors.NEUTRAL}">--</div></div>',
                    unsafe_allow_html=True,
                )
        section_divider()

    # --- Per-rep cards ---
    for sc in scorecards:
        with st.container(border=True):
            header_col, score_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"### {sc['rep_name']}")
                st.caption(f"{sc['scored_accounts']}/{sc['total_accounts']} accounts scored")
            with score_col:
                overall = sc["overall_score"]
                color = Colors.status_color(overall)
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">Overall</div>'
                    f'<div style="font-size:32px;font-weight:bold;color:{color}">'
                    f'{overall:.0f}</div></div>' if overall is not None else
                    f'<div style="text-align:center;color:{Colors.NEUTRAL}">--</div>',
                    unsafe_allow_html=True,
                )

            # Dimension scores
            dim_cols = st.columns(len(DIMENSIONS))
            for i, dim in enumerate(DIMENSIONS):
                val = sc["dimensions"].get(dim)
                color = Colors.status_color(val)
                with dim_cols[i]:
                    st.markdown(
                        f'<div style="text-align:center;padding:8px;border-radius:6px;'
                        f'background:{Colors.with_alpha(color)}">'
                        f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">{dim}</div>'
                        f'<div style="font-size:22px;font-weight:bold;color:{color}">'
                        f'{val:.0f}</div></div>' if val is not None else
                        f'<div style="text-align:center;padding:8px">'
                        f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">{dim}</div>'
                        f'<div style="color:{Colors.NEUTRAL}">--</div></div>',
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
                                color = Colors.status_color(val)
                                st.markdown(
                                    f'<span style="color:{color};font-weight:bold">'
                                    f'{val:.0f}</span>' if val is not None else "--",
                                    unsafe_allow_html=True,
                                )

            # --- Coaching Log ---
            rep_key = hashlib.md5(sc["rep_name"].encode()).hexdigest()[:12]
            coaching_entries = coaching_service.list_coaching(rep_name=sc["rep_name"])
            with st.expander(f"Coaching Log ({len(coaching_entries)})"):
                # Submit form
                st.markdown("**Log Coaching Feedback**")
                all_accounts = sc["accounts"]
                acct_options = {a["account_name"]: a["account_id"] for a in all_accounts}
                if not acct_options:
                    st.info("No accounts for this rep.")
                else:
                    form_key = f"coaching_form_{rep_key}"
                    with st.form(form_key):
                        sel_acct_name = st.selectbox(
                            "Account",
                            list(acct_options.keys()),
                            key=f"coaching_acct_{rep_key}",
                        )
                        sel_dimension = st.selectbox(
                            "Dimension",
                            DIMENSIONS,
                            key=f"coaching_dim_{rep_key}",
                        )
                        coach_name = st.text_input(
                            "Coach Name",
                            key=f"coaching_coach_{rep_key}",
                        )
                        feedback_text = st.text_area(
                            "Coaching Feedback",
                            key=f"coaching_text_{rep_key}",
                        )
                        submitted = st.form_submit_button("Submit Coaching")
                        if submitted:
                            if not coach_name.strip():
                                st.error("Coach name is required.")
                            elif not feedback_text.strip():
                                st.error("Feedback text is required.")
                            else:
                                try:
                                    coaching_service.submit_coaching(
                                        account_id=acct_options[sel_acct_name],
                                        rep_name=sc["rep_name"],
                                        coach_name=coach_name.strip(),
                                        dimension=sel_dimension,
                                        feedback_text=feedback_text,
                                    )
                                    st.success("Coaching entry saved.")
                                    st.rerun()
                                except ValueError as e:
                                    st.error(str(e))

                # History
                if coaching_entries:
                    st.markdown("**History**")
                    for entry in coaching_entries:
                        entry_key = entry["id"]
                        inc_badge = (
                            status_badge("Incorporated", "success")
                            if entry["incorporated"]
                            else status_badge("Pending", "warning")
                        )
                        dim_score = entry["dimension_score_at_time"]
                        dim_label = f" | Score: {dim_score}" if dim_score is not None else ""
                        escaped_text = html.escape(entry["feedback_text"])
                        escaped_coach = html.escape(entry["coach_name"])
                        escaped_acct = html.escape(entry["account_name"])
                        st.markdown(
                            f'<div style="padding:8px;margin:4px 0;border-left:3px solid {Colors.ACCENT};'
                            f'background:{Colors.BG_SECONDARY};border-radius:0 6px 6px 0">'
                            f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">'
                            f'{html.escape(entry["dimension"])} | {escaped_acct}{dim_label} | '
                            f'{html.escape(entry["coaching_date"][:10])} | Coach: {escaped_coach} | '
                            f'{inc_badge}</div>'
                            f'<div style="margin-top:4px">{escaped_text}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if not entry["incorporated"]:
                            inc_col1, inc_col2 = st.columns([3, 1])
                            with inc_col1:
                                notes = st.text_input(
                                    "Notes",
                                    key=f"inc_notes_{rep_key}_{entry_key}",
                                    label_visibility="collapsed",
                                    placeholder="Incorporation notes (optional)",
                                )
                            with inc_col2:
                                if st.button(
                                    "Mark Incorporated",
                                    key=f"inc_btn_{rep_key}_{entry_key}",
                                ):
                                    coaching_service.mark_incorporated(
                                        entry["id"],
                                        notes=notes if notes.strip() else None,
                                    )
                                    st.rerun()
                        elif entry["incorporated_notes"]:
                            st.caption(f"Notes: {html.escape(entry['incorporated_notes'])}")
                else:
                    st.info("No coaching entries yet.")

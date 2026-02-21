"""Cost Monitor — LLM cost tracking per Technical Architecture Section 3.5."""

from __future__ import annotations

import streamlit as st

from sis.db.session import get_session
from sis.db.models import AnalysisRun
from sis.ui.components.layout import (
    page_header, section_divider, metric_row, status_badge, empty_state,
)
from sis.ui.theme import Colors


def render():
    page_header("Cost Monitor", "Track LLM usage and costs across pipeline runs")

    # Load data within session scope and convert to dicts
    with get_session() as session:
        rows = (
            session.query(AnalysisRun)
            .order_by(AnalysisRun.started_at.desc())
            .limit(50)
            .all()
        )
        runs = [
            {
                "id": r.id,
                "account_id": r.account_id,
                "status": r.status,
                "total_cost_usd": r.total_cost_usd or 0,
                "total_input_tokens": r.total_input_tokens or 0,
                "total_output_tokens": r.total_output_tokens or 0,
                "started_at": r.started_at,
            }
            for r in rows
        ]

    if not runs:
        empty_state(
            "No analysis runs yet",
            "\U0001f4ca",
            "Run an analysis pipeline to start tracking costs.",
        )
        return

    # Summary
    total_cost = sum(r["total_cost_usd"] for r in runs)
    total_input = sum(r["total_input_tokens"] for r in runs)
    total_output = sum(r["total_output_tokens"] for r in runs)

    metric_row([
        {"label": "Total Runs", "value": len(runs)},
        {"label": "Total Cost", "value": f"${total_cost:.2f}"},
        {"label": "Total Input Tokens", "value": f"{total_input:,}"},
        {"label": "Total Output Tokens", "value": f"{total_output:,}"},
    ])

    # Monthly projection
    avg_cost = total_cost / len(runs)
    st.markdown(
        f"**Average cost per run:** ${avg_cost:.4f} | "
        f"**Monthly projection (400 runs):** ${avg_cost * 400:.2f}"
    )

    section_divider()

    # Per-run table
    st.subheader("Recent Runs")
    for run in runs:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.caption("Account")
                st.markdown(f"`{run['account_id'][:8]}...`")
            with c2:
                st.caption("Status")
                status = run["status"]
                if status == "completed":
                    badge_status = "success"
                elif status == "partial":
                    badge_status = "warning"
                else:
                    badge_status = "danger"
                st.markdown(
                    status_badge(status, badge_status),
                    unsafe_allow_html=True,
                )
            with c3:
                st.caption("Cost")
                st.markdown(f"${run['total_cost_usd']:.4f}")
            with c4:
                st.caption("Tokens")
                st.markdown(f"{run['total_input_tokens']:,} in / {run['total_output_tokens']:,} out")

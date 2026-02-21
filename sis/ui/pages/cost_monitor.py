"""Cost Monitor — LLM cost tracking per Technical Architecture Section 3.5."""

import streamlit as st

from sis.db.session import get_session
from sis.db.models import AnalysisRun


def render():
    st.title("Cost Monitor")
    st.caption("Track LLM usage and costs across pipeline runs")

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
        st.info("No analysis runs yet.")
        return

    # Summary
    total_cost = sum(r["total_cost_usd"] for r in runs)
    total_input = sum(r["total_input_tokens"] for r in runs)
    total_output = sum(r["total_output_tokens"] for r in runs)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Runs", len(runs))
    with col2:
        st.metric("Total Cost", f"${total_cost:.2f}")
    with col3:
        st.metric("Total Input Tokens", f"{total_input:,}")
    with col4:
        st.metric("Total Output Tokens", f"{total_output:,}")

    # Monthly projection
    avg_cost = total_cost / len(runs)
    st.markdown(
        f"**Average cost per run:** ${avg_cost:.4f} | "
        f"**Monthly projection (400 runs):** ${avg_cost * 400:.2f}"
    )

    st.divider()

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
                color = "#22c55e" if status == "completed" else "#f59e0b" if status == "partial" else "#ef4444"
                st.markdown(f'<span style="color:{color}">{status}</span>', unsafe_allow_html=True)
            with c3:
                st.caption("Cost")
                st.markdown(f"${run['total_cost_usd']:.4f}")
            with c4:
                st.caption("Tokens")
                st.markdown(f"{run['total_input_tokens']:,} in / {run['total_output_tokens']:,} out")

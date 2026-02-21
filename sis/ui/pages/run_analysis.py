"""Run Analysis — trigger pipeline + progress view per PRD P0-2."""

from __future__ import annotations

import streamlit as st

from sis.services.account_service import list_accounts
from sis.services.transcript_service import list_transcripts
from sis.services.user_action_log_service import log_action, ACTION_ANALYSIS_RUN
from sis.ui.components.layout import page_header, empty_state


def render():
    page_header("Run Analysis")

    accounts = list_accounts()
    if not accounts:
        empty_state(
            "No accounts yet",
            "\U0001f4e5",
            "Upload transcripts first.",
        )
        return

    account_names = [a["account_name"] for a in accounts]
    account_ids = [a["id"] for a in accounts]

    selected_name = st.selectbox("Select Account", account_names)
    idx = account_names.index(selected_name)
    account_id = account_ids[idx]

    transcripts = list_transcripts(account_id)
    st.info(f"{len(transcripts)} active transcripts for this account")

    if not transcripts:
        st.warning("No transcripts. Upload at least one transcript first.")
        return

    if st.button("Run Full 10-Agent Pipeline", type="primary", use_container_width=True):
        progress_bar = st.progress(0, text="Starting pipeline...")
        status_text = st.empty()

        def progress_callback(step_name: str, current: int, total: int):
            progress_bar.progress(current / total, text=f"Step {current}/{total}: {step_name}")
            status_text.markdown(f"**Running:** {step_name}")

        try:
            from sis.services.analysis_service import analyze_account

            log_action(
                ACTION_ANALYSIS_RUN,
                action_detail=f"Running 10-agent pipeline for {selected_name}",
                account_id=account_id,
                account_name=selected_name,
                page_name="Run Analysis",
            )
            result = analyze_account(
                account_id=account_id,
                progress_callback=progress_callback,
            )

            progress_bar.progress(1.0, text="Complete!")
            status_text.empty()

            if result["status"] == "completed":
                st.success(
                    f"Analysis complete! "
                    f"{result['agents_completed']}/{result['agents_total']} agents, "
                    f"${result['total_cost_usd']:.4f}, "
                    f"{result['wall_clock_seconds']}s"
                )
            elif result["status"] == "partial":
                st.warning(
                    f"Partial completion: {result['agents_completed']}/{result['agents_total']} agents. "
                    f"Errors: {len(result['errors'])}"
                )
                for err in result["errors"]:
                    st.error(err)
            else:
                st.error(f"Pipeline failed: {result['errors']}")

            if result.get("validation_warnings"):
                with st.expander(f"Validation Warnings ({len(result['validation_warnings'])})"):
                    for w in result["validation_warnings"]:
                        st.warning(w)

            st.session_state["selected_account_id"] = account_id
            if st.button("View Deal Detail →"):
                st.rerun()

        except Exception as e:
            progress_bar.progress(0, text="Failed")
            st.error(f"Pipeline error: {e}")

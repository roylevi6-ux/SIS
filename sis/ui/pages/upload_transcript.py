"""Upload Transcript — account creation + transcript upload per PRD P0-4, P0-1."""

import streamlit as st

from sis.services.account_service import create_account, list_accounts
from sis.services.transcript_service import upload_transcript, list_transcripts
from sis.ui.components.layout import page_header, empty_state


def render():
    page_header("Upload Transcript")

    tab1, tab2 = st.tabs(["Upload to Existing Account", "Create New Account"])

    with tab2:
        st.subheader("Create New Account")
        with st.form("create_account"):
            name = st.text_input("Account Name *")
            mrr = st.number_input("MRR Estimate ($)", min_value=0.0, value=0.0, step=1000.0)
            team_lead = st.text_input("Team Lead")
            ae_owner = st.text_input("AE Owner")
            team_name = st.text_input("Team Name")

            if st.form_submit_button("Create Account"):
                if not name:
                    st.error("Account name is required.")
                else:
                    acct = create_account(
                        name=name,
                        mrr=mrr if mrr > 0 else None,
                        team_lead=team_lead or None,
                        ae_owner=ae_owner or None,
                        team=team_name or None,
                    )
                    st.success(f"Account created: {acct.account_name} (ID: {acct.id[:8]}...)")
                    st.rerun()

    with tab1:
        st.subheader("Upload Transcript")

        accounts = list_accounts()
        if not accounts:
            empty_state(
                "No accounts yet",
                "\U0001f4c1",
                "Create one first using the tab above.",
            )
            return

        account_names = [a["account_name"] for a in accounts]
        account_ids = [a["id"] for a in accounts]

        selected_name = st.selectbox("Select Account", account_names)
        idx = account_names.index(selected_name)
        account_id = account_ids[idx]

        existing = list_transcripts(account_id)
        if existing:
            st.caption(f"{len(existing)} active transcripts for this account")

        with st.form("upload_transcript"):
            call_date = st.date_input("Call Date")
            duration = st.number_input("Duration (minutes)", min_value=0, value=30, step=5)
            raw_text = st.text_area(
                "Paste Transcript Text",
                height=300,
                placeholder="Paste the full transcript text here...",
            )

            if st.form_submit_button("Upload"):
                if not raw_text or len(raw_text.strip()) < 50:
                    st.error("Transcript must be at least 50 characters.")
                else:
                    transcript = upload_transcript(
                        account_id=account_id,
                        raw_text=raw_text,
                        call_date=str(call_date),
                        duration_minutes=duration if duration > 0 else None,
                    )
                    st.success(
                        f"Transcript uploaded ({transcript.token_count} estimated tokens). "
                        f"ID: {transcript.id[:8]}..."
                    )
                    st.rerun()

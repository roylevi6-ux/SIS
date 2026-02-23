"""Upload Transcript — Google Drive import + manual upload per PRD P0-4, P0-1."""

from __future__ import annotations

import streamlit as st

from sis.services.account_service import create_account, list_accounts
from sis.services.transcript_service import upload_transcript, list_transcripts
from sis.services.gdrive_service import (
    validate_drive_path,
    list_account_folders,
    get_recent_calls_info,
    download_and_parse_calls,
    upload_calls_to_db,
)
from sis.services.user_action_log_service import log_action, ACTION_TRANSCRIPT_UPLOAD
from sis.ui.components.layout import page_header, empty_state
from sis.config import GOOGLE_DRIVE_TRANSCRIPTS_PATH


def render():
    page_header("Upload Transcript")

    tab1, tab2, tab3 = st.tabs([
        "📁 Import from Google Drive",
        "📝 Upload Text (Manual)",
        "➕ Create New Account",
    ])

    with tab1:
        _render_drive_import()

    with tab2:
        _render_manual_upload()

    with tab3:
        _render_create_account()


# ── Tab 1: Google Drive Import ─────────────────────────────────────────────


def _render_drive_import():
    st.subheader("Import from Google Drive")

    # Step 1: Configure drive path
    default_path = GOOGLE_DRIVE_TRANSCRIPTS_PATH or ""
    drive_path = st.text_input(
        "Google Drive Folder Path",
        value=st.session_state.get("gdrive_path", default_path),
        placeholder="~/Library/CloudStorage/GoogleDrive-you@company.com/My Drive/Transcripts",
        help="Local path to the Google Drive folder containing account sub-folders with Gong exports",
    )

    if not drive_path:
        st.info(
            "Enter the local path to your Google Drive folder that contains "
            "account sub-folders with Gong JSON transcripts."
        )
        return

    # Validate path
    is_valid, message = validate_drive_path(drive_path)
    if not is_valid:
        st.error(message)
        return

    st.session_state["gdrive_path"] = drive_path
    st.caption(f"✅ {message}")

    # Step 2: List account folders
    with st.spinner("Scanning account folders..."):
        accounts = list_account_folders(drive_path)

    if not accounts:
        empty_state("No account folders found", "📂", "Check that the folder contains sub-folders.")
        return

    # Account selector
    account_options = [f"{a['name']} ({a['call_count']} calls)" for a in accounts]
    selected_idx = st.selectbox(
        "Select Account",
        range(len(account_options)),
        format_func=lambda i: account_options[i],
        key="gdrive_account_select",
    )

    selected_account = accounts[selected_idx]

    # Step 3: Show recent calls
    st.markdown(f"**Account: {selected_account['name']}** — {selected_account['call_count']} total calls")

    with st.spinner("Loading most recent calls..."):
        recent_calls = get_recent_calls_info(selected_account["path"], max_calls=5)

    if not recent_calls:
        st.warning("No call files found in this account folder.")
        return

    st.markdown(f"**{len(recent_calls)} most recent calls to import:**")

    # Display calls table
    call_data = []
    for call in recent_calls:
        call_data.append({
            "Date": call["date"],
            "Title": call["title"],
            "Has Transcript": "✅" if call["has_transcript"] else "❌",
        })
    st.table(call_data)

    # Step 4: Import button
    if st.button("🚀 Import Selected Account", type="primary", use_container_width=True):
        _execute_import(
            account_name=selected_account["name"],
            account_path=selected_account["path"],
            max_calls=5,
        )


def _execute_import(account_name: str, account_path: str, max_calls: int):
    """Run the full import pipeline: parse, create account if needed, upload."""

    progress = st.progress(0, text="Parsing Gong transcripts...")

    # Parse calls
    try:
        parsed_calls = download_and_parse_calls(account_path, max_calls)
    except Exception as e:
        st.error(f"Failed to parse transcripts: {e}")
        return

    if not parsed_calls:
        st.warning("No valid calls found to import.")
        return

    progress.progress(30, text=f"Parsed {len(parsed_calls)} calls")

    # Find or create account
    existing_accounts = list_accounts()
    account_id = None
    for acct in existing_accounts:
        if acct["account_name"].lower() == account_name.lower():
            account_id = acct["id"]
            break

    if not account_id:
        progress.progress(40, text=f"Creating account: {account_name}")
        acct = create_account(name=account_name)
        account_id = acct.id
        st.info(f"Created new account: **{account_name}**")

    progress.progress(50, text="Uploading transcripts to database...")

    # Upload each call
    try:
        results = upload_calls_to_db(parsed_calls, account_id)
    except Exception as e:
        st.error(f"Failed to upload transcripts: {e}")
        return

    progress.progress(100, text="Import complete!")

    # Log action
    log_action(
        ACTION_TRANSCRIPT_UPLOAD,
        action_detail=f"Imported {len(results)} calls from Google Drive for {account_name}",
        account_id=account_id,
        account_name=account_name,
        page_name="Upload Transcript",
    )

    # Success summary
    st.success(
        f"✅ Imported **{len(results)}** calls for **{account_name}**\n\n"
        + "\n".join(
            f"- {call.metadata.date}: {call.metadata.title[:50]} ({r.token_count} tokens)"
            for call, r in zip(parsed_calls, results)
        )
    )
    st.balloons()


# ── Tab 2: Manual Text Upload ──────────────────────────────────────────────


def _render_manual_upload():
    st.subheader("Upload Transcript (Text Paste)")

    accounts = list_accounts()
    if not accounts:
        empty_state(
            "No accounts yet",
            "📁",
            "Create one first using the Create New Account tab.",
        )
        return

    account_names = [a["account_name"] for a in accounts]
    account_ids = [a["id"] for a in accounts]

    selected_name = st.selectbox("Select Account", account_names, key="manual_account_select")
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
                log_action(
                    ACTION_TRANSCRIPT_UPLOAD,
                    action_detail=f"Uploading transcript for {selected_name}",
                    account_id=account_id,
                    account_name=selected_name,
                    page_name="Upload Transcript",
                )
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


# ── Tab 3: Create Account ─────────────────────────────────────────────────


def _render_create_account():
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

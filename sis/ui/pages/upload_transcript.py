"""Import & Analyze — scan folder, pick account, choose deal type, run pipeline."""

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
from sis.services.user_action_log_service import (
    log_action,
    ACTION_TRANSCRIPT_UPLOAD,
    ACTION_ANALYSIS_RUN,
)
from sis.ui.components.layout import page_header, empty_state
from sis.config import GOOGLE_DRIVE_TRANSCRIPTS_PATH

# ── Constants ──────────────────────────────────────────────────────────

DEAL_TYPES = [
    "New Logo",
    "Expansion - Upsell",
    "Expansion - Cross Sell",
    "Expansion - Both",
    "Renewal",
]


def render():
    page_header("Import & Analyze")

    # ── Step 1: Folder path ────────────────────────────────────────────
    default_path = GOOGLE_DRIVE_TRANSCRIPTS_PATH or ""
    drive_path = st.text_input(
        "📁 Transcripts Folder Path",
        value=st.session_state.get("gdrive_path", default_path),
        placeholder="~/Library/CloudStorage/GoogleDrive-you@company.com/My Drive/Transcripts",
        help="Local path to the folder containing account sub-folders with Gong JSON exports",
    )

    if not drive_path:
        st.info(
            "Enter the local path to your transcripts folder. "
            "Each sub-folder should represent an account with paired Gong JSON files "
            "(metadata + transcript)."
        )
        return

    is_valid, message = validate_drive_path(drive_path)
    if not is_valid:
        st.error(message)
        return

    st.session_state["gdrive_path"] = drive_path
    st.caption(f"✅ {message}")

    # ── Step 2: Account picker ─────────────────────────────────────────
    with st.spinner("Scanning account folders..."):
        accounts = list_account_folders(drive_path)

    if not accounts:
        empty_state("No account folders found", "📂", "Check that the folder contains sub-folders.")
        return

    account_options = [f"{a['name']} ({a['call_count']} calls)" for a in accounts]
    selected_idx = st.selectbox(
        "Select Account",
        range(len(account_options)),
        format_func=lambda i: account_options[i],
        key="import_account_select",
    )
    selected_account = accounts[selected_idx]

    # ── Step 3: Recent calls preview ───────────────────────────────────
    st.markdown(f"**Account: {selected_account['name']}** — {selected_account['call_count']} total calls")

    with st.spinner("Loading most recent calls..."):
        recent_calls = get_recent_calls_info(selected_account["path"], max_calls=5)

    if not recent_calls:
        st.warning("No call files found in this account folder.")
        return

    st.markdown(f"**{len(recent_calls)} most recent calls to import:**")
    call_data = []
    for call in recent_calls:
        call_data.append({
            "Date": call["date"],
            "Title": call["title"],
            "Transcript": "✅" if call["has_transcript"] else "❌",
        })
    st.table(call_data)

    # ── Step 4: Deal configuration ─────────────────────────────────────
    st.markdown("---")
    st.subheader("Deal Configuration")

    col1, col2 = st.columns(2)

    with col1:
        deal_type = st.selectbox(
            "Deal Type *",
            DEAL_TYPES,
            key="import_deal_type",
            help="Type of deal for this account",
        )

    with col2:
        mrr = st.number_input(
            "MRR Estimate ($)",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            key="import_mrr",
            help="Monthly recurring revenue estimate (optional)",
        )

    # Optional fields in an expander
    with st.expander("Additional Details (Optional)"):
        ecol1, ecol2, ecol3 = st.columns(3)
        with ecol1:
            ae_owner = st.text_input("AE Owner", key="import_ae_owner")
        with ecol2:
            team_lead = st.text_input("Team Lead", key="import_team_lead")
        with ecol3:
            team_name = st.text_input("Team Name", key="import_team_name")

    # ── Step 5: Run Analysis button ────────────────────────────────────
    st.markdown("---")

    if st.button("🚀 Import & Run Analysis", type="primary", use_container_width=True):
        _execute_import_and_analyze(
            account_name=selected_account["name"],
            account_path=selected_account["path"],
            deal_type=deal_type,
            mrr=mrr if mrr > 0 else None,
            ae_owner=ae_owner or None,
            team_lead=team_lead or None,
            team_name=team_name or None,
            max_calls=5,
        )

    # ── Fallback: manual text-paste ────────────────────────────────────
    with st.expander("📝 Manual Text Upload (Advanced)"):
        _render_manual_upload()


# ── Core pipeline: import transcripts + run analysis ───────────────────


def _execute_import_and_analyze(
    account_name: str,
    account_path: str,
    deal_type: str,
    mrr: float | None,
    ae_owner: str | None,
    team_lead: str | None,
    team_name: str | None,
    max_calls: int,
):
    """Import transcripts from folder, then run the full 10-agent analysis pipeline."""

    progress = st.progress(0, text="Parsing Gong transcripts...")

    # ── Phase 1: Parse calls ───────────────────────────────────────────
    try:
        parsed_calls = download_and_parse_calls(account_path, max_calls)
    except Exception as e:
        st.error(f"Failed to parse transcripts: {e}")
        return

    if not parsed_calls:
        st.warning("No valid calls found to import.")
        return

    progress.progress(15, text=f"Parsed {len(parsed_calls)} calls")

    # ── Phase 2: Find or create account ────────────────────────────────
    existing_accounts = list_accounts()
    account_id = None
    for acct in existing_accounts:
        if acct["account_name"].lower() == account_name.lower():
            account_id = acct["id"]
            break

    if not account_id:
        progress.progress(20, text=f"Creating account: {account_name}")
        acct = create_account(
            name=account_name,
            mrr=mrr,
            deal_type=deal_type,
            ae_owner=ae_owner,
            team_lead=team_lead,
            team=team_name,
        )
        account_id = acct.id
        st.info(f"Created new account: **{account_name}** ({deal_type})")
    else:
        progress.progress(20, text=f"Found existing account: {account_name}")

    # ── Phase 3: Upload transcripts to DB ──────────────────────────────
    progress.progress(25, text="Uploading transcripts to database...")

    try:
        results = upload_calls_to_db(parsed_calls, account_id)
    except Exception as e:
        st.error(f"Failed to upload transcripts: {e}")
        return

    progress.progress(40, text=f"Uploaded {len(results)} transcripts")

    log_action(
        ACTION_TRANSCRIPT_UPLOAD,
        action_detail=f"Imported {len(results)} calls from folder for {account_name}",
        account_id=account_id,
        account_name=account_name,
        page_name="Import & Analyze",
    )

    # ── Phase 4: Run 10-agent analysis pipeline ────────────────────────
    progress.progress(45, text="Starting analysis pipeline...")
    status_text = st.empty()

    def progress_callback(step_name: str, current: int, total: int):
        pct = 45 + int(50 * current / total)
        progress.progress(pct / 100, text=f"Step {current}/{total}: {step_name}")
        status_text.markdown(f"**Running:** {step_name}")

    try:
        from sis.services.analysis_service import analyze_account

        log_action(
            ACTION_ANALYSIS_RUN,
            action_detail=f"Running 10-agent pipeline for {account_name} ({deal_type})",
            account_id=account_id,
            account_name=account_name,
            page_name="Import & Analyze",
        )

        result = analyze_account(
            account_id=account_id,
            progress_callback=progress_callback,
        )

        progress.progress(100, text="Complete!")
        status_text.empty()

        # ── Results summary ────────────────────────────────────────────
        if result["status"] == "completed":
            st.success(
                f"✅ **Import & Analysis complete for {account_name}**\n\n"
                f"- **Transcripts imported:** {len(results)}\n"
                f"- **Agents completed:** {result['agents_completed']}/{result['agents_total']}\n"
                f"- **Cost:** ${result['total_cost_usd']:.4f}\n"
                f"- **Time:** {result['wall_clock_seconds']}s"
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

        st.balloons()

    except Exception as e:
        progress.progress(0, text="Failed")
        st.error(f"Pipeline error: {e}")


# ── Manual text upload (fallback) ──────────────────────────────────────


def _render_manual_upload():
    accounts = list_accounts()
    if not accounts:
        st.caption("No accounts yet — use the main flow above to create one automatically.")
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
                    action_detail=f"Manual upload for {selected_name}",
                    account_id=account_id,
                    account_name=selected_name,
                    page_name="Import & Analyze",
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

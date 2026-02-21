"""Deal Brief — 3-format deal brief per PRD P0-19.

Generates exportable deal briefs in three styles:
1. Structured one-pager (fixed template)
2. Narrative memo (3-5 paragraphs + structured fields)
3. Inspection questions (3-5 questions with evidence)
"""

import streamlit as st

from sis.services.account_service import list_accounts
from sis.services.export_service import export_deal_brief
from sis.services.usage_tracking_service import track_event


def render():
    st.title("Deal Brief")
    st.caption("One-page deal brief for pipeline review prep — 3 formats")

    accounts = list_accounts()
    scored = [a for a in accounts if a.get("health_score") is not None]

    if not scored:
        st.info("No scored accounts. Run analysis first.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        names = [a["account_name"] for a in scored]
        selected = st.selectbox("Select Account", names)
        account = scored[names.index(selected)]

    with col2:
        format_labels = {
            "structured": "Structured One-Pager",
            "narrative": "Narrative Memo",
            "inspection": "Inspection Questions",
        }
        chosen_format = st.radio(
            "Brief Format",
            list(format_labels.keys()),
            format_func=lambda x: format_labels[x],
        )

    st.divider()

    # Generate brief
    track_event("brief_view", account_id=account["id"], page_name="Deal Brief")
    brief = export_deal_brief(account["id"], format=chosen_format)

    # Display
    st.markdown(brief)

    # Download button
    st.divider()
    st.download_button(
        label="Download as Markdown",
        data=brief,
        file_name=f"deal-brief-{account['account_name'].lower().replace(' ', '-')}.md",
        mime="text/markdown",
    )

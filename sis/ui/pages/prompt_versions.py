"""Prompt Versions — Git-like prompt version control UI per PRD Sec 8.

Agent selector, version history, create new version, rollback, and side-by-side diff.
"""

import streamlit as st

from sis.services.prompt_version_service import (
    list_versions,
    get_active_version,
    create_version,
    rollback_version,
    diff_versions,
)
from sis.ui.components.layout import page_header, section_divider, empty_state


AGENTS = [
    ("agent_1", "Stage & Progress Classifier"),
    ("agent_2", "Relationship & Power Map"),
    ("agent_3", "Commercial & Risk"),
    ("agent_4", "Momentum & Engagement"),
    ("agent_5", "Technical Validation"),
    ("agent_6", "Economic Buyer"),
    ("agent_7", "MSP & Next Steps"),
    ("agent_8", "Competitive Displacement"),
    ("agent_9", "Open Discovery / Adversarial"),
    ("agent_10", "Synthesis"),
]


def render():
    page_header("Prompt Versions", "Version control for agent prompts — create, rollback, and diff")

    # Agent selector
    agent_labels = {aid: f"{aid}: {name}" for aid, name in AGENTS}
    selected_agent = st.selectbox(
        "Select Agent",
        [aid for aid, _ in AGENTS],
        format_func=lambda x: agent_labels[x],
    )

    # Show rollback/create toasts from previous rerun
    if st.session_state.get("_pv_toast"):
        st.toast(st.session_state.pop("_pv_toast"))

    versions = list_versions(agent_id=selected_agent)
    active = get_active_version(selected_agent)

    # --- Active version display ---
    st.subheader("Active Version")
    if active:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                st.markdown(f"**Version:** {active['version']}")
            with c2:
                st.caption(f"Created: {active['created_at'][:19]}")
            with c3:
                if active.get("change_notes"):
                    st.caption(f"Notes: {active['change_notes']}")
            st.code(active["prompt_template"], language="text")
    else:
        empty_state(
            "No versions for this agent",
            "\U0001f4dd",
            "Create the first version below.",
        )

    section_divider()

    # --- Version history ---
    st.subheader("Version History")
    if versions:
        for v in versions:
            status = ":green[ACTIVE]" if v["is_active"] else ":gray[inactive]"
            with st.expander(f"v{v['version']} {status} — {v['created_at'][:19]}"):
                if v.get("change_notes"):
                    st.markdown(f"**Notes:** {v['change_notes']}")
                if v.get("calibration_config_version"):
                    st.caption(f"Calibration config: {v['calibration_config_version']}")
                st.code(v["prompt_template"], language="text")

                if not v["is_active"]:
                    if st.button(
                        f"Rollback to v{v['version']}",
                        key=f"rollback_{v['id']}",
                        type="secondary",
                    ):
                        rollback_version(selected_agent, v["id"])
                        st.session_state["_pv_toast"] = f"Rolled back to v{v['version']}"
                        st.rerun()
    else:
        empty_state(
            "No version history",
            "\U0001f4c2",
        )

    section_divider()

    # --- Create new version ---
    st.subheader("Create New Version")
    with st.expander("New Version", expanded=not versions):
        new_version = st.text_input("Version label", placeholder="e.g. 1.1, 2.0")
        new_template = st.text_area(
            "Prompt template",
            height=300,
            placeholder="Enter the full prompt template...",
        )
        new_notes = st.text_input("Change notes", placeholder="What changed and why?")
        new_cal_version = st.text_input(
            "Calibration config version (optional)",
            placeholder="e.g. v1.0",
        )

        if st.button("Save New Version", type="primary", disabled=not (new_version and new_template)):
            try:
                create_version(
                    agent_id=selected_agent,
                    version=new_version,
                    prompt_template=new_template,
                    change_notes=new_notes or None,
                    calibration_config_version=new_cal_version or None,
                )
                st.session_state["_pv_toast"] = f"Created v{new_version} for {selected_agent}"
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    section_divider()

    # --- Side-by-side diff ---
    st.subheader("Compare Versions")
    if len(versions) >= 2:
        dc1, dc2 = st.columns(2)
        version_options = {v["id"]: f"v{v['version']} ({v['created_at'][:10]})" for v in versions}
        ids = list(version_options.keys())
        with dc1:
            id_a = st.selectbox("Version A", ids, format_func=lambda x: version_options[x], key="diff_a")
        with dc2:
            id_b = st.selectbox(
                "Version B", ids, index=min(1, len(ids) - 1),
                format_func=lambda x: version_options[x], key="diff_b",
            )

        if st.button("Show Diff"):
            if id_a == id_b:
                st.warning("Select two different versions to compare.")
            else:
                diff_text = diff_versions(id_a, id_b)
                if diff_text:
                    st.code(diff_text, language="diff")
                else:
                    st.success("No differences found.")
    else:
        empty_state(
            "Need at least 2 versions to compare",
            "\U0001f504",
        )

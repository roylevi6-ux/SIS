"""Agent card — renders a single agent's analysis in a styled card per Technical Architecture Appendix B."""

import html

import streamlit as st


def render_agent_card(analysis: dict) -> None:
    """Render an agent analysis as a styled expandable card.

    Args:
        analysis: Dict with agent_id, agent_name, narrative, findings,
                  evidence, confidence_overall, data_gaps, sparse_data_flag.
    """
    agent_name = analysis.get("agent_name", "Unknown Agent")
    confidence = analysis.get("confidence_overall")
    sparse = analysis.get("sparse_data_flag", False)

    # Confidence color
    if confidence is not None:
        if confidence >= 0.7:
            conf_color = "#22c55e"
        elif confidence >= 0.4:
            conf_color = "#f59e0b"
        else:
            conf_color = "#ef4444"
        conf_label = f"{confidence:.0%}"
    else:
        conf_color = "#6b7280"
        conf_label = "N/A"

    # Build header
    header_parts = [agent_name]
    if sparse:
        header_parts.append("[sparse data]")
    header = " ".join(header_parts)

    badge = (
        f'<span style="padding:2px 6px;border-radius:4px;'
        f'background:{conf_color}20;color:{conf_color};font-size:12px;font-weight:600">'
        f'{conf_label}</span>'
    )

    with st.expander(f"{header} (confidence: {conf_label})"):
        st.markdown(badge, unsafe_allow_html=True)

        # Narrative
        narrative = analysis.get("narrative", "")
        if narrative:
            st.markdown(narrative)

        # Data gaps
        gaps = analysis.get("data_gaps", [])
        if gaps:
            st.markdown("**Data Gaps:**")
            for gap in gaps:
                st.markdown(f"- {html.escape(str(gap))}")

        # Findings summary
        findings = analysis.get("findings", {})
        if findings:
            with st.container():
                st.markdown("**Findings:**")
                st.json(findings)

        # Evidence (first 5)
        evidence = analysis.get("evidence", [])
        if evidence:
            from sis.ui.components.evidence_viewer import render_evidence_list
            render_evidence_list(evidence[:5])

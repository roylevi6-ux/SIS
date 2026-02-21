"""Agent card — renders a single agent's analysis in a styled card per Technical Architecture Appendix B."""

import html

import streamlit as st

from sis.ui.theme import Colors, Typography


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
    conf_color = Colors.confidence_color(confidence)
    conf_label = f"{confidence:.0%}" if confidence is not None else "N/A"

    # Build header
    header_parts = [agent_name]
    if sparse:
        header_parts.append("[sparse data]")
    header = " ".join(header_parts)

    badge = (
        f'<span style="padding:2px 6px;border-radius:4px;'
        f'background:{Colors.with_alpha(conf_color)};color:{conf_color};'
        f'font-size:{Typography.CAPTION}px;font-weight:{Typography.SEMIBOLD}">'
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

"""Evidence viewer — renders evidence citations per Technical Architecture Appendix B."""

import html

import streamlit as st


def render_evidence_list(evidence: list[dict], max_items: int = 5) -> None:
    """Render a list of evidence citations.

    Args:
        evidence: List of evidence dicts with quote, speaker, transcript_index, interpretation.
        max_items: Maximum number of evidence items to show.
    """
    if not evidence:
        return

    st.markdown("**Evidence:**")
    for ev in evidence[:max_items]:
        if not isinstance(ev, dict):
            continue
        render_evidence_item(ev)


def render_evidence_item(ev: dict) -> None:
    """Render a single evidence citation with quote styling."""
    quote = html.escape(ev.get("quote", ""))
    speaker = html.escape(ev.get("speaker", "Unknown"))
    transcript_idx = ev.get("transcript_index", "?")
    interpretation = html.escape(ev.get("interpretation", ""))

    st.markdown(
        f'<div style="border-left:3px solid #8b5cf6;padding:6px 12px;margin:4px 0;'
        f'background:#8b5cf610;border-radius:0 4px 4px 0">'
        f'<em>"{quote}"</em><br>'
        f'<span style="color:#6b7280;font-size:12px">'
        f'— {speaker}, Call {transcript_idx}</span>'
        f'{"<br><span style=&quot;color:#374151;font-size:13px&quot;>" + interpretation + "</span>" if interpretation else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

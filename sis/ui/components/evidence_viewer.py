"""Evidence viewer — renders evidence citations per Technical Architecture Appendix B."""

import html

import streamlit as st

from sis.ui.theme import Colors, Typography


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

    interp_html = ""
    if interpretation:
        interp_html = (
            f'<br><span style="color:{Colors.TEXT_PRIMARY};'
            f'font-size:{Typography.CAPTION + 1}px">{interpretation}</span>'
        )

    st.markdown(
        f'<div class="sis-evidence">'
        f'<div class="quote">"{quote}"</div>'
        f'<div class="attribution">— {speaker}, Call {transcript_idx}</div>'
        f'{interp_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

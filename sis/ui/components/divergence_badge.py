"""Divergence badge — visual indicator when AI and IC forecasts differ per PRD P0-12."""

import html

import streamlit as st

from sis.ui.theme import Colors, Typography


def render_divergence_badge(
    ai_forecast: str | None,
    ic_forecast: str | None,
    explanation: str | None = None,
) -> None:
    """Render a divergence badge when AI and IC forecasts differ.

    Args:
        ai_forecast: AI-predicted forecast category.
        ic_forecast: IC (rep) forecast category.
        explanation: Optional divergence explanation text.
    """
    if not ai_forecast or not ic_forecast:
        return

    if ai_forecast == ic_forecast:
        st.markdown(
            f'<span class="sis-badge sis-badge-success">ALIGNED</span>',
            unsafe_allow_html=True,
        )
        return

    ai_safe = html.escape(ai_forecast)
    ic_safe = html.escape(ic_forecast)
    st.markdown(
        f'<div style="padding:8px;border-radius:6px;'
        f'background:{Colors.with_alpha(Colors.DANGER, "15")};'
        f'border:1px solid {Colors.with_alpha(Colors.DANGER, "40")}">'
        f'<span style="color:{Colors.DANGER};font-weight:700;'
        f'font-size:{Typography.CAPTION + 1}px">DIVERGENT</span><br>'
        f'<span style="font-size:{Typography.CAPTION}px">'
        f'AI: <b>{ai_safe}</b> vs IC: <b>{ic_safe}</b></span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if explanation:
        st.caption(html.escape(explanation))


def render_divergence_inline(divergence_flag: bool) -> str:
    """Return an inline HTML span for use in tables/lists.

    Args:
        divergence_flag: Whether AI and IC forecasts diverge.

    Returns:
        HTML string for inline use.
    """
    if divergence_flag:
        return (
            f'<span style="padding:1px 6px;border-radius:3px;'
            f'background:{Colors.with_alpha(Colors.DANGER)};color:{Colors.DANGER};'
            f'font-size:{Typography.CAPTION}px;font-weight:{Typography.SEMIBOLD}">'
            f'DIV</span>'
        )
    return ""

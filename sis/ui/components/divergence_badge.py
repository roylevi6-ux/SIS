"""Divergence badge — visual indicator when AI and IC forecasts differ per PRD P0-12."""

import html

import streamlit as st


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
            '<span style="padding:2px 8px;border-radius:4px;'
            'background:#22c55e20;color:#22c55e;font-size:12px;font-weight:600">'
            'ALIGNED</span>',
            unsafe_allow_html=True,
        )
        return

    ai_safe = html.escape(ai_forecast)
    ic_safe = html.escape(ic_forecast)
    st.markdown(
        f'<div style="padding:8px;border-radius:6px;'
        f'background:#ef444415;border:1px solid #ef444440">'
        f'<span style="color:#ef4444;font-weight:700;font-size:13px">'
        f'DIVERGENT</span><br>'
        f'<span style="font-size:12px">'
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
            '<span style="padding:1px 6px;border-radius:3px;'
            'background:#ef444420;color:#ef4444;font-size:11px;font-weight:600">'
            'DIV</span>'
        )
    return ""

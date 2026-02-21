"""Health score badge — color-coded display per PRD Section 7.11."""

from __future__ import annotations

import streamlit as st

from sis.ui.theme import Colors, Typography


def render_health_badge(score: int | None, size: str = "large") -> None:
    """Render a color-coded health score badge.

    Args:
        score: Health score 0-100, or None if unscored
        size: "large" for detail view, "small" for table/list view
    """
    if score is None:
        st.markdown("**--**")
        return

    color = Colors.status_color(score)
    label = "Healthy" if score >= 70 else "At Risk" if score >= 45 else "Critical"

    if size == "large":
        st.markdown(
            f'<div class="sis-score-lg" style="background:{Colors.with_alpha(color)};'
            f'border:2px solid {color}">'
            f'<div class="score-value" style="color:{color}">{score}</div>'
            f'<div class="score-label" style="color:{color}">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<span style="padding:2px 8px;border-radius:4px;'
            f'background:{Colors.with_alpha(color)};color:{color};'
            f'font-weight:bold;font-size:{Typography.CAPTION}px">{score}</span>',
            unsafe_allow_html=True,
        )


def render_momentum_indicator(direction: str | None) -> None:
    """Render momentum arrow indicator."""
    if direction is None:
        st.markdown("--")
        return

    arrows = {
        "Improving": "↑",
        "Stable": "→",
        "Declining": "↓",
    }
    arrow = arrows.get(direction, "?")
    color = Colors.direction_color(direction)
    st.markdown(
        f'<span style="color:{color};font-size:20px;font-weight:bold">{arrow}</span> '
        f'<span style="color:{color}">{direction}</span>',
        unsafe_allow_html=True,
    )


def render_forecast_badge(category: str | None) -> None:
    """Render forecast category badge."""
    if not category:
        st.markdown("--")
        return

    color = Colors.FORECAST.get(category, Colors.NEUTRAL)
    st.markdown(
        f'<span style="padding:2px 8px;border-radius:4px;'
        f'background:{Colors.with_alpha(color)};color:{color};'
        f'font-weight:600;font-size:{Typography.CAPTION}px">{category}</span>',
        unsafe_allow_html=True,
    )

"""Health score badge — color-coded display per PRD Section 7.11."""

import streamlit as st


def render_health_badge(score: int | None, size: str = "large") -> None:
    """Render a color-coded health score badge.

    Args:
        score: Health score 0-100, or None if unscored
        size: "large" for detail view, "small" for table/list view
    """
    if score is None:
        st.markdown("**--**")
        return

    if score >= 70:
        color = "#22c55e"  # green
        label = "Healthy"
    elif score >= 45:
        color = "#f59e0b"  # amber
        label = "At Risk"
    else:
        color = "#ef4444"  # red
        label = "Critical"

    if size == "large":
        st.markdown(
            f'<div style="text-align:center;padding:16px;border-radius:12px;'
            f'background:{color}20;border:2px solid {color}">'
            f'<span style="font-size:48px;font-weight:bold;color:{color}">{score}</span>'
            f'<br><span style="color:{color};font-weight:600">{label}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<span style="padding:2px 8px;border-radius:4px;'
            f'background:{color}20;color:{color};font-weight:bold">{score}</span>',
            unsafe_allow_html=True,
        )


def render_momentum_indicator(direction: str | None) -> None:
    """Render momentum arrow indicator."""
    if direction is None:
        st.markdown("--")
        return

    arrows = {
        "Improving": ("↑", "#22c55e"),
        "Stable": ("→", "#6b7280"),
        "Declining": ("↓", "#ef4444"),
    }
    arrow, color = arrows.get(direction, ("?", "#6b7280"))
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

    colors = {
        "Commit": "#22c55e",
        "Best Case": "#3b82f6",
        "Pipeline": "#8b5cf6",
        "Upside": "#06b6d4",
        "At Risk": "#f59e0b",
        "No Decision Risk": "#ef4444",
    }
    color = colors.get(category, "#6b7280")
    st.markdown(
        f'<span style="padding:2px 8px;border-radius:4px;'
        f'background:{color}20;color:{color};font-weight:600;font-size:13px">{category}</span>',
        unsafe_allow_html=True,
    )

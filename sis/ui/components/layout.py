"""SIS reusable layout components — replaces duplicated patterns across 20 pages."""

from __future__ import annotations

import html as html_mod

import streamlit as st

from sis.ui.theme import Colors, Typography


def page_header(title: str, subtitle: str | None = None) -> None:
    """Render a consistent page header with optional subtitle."""
    st.markdown(
        f'<h1 style="margin-bottom:0;color:{Colors.TEXT_PRIMARY};'
        f'font-size:{Typography.H1}px;font-weight:{Typography.BOLD}">{html_mod.escape(title)}</h1>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.caption(subtitle)


def section_divider() -> None:
    """Render a subtle section divider (replaces st.divider())."""
    st.markdown('<hr class="sis-section-divider">', unsafe_allow_html=True)


def metric_row(metrics: list[dict]) -> None:
    """Render a row of metric cards.

    Args:
        metrics: List of dicts with 'label', 'value', and optional 'color' keys.
                 Example: [{"label": "Total Deals", "value": 42}, ...]
    """
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        color = m.get("color", Colors.TEXT_PRIMARY)
        with col:
            st.markdown(
                f'<div class="sis-metric-card">'
                f'<div class="label">{html_mod.escape(str(m["label"]))}</div>'
                f'<div class="value" style="color:{color}">{html_mod.escape(str(m["value"]))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def status_badge(text: str, status: str = "neutral") -> str:
    """Return HTML for a status badge pill.

    Args:
        text: Badge text.
        status: One of success, warning, danger, info, neutral, accent, primary.

    Returns:
        HTML string (use with st.markdown(..., unsafe_allow_html=True)).
    """
    safe = html_mod.escape(text)
    return f'<span class="sis-badge sis-badge-{status}">{safe}</span>'


def score_badge(score: int | float | None, size: str = "small") -> str:
    """Return HTML for a color-coded score badge.

    Args:
        score: Numeric score 0-100, or None.
        size: 'small' for inline, 'large' for hero display.

    Returns:
        HTML string.
    """
    if score is None:
        return '<span class="sis-badge sis-badge-neutral">--</span>'

    color = Colors.status_color(score)
    if size == "large":
        label = "Healthy" if score >= 70 else "At Risk" if score >= 45 else "Critical"
        return (
            f'<div class="sis-score-lg" style="background:{Colors.with_alpha(color)};'
            f'border:2px solid {color}">'
            f'<div class="score-value" style="color:{color}">{int(score)}</div>'
            f'<div class="score-label" style="color:{color}">{label}</div>'
            f'</div>'
        )
    return (
        f'<span style="padding:2px 8px;border-radius:4px;'
        f'background:{Colors.with_alpha(color)};color:{color};'
        f'font-weight:bold;font-size:{Typography.CAPTION}px">{int(score)}</span>'
    )


def direction_badge(direction: str | None) -> str:
    """Return HTML for a momentum direction badge.

    Args:
        direction: 'Improving', 'Stable', 'Declining', or None.

    Returns:
        HTML string.
    """
    if not direction:
        return '<span class="sis-badge sis-badge-neutral">--</span>'

    arrows = {"Improving": "↑", "Stable": "→", "Declining": "↓"}
    arrow = arrows.get(direction, "?")
    color = Colors.direction_color(direction)
    safe = html_mod.escape(direction)
    return (
        f'<span style="color:{color};font-weight:bold">{arrow}</span> '
        f'<span style="color:{color}">{safe}</span>'
    )


def empty_state(msg: str, icon: str = "📭", hint: str | None = None) -> None:
    """Render a centered empty-state placeholder.

    Args:
        msg: Primary message.
        icon: Emoji icon.
        hint: Optional secondary hint text.
    """
    hint_html = f'<div class="hint">{html_mod.escape(hint)}</div>' if hint else ""
    st.markdown(
        f'<div class="sis-empty-state">'
        f'<div class="icon">{icon}</div>'
        f'<div class="message">{html_mod.escape(msg)}</div>'
        f'{hint_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def forecast_badge(category: str | None) -> str:
    """Return HTML for a forecast category badge.

    Args:
        category: Forecast category string.

    Returns:
        HTML string.
    """
    if not category:
        return '<span class="sis-badge sis-badge-neutral">--</span>'
    color = Colors.FORECAST.get(category, Colors.NEUTRAL)
    safe = html_mod.escape(category)
    return (
        f'<span style="padding:2px 8px;border-radius:4px;'
        f'background:{Colors.with_alpha(color)};color:{color};'
        f'font-weight:600;font-size:{Typography.CAPTION}px">{safe}</span>'
    )

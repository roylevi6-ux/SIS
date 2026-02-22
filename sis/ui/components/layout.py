"""SIS reusable layout components — replaces duplicated patterns across 20 pages."""

from __future__ import annotations

import html as html_mod

import streamlit as st

from sis.ui.theme import Colors, Radius, Shadows, Spacing, Typography


def page_header(title: str, subtitle: str | None = None) -> None:
    """Render a gradient page header banner."""
    subtitle_html = (
        f'<div class="subtitle">{html_mod.escape(subtitle)}</div>'
        if subtitle else ""
    )
    st.markdown(
        f'<div class="sis-page-header">'
        f'<div class="title">{html_mod.escape(title)}</div>'
        f'{subtitle_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_divider() -> None:
    """Render a subtle section divider."""
    st.markdown('<hr class="sis-section-divider">', unsafe_allow_html=True)


def metric_row(metrics: list[dict]) -> None:
    """Render a row of elevated metric cards.

    Args:
        metrics: List of dicts with 'label', 'value', and optional 'color'/'variant' keys.
                 variant: success|warning|danger|info for colored top border.
    """
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        color = m.get("color", Colors.TEXT_PRIMARY)
        variant = m.get("variant", "")
        variant_cls = f" sis-metric-card-{variant}" if variant else ""
        with col:
            st.markdown(
                f'<div class="sis-metric-card{variant_cls}">'
                f'<div class="label">{html_mod.escape(str(m["label"]))}</div>'
                f'<div class="value" style="color:{color}">'
                f'{html_mod.escape(str(m["value"]))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def status_badge(text: str, status: str = "neutral") -> str:
    """Return HTML for a status badge pill."""
    safe = html_mod.escape(text)
    return f'<span class="sis-badge sis-badge-{status}">{safe}</span>'


def score_badge(score: int | float | None, size: str = "small") -> str:
    """Return HTML for a color-coded score badge."""
    if score is None:
        return '<span class="sis-badge sis-badge-neutral">--</span>'

    color = Colors.status_color(score)
    if size == "large":
        label = "Healthy" if score >= 70 else "At Risk" if score >= 45 else "Critical"
        bg_color = Colors.with_alpha(color, "15")
        return (
            f'<div class="sis-score-lg" style="background:{bg_color};'
            f'border:2px solid {color}">'
            f'<div class="score-value" style="color:{color}">{int(score)}</div>'
            f'<div class="score-label" style="color:{color}">{label}</div>'
            f'</div>'
        )
    # Small inline badge
    bg_color = Colors.with_alpha(color, "18")
    return (
        f'<span style="padding:3px 10px;border-radius:{Radius.FULL}px;'
        f'background:{bg_color};color:{color};'
        f'font-weight:{Typography.BOLD};font-size:11px">{int(score)}</span>'
    )


def direction_badge(direction: str | None) -> str:
    """Return HTML for a momentum direction badge."""
    if not direction:
        return '<span class="sis-badge sis-badge-neutral">--</span>'

    arrows = {"Improving": "\u2191", "Stable": "\u2192", "Declining": "\u2193"}
    arrow = arrows.get(direction, "?")
    color = Colors.direction_color(direction)
    safe = html_mod.escape(direction)
    bg = Colors.with_alpha(color, "15")
    return (
        f'<span style="padding:3px 10px;border-radius:{Radius.FULL}px;'
        f'background:{bg};color:{color};font-weight:{Typography.SEMIBOLD};'
        f'font-size:11px">'
        f'{arrow} {safe}</span>'
    )


def empty_state(msg: str, icon: str = "\U0001f4ed", hint: str | None = None) -> None:
    """Render a centered empty-state placeholder with dashed border."""
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
    """Return HTML for a forecast category badge."""
    if not category:
        return '<span class="sis-badge sis-badge-neutral">--</span>'
    color = Colors.FORECAST.get(category, Colors.NEUTRAL)
    safe = html_mod.escape(category)
    bg = Colors.with_alpha(color, "18")
    return (
        f'<span style="padding:3px 10px;border-radius:{Radius.FULL}px;'
        f'background:{bg};color:{color};'
        f'font-weight:{Typography.SEMIBOLD};font-size:11px">{safe}</span>'
    )

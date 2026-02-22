"""SIS Design System — single source of truth for all design tokens.

Visual style: modern sales intelligence dashboard (Gong/Clari/Linear inspired).
Dark sidebar, white main area, rich accent colors, elevated cards.
"""

from __future__ import annotations


class Colors:
    """Color palette — sales intelligence dashboard."""

    # Brand — teal-green (energetic, not corporate)
    PRIMARY = "#059669"
    PRIMARY_LIGHT = "#34d399"
    PRIMARY_DARK = "#047857"
    PRIMARY_BG = "#ecfdf5"

    # Semantic status
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    INFO = "#3b82f6"
    ACCENT = "#8b5cf6"
    NEUTRAL = "#6b7280"

    # Layout
    SIDEBAR_BG = "#0f172a"
    SIDEBAR_BG_HOVER = "#1e293b"
    BG_PRIMARY = "#ffffff"
    BG_SECONDARY = "#f8fafc"
    BG_ELEVATED = "#ffffff"
    BORDER = "#e2e8f0"
    BORDER_LIGHT = "#f1f5f9"

    # Text
    TEXT_PRIMARY = "#0f172a"
    TEXT_SECONDARY = "#475569"
    TEXT_MUTED = "#64748b"
    TEXT_SUBTLE = "#94a3b8"

    # Sidebar text
    SIDEBAR_TEXT = "#94a3b8"
    SIDEBAR_TEXT_MUTED = "#475569"
    SIDEBAR_TEXT_BRIGHT = "#e2e8f0"
    SIDEBAR_ACTIVE_BG = "#1e293b"

    # WCAG AA-compliant badge text
    BADGE_SUCCESS = "#065f46"
    BADGE_WARNING = "#92400e"
    BADGE_DANGER = "#991b1b"
    BADGE_INFO = "#1e40af"
    BADGE_ACCENT = "#5b21b6"
    BADGE_NEUTRAL = "#374151"
    BADGE_PRIMARY = "#065f46"

    # Badge backgrounds (tinted, not too faint)
    BADGE_BG_SUCCESS = "#d1fae5"
    BADGE_BG_WARNING = "#fef3c7"
    BADGE_BG_DANGER = "#fee2e2"
    BADGE_BG_INFO = "#dbeafe"
    BADGE_BG_ACCENT = "#ede9fe"
    BADGE_BG_NEUTRAL = "#f3f4f6"
    BADGE_BG_PRIMARY = "#d1fae5"

    # Forecast category colors
    FORECAST = {
        "Commit": "#10b981",
        "Best Case": "#3b82f6",
        "Pipeline": "#8b5cf6",
        "Upside": "#06b6d4",
        "At Risk": "#f59e0b",
        "No Decision Risk": "#ef4444",
    }

    # Gradient pairs for cards/headers
    GRADIENT_PRIMARY = "linear-gradient(135deg, #059669 0%, #10b981 100%)"
    GRADIENT_DANGER = "linear-gradient(135deg, #dc2626 0%, #ef4444 100%)"
    GRADIENT_WARNING = "linear-gradient(135deg, #d97706 0%, #f59e0b 100%)"
    GRADIENT_INFO = "linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)"
    GRADIENT_DARK = "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)"

    @staticmethod
    def status_color(value: int | float | None) -> str:
        if value is None:
            return Colors.NEUTRAL
        if value >= 70:
            return Colors.SUCCESS
        if value >= 45:
            return Colors.WARNING
        return Colors.DANGER

    @staticmethod
    def confidence_color(value: float | None) -> str:
        if value is None:
            return Colors.NEUTRAL
        if value >= 0.7:
            return Colors.SUCCESS
        if value >= 0.4:
            return Colors.WARNING
        return Colors.DANGER

    @staticmethod
    def with_alpha(hex_color: str, alpha_hex: str = "20") -> str:
        return f"{hex_color}{alpha_hex}"

    @staticmethod
    def direction_color(direction: str | None) -> str:
        return {
            "Improving": Colors.SUCCESS,
            "Stable": Colors.NEUTRAL,
            "Declining": Colors.DANGER,
        }.get(direction or "", Colors.NEUTRAL)


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    XXXL = 48


class Typography:
    CAPTION = 12
    BODY = 14
    BODY_LG = 16
    H3 = 18
    H2 = 22
    H1 = 28
    HERO = 36

    NORMAL = 400
    MEDIUM = 500
    SEMIBOLD = 600
    BOLD = 700
    EXTRABOLD = 800


class Radius:
    SM = 4
    MD = 6
    LG = 8
    XL = 12
    XXL = 16
    FULL = 9999


class Shadows:
    SM = "0 1px 2px rgba(0,0,0,0.05)"
    MD = "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)"
    LG = "0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04)"
    XL = "0 20px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.04)"
    GLOW_PRIMARY = "0 0 20px rgba(5,150,105,0.15)"
    GLOW_DANGER = "0 0 20px rgba(239,68,68,0.15)"

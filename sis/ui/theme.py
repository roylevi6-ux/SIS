"""SIS Design System — single source of truth for all design tokens."""


class Colors:
    """Color palette inspired by Riskified enterprise dashboard."""

    # Brand
    PRIMARY = "#16a34a"

    # Semantic status
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    INFO = "#3b82f6"
    ACCENT = "#8b5cf6"
    NEUTRAL = "#6b7280"

    # Layout
    SIDEBAR_BG = "#1e293b"
    BG_SECONDARY = "#f8fafc"
    BORDER = "#e2e8f0"

    # Text
    TEXT_PRIMARY = "#0f172a"
    TEXT_MUTED = "#6b7280"

    # Forecast category colors
    FORECAST = {
        "Commit": "#22c55e",
        "Best Case": "#3b82f6",
        "Pipeline": "#8b5cf6",
        "Upside": "#06b6d4",
        "At Risk": "#f59e0b",
        "No Decision Risk": "#ef4444",
    }

    @staticmethod
    def status_color(value: int | float | None) -> str:
        """Return hex color for a 0-100 health/dimension score."""
        if value is None:
            return Colors.NEUTRAL
        if value >= 70:
            return Colors.SUCCESS
        if value >= 45:
            return Colors.WARNING
        return Colors.DANGER

    @staticmethod
    def confidence_color(value: float | None) -> str:
        """Return hex color for a 0-1 confidence value."""
        if value is None:
            return Colors.NEUTRAL
        if value >= 0.7:
            return Colors.SUCCESS
        if value >= 0.4:
            return Colors.WARNING
        return Colors.DANGER

    @staticmethod
    def with_alpha(hex_color: str, alpha_hex: str = "20") -> str:
        """Append alpha to a hex color, e.g. '#22c55e' → '#22c55e20'."""
        return f"{hex_color}{alpha_hex}"

    @staticmethod
    def direction_color(direction: str | None) -> str:
        """Return color for a momentum direction."""
        return {
            "Improving": Colors.SUCCESS,
            "Stable": Colors.NEUTRAL,
            "Declining": Colors.DANGER,
        }.get(direction or "", Colors.NEUTRAL)


class Spacing:
    """Spacing scale (px)."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Typography:
    """Font sizes and weights."""

    CAPTION = 12
    BODY = 14
    H3 = 18
    H2 = 22
    H1 = 28

    NORMAL = 400
    MEDIUM = 500
    SEMIBOLD = 600
    BOLD = 700


class Radius:
    """Border-radius scale (px)."""

    SM = 4
    MD = 6
    LG = 8
    XL = 12
    FULL = 9999

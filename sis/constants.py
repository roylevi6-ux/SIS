"""SIS constants — deal types, shared enums."""

from __future__ import annotations

DEAL_TYPES = frozenset({
    "new_logo",
    "expansion_upsell",
    "expansion_cross_sell",
    "expansion_both",
})

EXPANSION_DEAL_TYPES = frozenset({
    "expansion_upsell",
    "expansion_cross_sell",
    "expansion_both",
})


def is_expansion_deal(deal_type: str) -> bool:
    """Check if a deal type is an expansion deal."""
    return normalize_deal_type(deal_type) in EXPANSION_DEAL_TYPES


# Map UI display labels to normalized enum values
_DISPLAY_TO_ENUM = {
    "new logo": "new_logo",
    "expansion - upsell": "expansion_upsell",
    "expansion - cross sell": "expansion_cross_sell",
    "expansion - both": "expansion_both",
    "renewal": "new_logo",  # treat renewal as new_logo for pipeline purposes
}


def normalize_deal_type(deal_type: str | None) -> str:
    """Normalize a deal type from any format to the canonical enum value.

    Handles UI display labels ("Expansion - Both"), raw enums ("expansion_both"),
    and partial matches. Returns "new_logo" as fallback.
    """
    if not deal_type:
        return "new_logo"
    lowered = deal_type.strip().lower()
    # Already a valid enum?
    if lowered in DEAL_TYPES:
        return lowered
    # UI display label?
    if lowered in _DISPLAY_TO_ENUM:
        return _DISPLAY_TO_ENUM[lowered]
    # Fallback
    return "new_logo"

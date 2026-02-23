"""SIS constants — deal types, shared enums."""

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
    return deal_type in EXPANSION_DEAL_TYPES

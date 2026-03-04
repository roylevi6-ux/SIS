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


# --- Deal Context Questions ---------------------------------------------------

DEAL_CONTEXT_QUESTIONS: dict[int, dict] = {
    1: {
        "label": "Since the last analysis, has anything material changed in: (a) stakeholder involvement, (b) budget/timeline, (c) competitive situation, (d) deal momentum? Describe only what changed.",
        "category": "change_event",
        "input_type": "multi_category_text",
        "change_categories": ["stakeholder", "budget_timeline", "competitive", "momentum"],
    },
    2: {
        "label": "Who is the real economic buyer / decision maker?",
        "category": "stakeholder",
        "input_type": "text",
    },
    3: {
        "label": "Are there key stakeholders not appearing in calls?",
        "category": "stakeholder",
        "input_type": "text",
    },
    4: {
        "label": "Any off-channel activity (dinners, emails, office visits)?",
        "category": "engagement",
        "input_type": "text",
    },
    5: {
        "label": "What's the competitive landscape right now?",
        "category": "competitive",
        "input_type": "text",
    },
    6: {
        "label": "Has your champion's status changed?",
        "category": "stakeholder",
        "input_type": "dropdown_text",
        "options": ["Active", "Going quiet", "Left", "New champion identified"],
    },
    7: {
        "label": "Budget status?",
        "category": "commercial",
        "input_type": "dropdown",
        "options": ["Approved", "In discussion", "Not raised", "Frozen", "Unknown"],
    },
    8: {
        "label": "Is there a hard deadline driving this deal? If so, what is it and what happens if it's missed?",
        "category": "commercial",
        "input_type": "text",
    },
    9: {
        "label": "Any blockers or risks the calls don't show?",
        "category": "risk",
        "input_type": "text",
    },
    10: {
        "label": "Deal momentum right now?",
        "category": "momentum",
        "input_type": "dropdown_text",
        "options": ["Accelerating", "Steady", "Slowing", "Stalled"],
    },
    11: {
        "label": "On a 1-5 scale, how confident are you this deal closes this quarter? What would change your answer?",
        "category": "forecast",
        "input_type": "scale_text",
        "scale_min": 1,
        "scale_max": 5,
    },
    12: {
        "label": "Anything else?",
        "category": "general",
        "input_type": "text",
        "max_chars": 500,
    },
}

MAX_TL_CONTEXT_CHARS = 12000  # ~3000 tokens hard cap
TL_CONTEXT_STALENESS_DAYS = 60

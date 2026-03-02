# Design: Manager Actions Panel + Configurable Widget Layout

**Date**: 2026-03-02
**Status**: Approved
**Scope**: Two features — (1) surface manager_insight data as a consolidated panel, (2) per-user widget visibility/ordering config

---

## Feature 1: Manager Actions Panel

### Product Goal
Surface the weekly manager action items that every agent already generates (but nobody sees) into a single, scannable card near the top of the deal page.

### Implementation
- **No backend changes** — `manager_insight` is already inside the `findings` JSON blob returned by the existing agent analyses API
- **New component**: `ManagerActionsPanel` — placed after Deal Memo in the default widget order
- **Data flow**: Frontend fetches agent analyses → extracts `findings.manager_insight` from each → renders consolidated card
- **UI**: Card with header "Manager Actions This Week". Each item shows:
  - Agent name badge (e.g., "Relationship", "Momentum")
  - 2-3 sentence insight text
  - Ordered by agent number (pipeline order)

---

## Feature 2: Configurable Widget Layout

### Product Goal
Let each user choose which widgets appear on deal pages and in what order, via a dedicated settings page.

### Database: `user_preferences` table

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | Primary key |
| user_id | TEXT (FK → users.id) | The user |
| preference_key | TEXT | e.g., `"deal_page_widgets"` |
| preference_value | TEXT (JSON) | Config blob |
| updated_at | TEXT | ISO timestamp |

- **Unique constraint**: `(user_id, preference_key)`
- **Alembic migration** required

### Widget Config Schema

Stored as JSON in `preference_value` under key `"deal_page_widgets"`:

```json
{
  "widgets": [
    {"id": "status_strip", "visible": true, "order": 0},
    {"id": "call_timeline", "visible": true, "order": 1},
    {"id": "what_changed", "visible": true, "order": 2},
    {"id": "deal_memo", "visible": true, "order": 3},
    {"id": "manager_actions", "visible": true, "order": 4},
    {"id": "health_breakdown", "visible": true, "order": 5},
    {"id": "actions_risks", "visible": true, "order": 6},
    {"id": "positive_contradictions", "visible": true, "order": 7},
    {"id": "forecast_divergence", "visible": true, "order": 8},
    {"id": "key_unknowns", "visible": true, "order": 9},
    {"id": "forecast_rationale", "visible": true, "order": 10},
    {"id": "sf_gap", "visible": true, "order": 11},
    {"id": "agent_analyses", "visible": true, "order": 12},
    {"id": "deal_timeline", "visible": true, "order": 13},
    {"id": "analysis_history", "visible": true, "order": 14},
    {"id": "transcript_list", "visible": true, "order": 15}
  ]
}
```

### API Endpoints

- `GET /api/preferences/{key}` — returns user's config or default
- `PUT /api/preferences/{key}` — saves config (auto-save on change)

### Config Page: `/settings/display`

- Added to sidebar under Settings (alongside `/settings/teams`)
- Vertical list of all 16 widgets, each row:
  - Drag handle for reordering
  - Widget name + brief description
  - Toggle switch (visible/hidden)
- "Reset to Default" button
- Auto-saves with "Saved" toast feedback
- Uses `@dnd-kit/sortable` for drag-and-drop

### Deal Page Integration

- On load, fetch `deal_page_widgets` preference (default if none saved)
- Filter widgets where `visible: false`
- Sort by `order`
- Render via widget registry map: `{widget_id → component}`
- Refactor deal page from hardcoded layout to dynamic loop

### Default Config
New users / users without saved preferences get the current fixed layout order, with Manager Actions inserted after Deal Memo (order 4).

---

## Out of Scope
- Pipeline page widget config (future)
- Widget resize/column layout (future)
- Role-based widget defaults (future)
- Widget grouping/sections (future)

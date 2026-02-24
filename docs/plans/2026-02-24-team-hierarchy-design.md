# Team Hierarchy Design — VP, GM, Admin Roles

**Date:** 2026-02-24
**Status:** Approved

## Problem

The current system has 3 roles (`admin`, `team_lead`, `ic`) stored as JWT strings with zero enforcement. Team data lives as denormalized text fields on the Account table (`ae_owner`, `team_lead`, `team_name`). There's no User table, no Team table, and no data scoping. All users see all data.

A VP needs a portfolio roll-up across their team leads' teams. A GM needs full org visibility. The admin needs team management capabilities.

## Hierarchy

```
Admin (system)     — everything + user/team management
GM                 — all deals, all teams
VP                 — all deals across their TLs' teams
Team Lead          — their team's deals
IC                 — their own deals
```

Tree structure: GM Org → VP Divisions → TL Teams → ICs

## Data Model

### New: `users` table

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | PK |
| name | TEXT | Display name |
| email | TEXT | Unique, login identifier |
| role | TEXT | `admin`, `gm`, `vp`, `team_lead`, `ic` |
| team_id | TEXT FK → teams.id | Nullable for admin/gm |
| is_active | BOOLEAN | Soft delete |
| created_at | DATETIME | |

### New: `teams` table

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | PK |
| name | TEXT | e.g. "Enterprise East" |
| parent_id | TEXT FK → teams.id | Self-reference. NULL = root |
| leader_id | TEXT FK → users.id | TL, VP, or GM who leads this node |
| level | TEXT | `org`, `division`, `team` |
| created_at | DATETIME | |

### Modified: `accounts` table

- Add `owner_id TEXT FK → users.id` (replaces string `ae_owner`)
- Keep `ae_owner`, `team_lead`, `team_name` as read-only legacy during migration
- Backfill `owner_id` from existing `ae_owner` strings

### Tree Example

```
GM Org (level=org, leader=Roy)
├── Sales East (level=division, leader=VP Sarah)
│   ├── Enterprise (level=team, leader=TL Dan)
│   │   ├── IC: Alice
│   │   └── IC: Bob
│   └── Mid-Market (level=team, leader=TL Maya)
│       └── IC: Charlie
└── Sales West (level=division, leader=VP Jake)
    └── ...
```

## Data Scoping

Single helper function: `get_visible_user_ids(current_user) -> list[str]`

| Role | Scoping Rule |
|------|-------------|
| IC | `WHERE accounts.owner_id = current_user.id` |
| Team Lead | `WHERE accounts.owner_id IN (users on my team)` |
| VP | `WHERE accounts.owner_id IN (users on any team under my division)` |
| GM | No filter (all accounts) |
| Admin | No filter (all accounts) |

Applied at the service layer. All existing endpoints (`/api/accounts/`, `/api/dashboard/*`) automatically scope based on the logged-in user.

## API Changes

### New Endpoints

| Endpoint | Method | Purpose | Access |
|----------|--------|---------|--------|
| `/api/users/` | GET | List users | admin |
| `/api/users/` | POST | Create user | admin |
| `/api/users/{id}` | PUT | Update user | admin |
| `/api/teams/` | GET | List teams as tree | all (scoped) |
| `/api/teams/` | POST | Create team | admin |
| `/api/teams/{id}` | PUT | Update team | admin |
| `/api/teams/{id}/members` | GET | List team members | TL+ of that team |

### Modified Endpoints

All existing account/dashboard endpoints:
- Replace optional `?team=` parameter with automatic scoping via `get_scoped_user_ids()`
- Service layer receives visible user IDs, filters accordingly
- No endpoint signature changes needed for consumers

### Auth Changes

- `VALID_ROLES`: add `vp`, `gm` (5 total)
- JWT payload includes `user_id` (not just username/role)
- `get_current_user` returns full User object from DB

## Frontend Changes

### Dashboard (adapts by role, no new pages)

- **IC**: Their deals, pipeline, health scores (current behavior)
- **Team Lead**: Team's aggregated view (current behavior)
- **VP/GM**: Roll-up summary cards per team at top + team selector bar as filter chips. "All Teams" default. Click a team to drill down.
- **Admin**: Same as GM

### New Components

- **Team selector bar**: Filter chips showing teams, visible for VP/GM only
- **Roll-up summary cards**: Total pipeline, avg health, # at-risk per team

### New Page

- `/settings/teams` (admin only): Visual org tree, add/edit/move users and teams

### Login

- 5 roles in dropdown: IC, Team Lead, VP, GM, Admin

### Auth Context

- `AuthUser` adds `user_id` field
- New `usePermissions()` hook for role-based UI rendering

## Migration Strategy

1. Create `users` and `teams` tables
2. Seed initial users from distinct `ae_owner` / `team_lead` values in accounts
3. Build team tree from distinct `team_name` values
4. Backfill `accounts.owner_id` from matching users
5. Keep legacy string fields read-only until fully migrated

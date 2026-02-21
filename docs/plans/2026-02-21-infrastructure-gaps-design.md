# Design: Infrastructure Gaps — Config, Export, Cleanup

**Date:** 2026-02-21
**Status:** Implemented
**Spec References:** Technical Architecture Section 7 (directory structure), Section 7.5 (stage relevance), Section 7.9 (calibration), Section 6.7 (export)

## Changes

### 1. Config Directory (`config/`)

Created per spec Section 7 directory structure:

```
config/
├── agents.yml              # Agent registry: id, name, description, prompt_file
├── models.yml              # Model routing: agent → model, with env_override
├── stage_relevance.yml     # Agent-stage weight matrix (Section 7.5)
└── calibration/
    ├── v1.0.yml            # Calibration config (versioned)
    └── current.yml         # Symlink → v1.0.yml
```

**Design decisions:**
- `agents.yml` does NOT carry model assignments (those live in `models.yml` only)
- `models.yml` specifies `env_override` per agent, so env vars override YAML
- `sis/config.py` loads YAML first, then applies env var overrides
- `load_calibration_config()` reads from `config/calibration/current.yml` with legacy path fallback
- New loaders: `load_agents_config()`, `load_stage_relevance()`, `_load_models_config()`

### 2. Export Service (`sis/services/export_service.py`)

Per spec Section 6.7, two functions:

- `export_deal_brief(account_id, format)` — supports 3 brief styles:
  - `"structured"` — fixed template one-pager (P0-19 format 1)
  - `"narrative"` — 3-5 paragraph memo + structured fields (P0-19 format 2)
  - `"inspection"` — 3-5 inspection questions with evidence (P0-19 format 3)
- `export_forecast_report(team, format)` — AI vs IC weighted pipeline comparison

**Deviation from spec:** Returns `str` not `bytes` (Markdown only for POC). PDF deferred.

### 3. Stub Module Cleanup

Removed empty stub packages that duplicated functionality elsewhere:
- `sis/chat/` — backend will be `sis/services/query_service.py` (Phase A)
- `sis/dashboard/` — logic in `sis/services/dashboard_service.py`
- `sis/models/` — ORM in `sis/db/models.py`
- `sis/export/` — service in `sis/services/export_service.py`

Kept `sis/alerts/` stub — Week 7-8 deliverable.

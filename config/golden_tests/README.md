# Golden Test Fixtures

Each `.json` file in this directory is a golden test fixture — a snapshot of a deal assessment used for regression testing.

## Format

```json
{
  "fixture_id": "golden_001",
  "account_id": "uuid-here",
  "account_name": "Test Account",
  "created_at": "2026-02-21T00:00:00+00:00",
  "baseline": {
    "health_score": 72,
    "ai_forecast_category": "Best Case",
    "inferred_stage": 3,
    "overall_confidence": 0.78,
    "momentum_direction": "Improving"
  }
}
```

## Regression Gates

1. **Health Score Delta > 10** → FAIL
2. **Forecast Category Changed** → FAIL
3. **Stage Inference Changed** → WARN
4. **Confidence Dropped > 0.15** → WARN

## Creating Fixtures

Use the Golden Tests UI page or call `create_baseline(account_id)` from the testing module.

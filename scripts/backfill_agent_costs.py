"""Backfill cost_usd for existing agent_analyses rows.

For rows where cost_usd IS NULL but input_tokens and model_used are set,
calculates and fills cost using the standard pricing table.

Usage:
    python -m scripts.backfill_agent_costs [--dry-run]
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sis.db.session import get_session
from sis.db.models import AgentAnalysis
from sis.orchestrator.cost_tracker import calculate_cost


def backfill(dry_run: bool = False) -> None:
    with get_session() as session:
        rows = (
            session.query(AgentAnalysis)
            .filter(
                AgentAnalysis.cost_usd.is_(None),
                AgentAnalysis.input_tokens.isnot(None),
                AgentAnalysis.model_used.isnot(None),
            )
            .all()
        )

        print(f"Found {len(rows)} rows to backfill")
        if not rows:
            return

        updated = 0
        for row in rows:
            cost = calculate_cost(row.model_used, row.input_tokens, row.output_tokens or 0)
            if dry_run:
                print(f"  [DRY RUN] {row.agent_id} (run {row.analysis_run_id[:8]}...): "
                      f"{row.input_tokens}in/{row.output_tokens}out @ {row.model_used} = ${cost:.4f}")
            else:
                row.cost_usd = round(cost, 4)
            updated += 1

        if not dry_run:
            session.flush()

        print(f"{'Would update' if dry_run else 'Updated'} {updated} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill agent_analyses.cost_usd")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)

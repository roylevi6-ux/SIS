"""Backfill divergence_flag for existing assessments.

Compares account.sf_forecast_category vs assessment.ai_forecast_category
and sets divergence_flag + divergence_explanation for all latest assessments.

Usage:
    python -m scripts.backfill_divergence [--dry-run]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment


def backfill(dry_run: bool = False) -> None:
    with get_session() as session:
        assessments = (
            session.query(DealAssessment, Account)
            .join(Account, DealAssessment.account_id == Account.id)
            .filter(DealAssessment.ai_forecast_category.isnot(None))
            .all()
        )

        updated = 0
        divergent = 0
        for assessment, account in assessments:
            sf = account.sf_forecast_category
            ai = assessment.ai_forecast_category

            # "At Risk" is SIS-only (not a SF category) — treat as aligned with SF "Upside"
            is_match = (sf == ai) or (ai == "At Risk" and sf == "Upside")
            if sf and ai and not is_match:
                new_flag = 1
                new_explanation = (
                    f"AI forecasts '{ai}' but rep set '{sf}' in Salesforce."
                )
                divergent += 1
            else:
                new_flag = 0
                new_explanation = None

            if assessment.divergence_flag != new_flag:
                if not dry_run:
                    assessment.divergence_flag = new_flag
                    assessment.divergence_explanation = new_explanation
                updated += 1
                print(
                    f"  {'[DRY RUN] ' if dry_run else ''}"
                    f"{account.account_name}: SF={sf}, AI={ai} → flag={new_flag}"
                )

        if not dry_run:
            session.commit()

        print(f"\nTotal assessments scanned: {len(assessments)}")
        print(f"Divergent: {divergent}")
        print(f"Updated: {updated}")
        if dry_run:
            print("(Dry run — no changes written)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)

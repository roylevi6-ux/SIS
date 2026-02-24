"""update_forecast_categories

Migrate forecast categories from 6 → 4:
- "Best Case" → "Realistic"
- "Pipeline" → "Realistic"
- "No Decision Risk" → "At Risk"

Revision ID: c5e7f9a1b3d6
Revises: b4d6e8f0a2c4
Create Date: 2026-02-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c5e7f9a1b3d6'
down_revision: Union[str, Sequence[str], None] = 'b4d6e8f0a2c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate old forecast categories to new 4-category model."""
    # accounts.ic_forecast_category
    op.execute("UPDATE accounts SET ic_forecast_category = 'Realistic' WHERE ic_forecast_category IN ('Best Case', 'Pipeline')")
    op.execute("UPDATE accounts SET ic_forecast_category = 'At Risk' WHERE ic_forecast_category = 'No Decision Risk'")

    # deal_assessments.ai_forecast_category
    op.execute("UPDATE deal_assessments SET ai_forecast_category = 'Realistic' WHERE ai_forecast_category IN ('Best Case', 'Pipeline')")
    op.execute("UPDATE deal_assessments SET ai_forecast_category = 'At Risk' WHERE ai_forecast_category = 'No Decision Risk'")


def downgrade() -> None:
    """Reverse is lossy — Best Case and Pipeline both mapped to Realistic.

    Best-effort: map Realistic back to Pipeline (the more conservative choice).
    """
    op.execute("UPDATE accounts SET ic_forecast_category = 'Pipeline' WHERE ic_forecast_category = 'Realistic'")
    op.execute("UPDATE deal_assessments SET ai_forecast_category = 'Pipeline' WHERE ai_forecast_category = 'Realistic'")

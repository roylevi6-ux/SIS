"""add_missing_columns

Add three columns that exist in models.py but were missing from migrations:
- accounts.prior_contract_value (Float, nullable)
- transcripts.call_title (Text, nullable)
- analysis_runs.deal_type_at_run (Text, nullable)

Revision ID: b4d6e8f0a2c4
Revises: a3c7e8f12d45
Create Date: 2026-02-23 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d6e8f0a2c4'
down_revision: Union[str, Sequence[str], None] = 'a3c7e8f12d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add prior_contract_value, call_title, and deal_type_at_run columns."""
    op.add_column('accounts', sa.Column('prior_contract_value', sa.Float(), nullable=True))
    op.add_column('transcripts', sa.Column('call_title', sa.Text(), nullable=True))
    op.add_column('analysis_runs', sa.Column('deal_type_at_run', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove the three columns."""
    op.drop_column('analysis_runs', 'deal_type_at_run')
    op.drop_column('transcripts', 'call_title')
    op.drop_column('accounts', 'prior_contract_value')

"""add_agent_timing_columns

Add elapsed_seconds and prep_seconds columns to agent_analyses table
for persisting per-agent timing data to the DB.

Revision ID: f8a2b3c4d5e6
Revises: d6f8a0b2c4e7
Create Date: 2026-03-02 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'd6f8a0b2c4e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add elapsed_seconds and prep_seconds to agent_analyses."""
    op.add_column('agent_analyses', sa.Column('elapsed_seconds', sa.Float(), nullable=True))
    op.add_column('agent_analyses', sa.Column('prep_seconds', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove elapsed_seconds and prep_seconds from agent_analyses."""
    op.drop_column('agent_analyses', 'prep_seconds')
    op.drop_column('agent_analyses', 'elapsed_seconds')

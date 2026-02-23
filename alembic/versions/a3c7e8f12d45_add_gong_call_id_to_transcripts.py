"""add_gong_call_id_to_transcripts

Revision ID: a3c7e8f12d45
Revises: 188fe591b9f2
Create Date: 2026-02-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c7e8f12d45'
down_revision: Union[str, Sequence[str], None] = '188fe591b9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add gong_call_id column and unique constraint to transcripts."""
    op.add_column('transcripts', sa.Column('gong_call_id', sa.Text(), nullable=True))
    # SQLite doesn't support ADD CONSTRAINT, so we create a unique index instead
    op.create_index(
        'uq_transcript_gong_call',
        'transcripts',
        ['account_id', 'gong_call_id'],
        unique=True,
    )


def downgrade() -> None:
    """Remove gong_call_id column."""
    op.drop_index('uq_transcript_gong_call', table_name='transcripts')
    op.drop_column('transcripts', 'gong_call_id')

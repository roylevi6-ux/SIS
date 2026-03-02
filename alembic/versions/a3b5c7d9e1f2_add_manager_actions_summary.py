"""Add manager_actions_summary to deal_assessments

Revision ID: a3b5c7d9e1f2
Revises: d6f8a0b2c4e7
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'a3b5c7d9e1f2'
down_revision: str = 'd6f8a0b2c4e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('deal_assessments', sa.Column('manager_actions_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('deal_assessments', 'manager_actions_summary')

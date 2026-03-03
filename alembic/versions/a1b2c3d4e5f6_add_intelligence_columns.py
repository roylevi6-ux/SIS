"""add deal intelligence columns

Revision ID: a1b2c3d4e5f6
Revises: f8a2b3c4d5e6
Create Date: 2026-03-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f8a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deal_assessments", sa.Column("manager_brief", sa.Text(), nullable=True))
    op.add_column("deal_assessments", sa.Column("attention_level", sa.Text(), nullable=True))
    op.add_column("deal_assessments", sa.Column("deal_memo_sections", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("deal_assessments", "deal_memo_sections")
    op.drop_column("deal_assessments", "attention_level")
    op.drop_column("deal_assessments", "manager_brief")

"""add_user_preferences

Revision ID: d6f8a0b2c4e7
Revises: e7a1b2c3d4f5
Create Date: 2026-03-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6f8a0b2c4e7'
down_revision: Union[str, Sequence[str], None] = 'e7a1b2c3d4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('preference_key', sa.Text(), nullable=False),
        sa.Column('preference_value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'preference_key', name='uq_user_preference'),
    )
    op.create_index('ix_user_preferences_user', 'user_preferences', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_preferences_user', table_name='user_preferences')
    op.drop_table('user_preferences')

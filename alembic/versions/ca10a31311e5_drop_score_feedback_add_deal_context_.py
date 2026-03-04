"""drop score_feedback add deal_context_entries

Revision ID: ca10a31311e5
Revises: b5c6d7e8f9a0
Create Date: 2026-03-04 08:03:10.437091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca10a31311e5'
down_revision: Union[str, Sequence[str], None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old score_feedback table
    op.drop_index("ix_score_feedback_account", table_name="score_feedback")
    op.drop_table("score_feedback")

    # Create the new deal_context_entries table
    op.create_table(
        "deal_context_entries",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("account_id", sa.Text(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("author_id", sa.Text(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("superseded_by", sa.Text(), sa.ForeignKey("deal_context_entries.id"), nullable=True),
        sa.Column("is_active", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_deal_context_account_question", "deal_context_entries", ["account_id", "question_id", "created_at"])
    op.create_index("ix_deal_context_account_latest", "deal_context_entries", ["account_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_deal_context_account_latest", table_name="deal_context_entries")
    op.drop_index("ix_deal_context_account_question", table_name="deal_context_entries")
    op.drop_table("deal_context_entries")

    # Recreate score_feedback for rollback
    op.create_table(
        "score_feedback",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("account_id", sa.Text(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("deal_assessment_id", sa.Text(), sa.ForeignKey("deal_assessments.id"), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("feedback_date", sa.Text(), nullable=False),
        sa.Column("health_score_at_time", sa.Integer(), nullable=False),
        sa.Column("disagreement_direction", sa.Text(), nullable=False),
        sa.Column("reason_category", sa.Text(), nullable=False),
        sa.Column("free_text", sa.Text(), nullable=True),
        sa.Column("off_channel_activity", sa.Integer(), server_default="0"),
        sa.Column("resolution", sa.Text(), server_default="pending"),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_score_feedback_account", "score_feedback", ["account_id", "created_at"])

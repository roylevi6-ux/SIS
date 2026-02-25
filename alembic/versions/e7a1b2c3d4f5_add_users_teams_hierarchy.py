"""add_users_teams_hierarchy

Retroactive migration: documents the users table, teams table,
accounts.owner_id column, and related indexes that were created
outside Alembic during team hierarchy development.

All operations are guarded with IF NOT EXISTS / inspector checks
so this migration is safe to run on databases where these objects
already exist (current state) AND on fresh databases built from
scratch via `alembic upgrade head`.

Revision ID: e7a1b2c3d4f5
Revises: d6f8a2b4c5e7
Create Date: 2026-02-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7a1b2c3d4f5"
down_revision: Union[str, None] = "d6f8a2b4c5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def _index_exists(index_name: str) -> bool:
    """Check if an index exists (across all tables)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in inspector.get_table_names():
        for idx in inspector.get_indexes(table):
            if idx["name"] == index_name:
                return True
    return False


def upgrade() -> None:
    # ── 1. Create teams table (must come before users due to FK) ────────
    if not _table_exists("teams"):
        op.create_table(
            "teams",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("parent_id", sa.Text(), nullable=True),
            sa.Column("leader_id", sa.Text(), nullable=True),
            sa.Column("level", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["parent_id"], ["teams.id"]),
            # leader_id FK added after users table exists
        )

    # ── 2. Create users table ───────────────────────────────────────────
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=False),
            sa.Column("role", sa.Text(), nullable=False),
            sa.Column("team_id", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Integer(), default=1),
            sa.Column("created_at", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        )

    # ── 3. Add owner_id to accounts ─────────────────────────────────────
    if not _column_exists("accounts", "owner_id"):
        op.add_column(
            "accounts",
            sa.Column("owner_id", sa.Text(), sa.ForeignKey("users.id"), nullable=True),
        )

    # ── 4. Create indexes ───────────────────────────────────────────────
    if not _index_exists("ix_users_email"):
        op.create_index("ix_users_email", "users", ["email"])
    if not _index_exists("ix_users_role"):
        op.create_index("ix_users_role", "users", ["role"])
    if not _index_exists("ix_teams_parent"):
        op.create_index("ix_teams_parent", "teams", ["parent_id"])
    if not _index_exists("ix_teams_level"):
        op.create_index("ix_teams_level", "teams", ["level"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_teams_level", table_name="teams")
    op.drop_index("ix_teams_parent", table_name="teams")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")

    # Drop owner_id from accounts
    # NOTE: SQLite doesn't support DROP COLUMN natively before 3.35.0.
    # For safety, we use batch mode.
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("owner_id")

    # Drop tables (users first due to FK dependencies)
    op.drop_table("users")
    op.drop_table("teams")

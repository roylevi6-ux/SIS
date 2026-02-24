"""rename_stage_names_salesforce

Rename deal stage names to match Riskified's Salesforce vocabulary.
Maps both the 7-stage Riskified internal names AND the 5-stage generic
names (from seed data) to the new Salesforce-aligned names.

Only migrates deal_assessments.stage_name (column). Historical JSON in
agent_analyses.findings is left unchanged — acceptable for POC data.

Revision ID: d6f8a2b4c5e7
Revises: c5e7f9a1b3d6
Create Date: 2026-02-24 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d6f8a2b4c5e7"
down_revision: Union[str, None] = "c5e7f9a1b3d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Old name → New name mapping
# Covers both 7-stage Riskified names and 5-stage generic seed names
STAGE_RENAMES = [
    # 7-stage Riskified internal names
    ("SQL", "Qualify"),
    ("Metrics Validation", "Establish Business Case"),
    ("Discovery & Validation", "Establish Business Case"),
    ("Commercial Build & Present", "Scope"),
    ("Stakeholder Alignment", "Proposal"),
    ("Legal", "Negotiate"),
    ("Integration", "Contract"),
    ("Onboarding", "Implement"),
    # 5-stage generic names (from seed data / tests)
    ("Qualification", "Qualify"),
    ("Discovery", "Establish Business Case"),
    ("Evaluation", "Scope"),
    # "Proposal" → "Proposal" (no change needed)
    ("Closing", "Negotiate"),
    # Legacy names that may appear in test data
    ("Negotiation", "Negotiate"),
]


def upgrade() -> None:
    for old_name, new_name in STAGE_RENAMES:
        op.execute(
            f"UPDATE deal_assessments SET stage_name = '{new_name}' "
            f"WHERE stage_name = '{old_name}'"
        )


def downgrade() -> None:
    # Reverse mapping — restore to 7-stage Riskified internal names
    REVERSE = [
        ("Qualify", "SQL"),
        ("Establish Business Case", "Metrics Validation"),
        ("Scope", "Commercial Build & Present"),
        ("Proposal", "Stakeholder Alignment"),
        ("Negotiate", "Legal"),
        ("Contract", "Integration"),
        ("Implement", "Onboarding"),
    ]
    for new_name, old_name in REVERSE:
        op.execute(
            f"UPDATE deal_assessments SET stage_name = '{old_name}' "
            f"WHERE stage_name = '{new_name}'"
        )

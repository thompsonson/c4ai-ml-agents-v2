"""Remove token usage tracking

Revision ID: f3a8b2c9d1e4
Revises: 27e054905f07
Create Date: 2025-09-30 15:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f3a8b2c9d1e4"
down_revision = "27e054905f07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove token_usage_json column from evaluation_question_results table."""
    op.drop_column("evaluation_question_results", "token_usage_json")


def downgrade() -> None:
    """Re-add token_usage_json column."""
    op.add_column(
        "evaluation_question_results",
        sa.Column("token_usage_json", sa.Text(), nullable=True),
    )

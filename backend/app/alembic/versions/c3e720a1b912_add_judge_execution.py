"""Add hidden judge tests and recoverable submission execution. """

import sqlalchemy as sa
from alembic import op

revision = "c3e720a1b912"
down_revision = "91d6b2a4e830"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "problem_bank",
        sa.Column("hidden_test_cases", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column("submissions", sa.Column("execution_id", sa.String(), nullable=True))
    op.execute(
        """UPDATE submissions SET status = CASE lower(status)
        WHEN 'accepted' THEN 'PASSED' WHEN 'passed' THEN 'PASSED'
        WHEN 'rejected' THEN 'FAILED' WHEN 'failed' THEN 'FAILED'
        WHEN 'runtime_error' THEN 'RUNTIME_ERROR'
        WHEN 'time_limit_exceeded' THEN 'TIME_LIMIT_EXCEEDED'
        ELSE 'QUEUED' END"""
    )
    op.alter_column("submissions", "status", nullable=False, server_default="QUEUED")
    op.create_index("ix_submissions_status", "submissions", ["status"])


def downgrade():
    op.drop_index("ix_submissions_status", table_name="submissions")
    op.alter_column("submissions", "status", nullable=True, server_default=None)
    op.drop_column("submissions", "execution_id")
    op.drop_column("problem_bank", "hidden_test_cases")

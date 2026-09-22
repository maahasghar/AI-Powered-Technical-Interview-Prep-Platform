"""Track coaching independently from deterministic judge results."""

import sqlalchemy as sa
from alembic import op

revision = "d14a3e91c602"
down_revision = "c3e720a1b912"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "submission_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("execution_id", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("submission_id", "stage", name="uq_feedback_stage"),
    )
    op.create_index(
        "ix_submission_feedback_submission_id", "submission_feedback", ["submission_id"]
    )
    op.create_index("ix_submission_feedback_status", "submission_feedback", ["status"])


def downgrade():
    op.drop_table("submission_feedback")

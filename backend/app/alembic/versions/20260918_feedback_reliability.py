"""Add feedback traceability, usage, and reliability metadata."""

import sqlalchemy as sa
from alembic import op

revision = "20260918_feedback_reliability"
down_revision = "d14a3e91c602"
branch_labels = None
depends_on = None


def upgrade():
    for name, column in [
        ("provider", sa.String()),
        ("model", sa.String()),
        ("prompt_version", sa.String()),
        ("schema_version", sa.String()),
        ("source", sa.String()),
        ("input_tokens", sa.Integer()),
        ("output_tokens", sa.Integer()),
        ("estimated_cost_usd", sa.String()),
        ("generation_ms", sa.Integer()),
        ("attempts", sa.Integer()),
        ("error_type", sa.String()),
        ("generated_at", sa.DateTime(timezone=True)),
    ]:
        op.add_column("submission_feedback", sa.Column(name, column, nullable=True))


def downgrade():
    for name in (
        "error_type",
        "attempts",
        "generation_ms",
        "estimated_cost_usd",
        "output_tokens",
        "input_tokens",
        "source",
        "schema_version",
        "prompt_version",
        "model",
        "provider",
        "generated_at",
    ):
        op.drop_column("submission_feedback", name)

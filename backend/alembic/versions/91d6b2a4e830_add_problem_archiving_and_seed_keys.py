"""Add problem archiving and stable seed keys."""

import sqlalchemy as sa
from alembic import op

revision = "91d6b2a4e830"
down_revision = "7f4a1d2c9e8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "problem_bank",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("problem_bank", sa.Column("seed_key", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_problem_bank_seed_key", "problem_bank", ["seed_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_problem_bank_seed_key", "problem_bank", type_="unique")
    op.drop_column("problem_bank", "seed_key")
    op.drop_column("problem_bank", "is_active")

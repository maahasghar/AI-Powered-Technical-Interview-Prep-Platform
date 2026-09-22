"""harden refresh tokens

Revision ID: 7f4a1d2c9e8b
Revises: 2c6c2d6f8c1a
Create Date: 2026-09-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "7f4a1d2c9e8b"
down_revision: str | None = "2c6c2d6f8c1a"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.alter_column("auth_tokens", "refresh_token", new_column_name="token_hash")
    op.execute(
        "UPDATE auth_tokens "
        "SET token_hash = encode(digest(token_hash, 'sha256'), 'hex')"
    )
    op.add_column("auth_tokens", sa.Column("family_id", sa.String(), nullable=True))
    op.add_column("auth_tokens", sa.Column("replaced_at", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE auth_tokens "
        "SET family_id = md5(random()::text || clock_timestamp()::text) "
        "WHERE family_id IS NULL"
    )
    op.alter_column("auth_tokens", "family_id", nullable=False)
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"])
    op.create_index("ix_auth_tokens_family_id", "auth_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_tokens_family_id", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_token_hash", table_name="auth_tokens")
    op.drop_column("auth_tokens", "replaced_at")
    op.drop_column("auth_tokens", "family_id")
    op.alter_column("auth_tokens", "token_hash", new_column_name="refresh_token")

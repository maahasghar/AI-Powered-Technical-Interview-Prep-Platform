# Add project root to sys.path
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import engine_from_config

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# ---- ADD THIS (this lets Alembic auto-detect schema changes) ----
from app.core.config import settings
from app.domain.auth import models as auth_models  # noqa: F401
from app.domain.auth import token_models as account_token_models  # noqa: F401
from app.domain.problems import models as problem_models  # noqa: F401
from app.domain.submissions import models as submission_models  # noqa: F401
from app.domain.user import models as user_models  # noqa: F401
from app.infrastructure.db import Base

# -------------------

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.DATABASE_URL,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# Add project root to sys.path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
fileConfig(config.config_file_name)

# ---- ADD THIS (this lets Alembic auto-detect schema changes) ----
from app.infrastructure.db import Base
from app.domain.auth.models import User
from app.domain.auth.models import AuthToken
from app.domain.user.models import UserProfile
from app.domain.problems.models import Problem
# -------------------

target_metadata = Base.metadata

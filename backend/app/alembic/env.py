# Add project root to sys.path
import os
import sys
from logging.config import fileConfig

from alembic import context

# ---- ADD THIS (this lets Alembic auto-detect schema changes) ----
from app.infrastructure.db import Base

# -------------------

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

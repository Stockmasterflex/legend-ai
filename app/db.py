"""
Database engine factory for Legend AI API.

Provides a minimal SQLAlchemy engine using `DATABASE_URL`. This is used by
readiness probes and other modules that only need a lightweight connection.
"""

from sqlalchemy import create_engine

from .config import get_database_url

# Use pool_pre_ping to avoid stale connections in serverless/pooled envs.
engine = create_engine(get_database_url(), pool_pre_ping=True, future=True)

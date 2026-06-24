"""
SQLAlchemy engine factory for direct PostgreSQL access.

Use this module for heavy workloads that bypass the PostgREST/Supabase SDK:
- ETL bulk inserts/upserts (100k+ rows)
- Analytics queries with CTEs or window functions
- Bulk deletes / offboarding
- pg_cron-compatible heavy jobs

DO NOT use for:
- Lightweight CRUD — use get_supabase_client() instead
- Frontend API responses — use the pooler (DATABASE_URL)
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pool configs by workload type
# ---------------------------------------------------------------------------

_POOLER_CONFIG = dict(
    # port 6543 — transaction mode — fast requests, frontend, agent reads
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=600,       # 10 min — pooler drops idle connections fast
    connect_args={"connect_timeout": 10},
)

_DIRECT_CONFIG = dict(
    # port 5432 — session mode — ETL, bulk ops, long-running analytics
    poolclass=QueuePool,
    pool_size=2,            # session mode has very few slots — keep small
    max_overflow=1,
    pool_timeout=60,
    pool_pre_ping=True,
    pool_recycle=1800,      # 30 min
    connect_args={"connect_timeout": 15},
)


@lru_cache(maxsize=1)
def get_pooler_engine() -> Engine:
    """Engine for the transaction-mode pooler (port 6543). Fast requests."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    engine = create_engine(url, **_POOLER_CONFIG)
    _register_listeners(engine, label="pooler")
    logger.info("SQLAlchemy pooler engine created (port 6543)")
    return engine


@lru_cache(maxsize=1)
def get_direct_engine() -> Engine:
    """
    Engine for the direct session-mode connection (port 5432).
    Falls back to pooler engine if DATABASE_URL_DIRECT is not set.
    """
    url = os.environ.get("DATABASE_URL_DIRECT") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_DIRECT and DATABASE_URL are both unset")
    if "5432" not in url and "DATABASE_URL_DIRECT" not in os.environ:
        logger.warning(
            "DATABASE_URL_DIRECT not set — falling back to pooler. "
            "Heavy jobs may exhaust pooler connections."
        )
    engine = create_engine(url, **_DIRECT_CONFIG)
    _register_listeners(engine, label="direct")
    logger.info("SQLAlchemy direct engine created (port 5432)")
    return engine


def _register_listeners(engine: Engine, label: str) -> None:
    """Log slow queries and connection events for observability."""

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, _) -> None:
        logger.debug(f"[{label}] New DB connection opened")

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_conn, _, __) -> None:  # noqa: F811
        logger.debug(f"[{label}] Connection checked out from pool")

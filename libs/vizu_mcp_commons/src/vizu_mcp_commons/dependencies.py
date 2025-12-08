"""
Shared dependency injection utilities for MCP services.

Provides centralized dependency management with connection pooling
and proper cleanup.
"""

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import AsyncGenerator, Optional, Callable

import redis

logger = logging.getLogger(__name__)


# =============================================================================
# SINGLETON POOLS
# =============================================================================

_redis_pool: Optional[redis.ConnectionPool] = None


def _get_redis_pool() -> redis.ConnectionPool:
    """Get or create shared Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)
        logger.info(f"Redis pool created: {redis_url}")
    return _redis_pool


def get_redis_client() -> redis.Redis:
    """
    Get Redis client from shared pool.

    Returns:
        Redis client instance
    """
    pool = _get_redis_pool()
    return redis.Redis(connection_pool=pool)


def get_db_session():
    """
    Get database session from vizu_db_connector.

    Returns:
        SQLAlchemy session
    """
    from vizu_db_connector.database import SessionLocal
    return SessionLocal()


def get_context_service():
    """
    Create a new ContextService instance with DB session and Redis.

    Note: Caller is responsible for closing the DB session.

    Returns:
        ContextService instance
    """
    from vizu_context_service.context_service import ContextService
    from vizu_context_service.redis_service import RedisService

    db = get_db_session()
    redis_client = get_redis_client()
    redis_service = RedisService(redis_client=redis_client)

    return ContextService(
        db_session=db,
        cache_service=redis_service,
        use_supabase=False,
    )


# =============================================================================
# ASYNC CONTEXT MANAGERS
# =============================================================================


@asynccontextmanager
async def context_service_context() -> AsyncGenerator:
    """
    Async context manager for ContextService with proper cleanup.

    Usage:
        async with context_service_context() as ctx_service:
            context = await ctx_service.get_client_context_by_id(client_id)
    """
    from vizu_context_service.context_service import ContextService
    from vizu_context_service.redis_service import RedisService

    db = get_db_session()
    redis_client = get_redis_client()
    redis_service = RedisService(redis_client=redis_client)

    ctx_service = ContextService(
        db_session=db,
        cache_service=redis_service,
        use_supabase=False,
    )

    try:
        yield ctx_service
    finally:
        try:
            db.close()
        except Exception as e:
            logger.warning(f"Error closing DB session: {e}")


@asynccontextmanager
async def db_session_context() -> AsyncGenerator:
    """
    Async context manager for database session.

    Usage:
        async with db_session_context() as db:
            result = db.query(Model).all()
    """
    db = get_db_session()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception as e:
            logger.warning(f"Error closing DB session: {e}")


# =============================================================================
# DEPENDENCY CONTAINER
# =============================================================================


@dataclass
class DependencyContainer:
    """
    Container for managing shared dependencies.

    Provides a central place to configure and access all dependencies
    needed by MCP services.

    Usage:
        container = DependencyContainer()
        ctx_service = container.get_context_service()
    """

    _context_service_factory: Optional[Callable] = None
    _redis_factory: Optional[Callable] = None
    _db_factory: Optional[Callable] = None
    _custom_factories: dict = field(default_factory=dict)

    def set_context_service_factory(self, factory: Callable) -> None:
        """Override context service factory."""
        self._context_service_factory = factory

    def set_redis_factory(self, factory: Callable) -> None:
        """Override Redis factory."""
        self._redis_factory = factory

    def set_db_factory(self, factory: Callable) -> None:
        """Override database factory."""
        self._db_factory = factory

    def register(self, name: str, factory: Callable) -> None:
        """Register a custom dependency factory."""
        self._custom_factories[name] = factory

    def get_context_service(self):
        """Get context service instance."""
        if self._context_service_factory:
            return self._context_service_factory()
        return get_context_service()

    def get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if self._redis_factory:
            return self._redis_factory()
        return get_redis_client()

    def get_db_session(self):
        """Get database session."""
        if self._db_factory:
            return self._db_factory()
        return get_db_session()

    def get(self, name: str):
        """Get custom dependency by name."""
        factory = self._custom_factories.get(name)
        if factory:
            return factory()
        raise KeyError(f"No dependency registered with name: {name}")


# Default global container
_default_container: Optional[DependencyContainer] = None


def get_default_container() -> DependencyContainer:
    """Get or create default dependency container."""
    global _default_container
    if _default_container is None:
        _default_container = DependencyContainer()
    return _default_container


def configure_container(container: DependencyContainer) -> None:
    """Set the default dependency container."""
    global _default_container
    _default_container = container


# =============================================================================
# CLEANUP UTILITIES
# =============================================================================


def cleanup_pools() -> None:
    """
    Cleanup all connection pools.

    Call this during application shutdown.
    """
    global _redis_pool
    if _redis_pool is not None:
        try:
            _redis_pool.disconnect()
            logger.info("Redis pool disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting Redis pool: {e}")
        _redis_pool = None


async def async_cleanup() -> None:
    """
    Async cleanup for graceful shutdown.
    """
    cleanup_pools()

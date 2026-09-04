"""Redis and Arq connection pool management."""

from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Return a shared Arq Redis pool for enqueuing jobs."""
    global _pool
    if _pool is None:
        safe_url = settings.redis_url.replace("localhost", "127.0.0.1")
        redis_settings = RedisSettings.from_dsn(safe_url)
        redis_settings.conn_timeout = 5
        _pool = await create_pool(redis_settings)
    return _pool


async def close_arq_pool() -> None:
    """Close the shared Arq Redis pool."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None

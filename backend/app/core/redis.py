"""Redis and Arq connection pool management."""

from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings

_pool: ArqRedis | None = None


def clean_redis_url(url: str) -> str:
    """Strip any accidental 'redis-cli --tls -u' prefix from connection string."""
    clean = url.strip()
    if "-u " in clean:
        clean = clean.split("-u ", 1)[1].strip()
    elif clean.startswith("redis-cli"):
        clean = clean.replace("redis-cli", "", 1).strip()
    return clean.replace("localhost", "127.0.0.1")


async def get_arq_pool() -> ArqRedis:
    """Return a shared Arq Redis pool for enqueuing jobs."""
    global _pool
    if _pool is None:
        safe_url = clean_redis_url(settings.redis_url)
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

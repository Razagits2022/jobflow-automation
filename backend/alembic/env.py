"""Alembic environment configuration.

Uses the async engine from app.db.session and imports all models via
app.models so that autogenerate can detect schema changes.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

import app.models  # noqa: F401 — registers all models on Base.metadata
from alembic import context

# ---------------------------------------------------------------------------
# Import models so their metadata is registered on Base before autogenerate
# ---------------------------------------------------------------------------
from app.db.base import Base

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_connection_params() -> tuple[str, dict[str, Any]]:
    """Get normalized DB URL and connect_args for migrations.

    Prefers DATABASE_DIRECT_URL if set (direct connection, port 5432) for DDL migrations;
    falls back to DATABASE_URL (Session-mode pooler). Never uses Transaction mode.
    Applies the same scheme normalization and SSL handling as app.db.session.
    """
    from app.core.config import settings
    from app.db.session import normalize_asyncpg_url

    raw_url = settings.database_direct_url or settings.database_url
    return normalize_asyncpg_url(raw_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection, emit SQL to stdout)."""
    url, _ = _get_connection_params()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode against the live database."""
    url, connect_args = _get_connection_params()
    engine = create_async_engine(url, connect_args=connect_args, echo=False)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


def _do_run_migrations(connection: AsyncConnection) -> None:  # type: ignore[type-arg]
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

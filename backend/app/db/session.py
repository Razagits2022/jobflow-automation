"""Async SQLAlchemy engine and session factory.

Import ``AsyncSessionLocal`` to create database sessions.
In FastAPI routes, use the ``get_db`` dependency from ``app.api.deps``.
"""

from __future__ import annotations

import ssl
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def normalize_asyncpg_url(raw_url: str) -> tuple[str, dict[str, Any]]:
    """Normalize a database URL for asyncpg and prepare connect_args with SSL.

    1. Normalizes scheme: replace 'postgresql://' and 'postgres://' with 'postgresql+asyncpg://'.
    2. Strips 'sslmode' query param from the URL; asyncpg does not parse it.
    3. Creates an ssl.create_default_context() with check_hostname=False and
       verify_mode=ssl.CERT_NONE (Supabase pooler certs fail strict verification on Windows).
    4. Returns tuple of (normalized_url, {"ssl": ctx}).
    """
    parsed = urlsplit(raw_url)

    # Normalize scheme to postgresql+asyncpg
    scheme = parsed.scheme
    if scheme in ("postgresql", "postgres", "postgresql+asyncpg"):
        scheme = "postgresql+asyncpg"

    # Strip sslmode from query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    query_params.pop("sslmode", None)
    clean_query = urlencode(query_params, doseq=True)

    normalized_url = urlunsplit(
        (
            scheme,
            parsed.netloc,
            parsed.path,
            clean_query,
            parsed.fragment,
        )
    )

    # Supabase pooler requires TLS, but cert chain fails strict verification on Windows
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connect_args: dict[str, Any] = {"ssl": ctx}

    if parsed.port == 6543:
        # PgBouncer transaction mode cannot handle prepared statement caching
        connect_args["statement_cache_size"] = 0

    return normalized_url, connect_args


url, connect_args = normalize_asyncpg_url(settings.database_url)

# Detect if using PgBouncer transaction pooler (port 6543)
parsed_url = urlsplit(url)
is_transaction_pooler = (parsed_url.port == 6543)

if is_transaction_pooler:
    # ---------------------------------------------------------------------------
    # Transaction mode (port 6543):
    # PgBouncer routes transactions dynamically; use NullPool and disable prepared statements.
    # ---------------------------------------------------------------------------
    from sqlalchemy.pool import NullPool

    engine: AsyncEngine = create_async_engine(
        url,
        poolclass=NullPool,
        connect_args=connect_args,
        echo=settings.db_echo,
    )
else:
    # ---------------------------------------------------------------------------
    # Session mode (port 5432) or direct connection:
    # Use conservative pool limits to respect Supabase free-tier limits (15 total connections).
    # ---------------------------------------------------------------------------
    engine = create_async_engine(
        url,
        connect_args=connect_args,
        echo=settings.db_echo,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=60,
        pool_timeout=30,
    )


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

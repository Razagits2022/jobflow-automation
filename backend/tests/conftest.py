"""Pytest configuration and fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from app.db.session import engine


@pytest.fixture(autouse=True)
async def cleanup_db_engine() -> AsyncGenerator[None, None]:
    """Dispose the global SQLAlchemy engine after each test to release loop-bound connections."""
    yield
    await engine.dispose()

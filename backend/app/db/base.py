"""SQLAlchemy declarative base shared by all models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Import and subclass this in every model module. Alembic's env.py
    imports ``Base.metadata`` to autogenerate migrations.
    """

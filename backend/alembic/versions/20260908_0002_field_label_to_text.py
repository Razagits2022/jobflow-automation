"""Alter field_results.field_label to Text.

Revision ID: 20260908_0002
Revises: 20260904_0001
Create Date: 2026-09-08 23:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260908_0002"
down_revision: str | None = "20260904_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "field_results",
        "field_label",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "field_results",
        "field_label",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )

"""Initial schema: candidates, resumes, job_postings, application_runs, field_results.

Revision ID: 20260904_0001
Revises:
Create Date: 2026-09-04 21:55:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260904_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # candidates
    # -----------------------------------------------------------------------
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_candidates_email"), "candidates", ["email"], unique=True)

    # -----------------------------------------------------------------------
    # resumes
    # -----------------------------------------------------------------------
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resumes_candidate_id"), "resumes", ["candidate_id"], unique=False)

    # -----------------------------------------------------------------------
    # job_postings
    # -----------------------------------------------------------------------
    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_normalized", sa.String(length=2048), nullable=False),
        sa.Column("ats_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_postings_url_normalized"), "job_postings", ["url_normalized"], unique=False
    )

    # -----------------------------------------------------------------------
    # application_runs
    # -----------------------------------------------------------------------
    op.create_table(
        "application_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="QUEUED", nullable=False),
        sa.Column("confirmation_artifact_key", sa.Text(), nullable=True),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_runs_candidate_id"), "application_runs", ["candidate_id"], unique=False
    )
    op.create_index(
        op.f("ix_application_runs_job_id"), "application_runs", ["job_id"], unique=False
    )

    # -----------------------------------------------------------------------
    # field_results
    # -----------------------------------------------------------------------
    op.create_table(
        "field_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_label", sa.String(length=255), nullable=False),
        sa.Column("mapped_value", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="filled", nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["application_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_field_results_run_id"), "field_results", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_field_results_run_id"), table_name="field_results")
    op.drop_table("field_results")
    op.drop_index(op.f("ix_application_runs_job_id"), table_name="application_runs")
    op.drop_index(op.f("ix_application_runs_candidate_id"), table_name="application_runs")
    op.drop_table("application_runs")
    op.drop_index(op.f("ix_job_postings_url_normalized"), table_name="job_postings")
    op.drop_table("job_postings")
    op.drop_index(op.f("ix_resumes_candidate_id"), table_name="resumes")
    op.drop_table("resumes")
    op.drop_index(op.f("ix_candidates_email"), table_name="candidates")
    op.drop_table("candidates")

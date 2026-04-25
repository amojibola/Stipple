"""add expired job status

Revision ID: bb9900112233
Revises: ff0077889900
Create Date: 2026-04-24 00:00:00.000000

"""
from alembic import op

revision = "bb9900112233"
down_revision = "ff0077889900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_jobs_status", "jobs")
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        "status IN ('queued', 'processing', 'complete', 'failed', 'expired')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_jobs_status", "jobs")
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        "status IN ('queued', 'processing', 'complete', 'failed')",
    )

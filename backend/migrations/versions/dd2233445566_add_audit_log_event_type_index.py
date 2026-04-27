"""add event_type index to audit_logs

Revision ID: dd2233445566
Revises: cc1122334455
Create Date: 2026-04-27 00:00:00.000000

"""
from alembic import op

revision = "dd2233445566"
down_revision = "cc1122334455"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")

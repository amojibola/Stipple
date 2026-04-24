"""add unique index on email_tokens token_hash

Revision ID: bbcc2233ddee
Revises: aabb1122ccdd
Create Date: 2026-04-23 00:00:00.000000
"""
from alembic import op

revision = "bbcc2233ddee"
down_revision = "aabb1122ccdd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uix_email_tokens_token_hash",
        "email_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uix_email_tokens_token_hash", table_name="email_tokens")

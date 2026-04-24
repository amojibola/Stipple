"""add check constraints to uploaded_files

Revision ID: eeff4455aabb
Revises: ccdd3344eeff
Create Date: 2026-04-23 00:00:00.000000

"""
from alembic import op

revision = "eeff4455aabb"
down_revision = "ccdd3344eeff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_uploaded_files_file_size_bytes_positive",
        "uploaded_files",
        "file_size_bytes >= 1",
    )
    op.create_check_constraint(
        "ck_uploaded_files_width_px_positive",
        "uploaded_files",
        "width_px >= 1",
    )
    op.create_check_constraint(
        "ck_uploaded_files_height_px_positive",
        "uploaded_files",
        "height_px >= 1",
    )
    op.create_check_constraint(
        "ck_uploaded_files_megapixels_positive",
        "uploaded_files",
        "megapixels >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_uploaded_files_megapixels_positive", "uploaded_files", type_="check"
    )
    op.drop_constraint(
        "ck_uploaded_files_height_px_positive", "uploaded_files", type_="check"
    )
    op.drop_constraint(
        "ck_uploaded_files_width_px_positive", "uploaded_files", type_="check"
    )
    op.drop_constraint(
        "ck_uploaded_files_file_size_bytes_positive", "uploaded_files", type_="check"
    )

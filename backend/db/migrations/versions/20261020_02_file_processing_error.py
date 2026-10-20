"""Add retained file-processing error details.

Revision ID: 20261020_02
Revises: 20261019_01
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa

revision = "20261020_02"
down_revision = "20261019_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "uploaded_files",
        sa.Column("processing_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("uploaded_files", "processing_error")

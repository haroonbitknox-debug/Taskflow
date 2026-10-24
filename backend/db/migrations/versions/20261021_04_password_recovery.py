"""Add password recovery and database-backed rate limiting.

Revision ID: 20261021_04
Revises: 20261020_03
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021_04"
down_revision = "20261020_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_password_reset_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
        sa.UniqueConstraint("user_id", name="uq_password_reset_tokens_user_id"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index(
        "ix_password_reset_tokens_expires_at",
        "password_reset_tokens",
        ["expires_at"],
    )

    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key_hash", name="pk_rate_limit_buckets"),
    )
    op.create_index(
        "ix_rate_limit_buckets_window_started_at",
        "rate_limit_buckets",
        ["window_started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rate_limit_buckets_window_started_at",
        table_name="rate_limit_buckets",
    )
    op.drop_table("rate_limit_buckets")
    op.drop_index(
        "ix_password_reset_tokens_expires_at",
        table_name="password_reset_tokens",
    )
    op.drop_table("password_reset_tokens")

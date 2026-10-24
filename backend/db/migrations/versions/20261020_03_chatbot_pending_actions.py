"""Add server-side chatbot action confirmations.

Revision ID: 20261020_03
Revises: 20261020_02
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa

revision = "20261020_03"
down_revision = "20261020_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_chat_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("challenge_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("target_task_id", sa.Integer(), nullable=True),
        sa.Column("expected_updated_at", sa.DateTime(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_pending_chat_actions"),
        sa.UniqueConstraint("challenge_hash", name="uq_pending_chat_actions_challenge_hash"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_pending_chat_actions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["chat_conversations.id"],
            name="fk_pending_chat_actions_conversation_id_chat_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_task_id"], ["tasks.id"],
            name="fk_pending_chat_actions_target_task_id_tasks",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_pending_chat_actions_user_expiry",
        "pending_chat_actions",
        ["user_id", "expires_at"],
    )
    op.create_index(
        "ix_pending_chat_actions_task",
        "pending_chat_actions",
        ["target_task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pending_chat_actions_task", table_name="pending_chat_actions")
    op.drop_index("ix_pending_chat_actions_user_expiry", table_name="pending_chat_actions")
    op.drop_table("pending_chat_actions")

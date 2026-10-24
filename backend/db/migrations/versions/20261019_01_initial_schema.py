"""Create the initial TaskFlow schema.

Revision ID: 20261019_01
Revises:
Create Date: 2026-10-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20261019_01"
down_revision = None
branch_labels = None
depends_on = None


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", _enum("user_role", "user", "admin"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_role_active", "users", ["role", "is_active"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("target_entity", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("change_summary", sa.JSON(), nullable=True),
        sa.Column("outcome", _enum("audit_outcome", "success", "failure"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_audit_logs_actor_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_id", "created_at"])
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_entity", "target_id"])

    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_chat_conversations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chat_conversations"),
    )
    op.create_index(
        "ix_chat_conversations_user_updated",
        "chat_conversations",
        ["user_id", "updated_at"],
    )

    op.create_table(
        "task_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_task_tags_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_task_tags"),
        sa.UniqueConstraint("user_id", "name", name="uq_task_tags_user_name"),
        sa.UniqueConstraint("user_id", "slug", name="uq_task_tags_user_slug"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            _enum("task_status", "pending", "in_progress", "completed"),
            nullable=False,
        ),
        sa.Column("priority", _enum("task_priority", "low", "medium", "high"), nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_tasks_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
    )
    op.create_index("ix_tasks_user_category", "tasks", ["user_id", "category"])
    op.create_index("ix_tasks_user_priority", "tasks", ["user_id", "priority"])
    op.create_index(
        "ix_tasks_user_status_due", "tasks", ["user_id", "status", "due_date"]
    )

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("relative_path", sa.String(512), nullable=False),
        sa.Column("extension", sa.String(16), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "processing_status",
            _enum("file_processing_status", "pending", "processing", "ready", "failed"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_uploaded_files_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_uploaded_files"),
        sa.UniqueConstraint("stored_filename", name="uq_uploaded_files_stored_filename"),
    )
    op.create_index(
        "ix_uploaded_files_user_created", "uploaded_files", ["user_id", "created_at"]
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", _enum("message_role", "system", "user", "assistant"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["chat_conversations.id"],
            name="fk_chat_messages_conversation_id_chat_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chat_messages"),
    )
    op.create_index(
        "ix_chat_messages_conversation_created",
        "chat_messages",
        ["conversation_id", "created_at"],
    )

    op.create_table(
        "file_index_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uploaded_file_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("worksheet_name", sa.String(128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(64), nullable=False),
        sa.Column("searchable_content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["uploaded_file_id"], ["uploaded_files.id"],
            name="fk_file_index_entries_uploaded_file_id_uploaded_files",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_file_index_entries_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_file_index_entries"),
        sa.UniqueConstraint(
            "uploaded_file_id", "worksheet_name", "row_number", "column_name",
            name="uq_file_index_file_sheet_row_column",
        ),
    )
    op.create_index(
        "ix_file_index_user_file", "file_index_entries", ["user_id", "uploaded_file_id"]
    )
    op.create_index(
        "ix_file_index_user_normalized",
        "file_index_entries",
        ["user_id", "normalized_content"],
    )
    op.create_index(
        "ix_file_index_sheet_position",
        "file_index_entries",
        ["user_id", "worksheet_name", "row_number", "column_name"],
    )

    op.create_table(
        "task_tag_associations",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name="fk_task_tag_associations_task_id_tasks",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["task_tags.id"],
            name="fk_task_tag_associations_tag_id_task_tags",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("task_id", "tag_id", name="pk_task_tag_associations"),
    )


def downgrade() -> None:
    for table in (
        "task_tag_associations",
        "file_index_entries",
        "chat_messages",
        "uploaded_files",
        "tasks",
        "task_tags",
        "chat_conversations",
        "audit_logs",
        "users",
    ):
        op.drop_table(table)

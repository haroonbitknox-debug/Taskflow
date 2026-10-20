"""Create the initial TaskFlow database schema.

Revision ID: 20261019_01
Revises:
Create Date: 2026-10-19
"""

from alembic import op

revision = "20261019_01"
down_revision = None
branch_labels = None
depends_on = None

CREATE_STATEMENTS = (
    """
    CREATE TABLE users (
        id INTEGER NOT NULL AUTO_INCREMENT,
        full_name VARCHAR(120) NOT NULL,
        email VARCHAR(254) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        `role` ENUM('user', 'admin') NOT NULL,
        is_active BOOL NOT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        CONSTRAINT pk_users PRIMARY KEY (id),
        CONSTRAINT uq_users_email UNIQUE (email)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE audit_logs (
        id INTEGER NOT NULL AUTO_INCREMENT,
        actor_id INTEGER,
        action_type VARCHAR(64) NOT NULL,
        target_entity VARCHAR(64) NOT NULL,
        target_id VARCHAR(64),
        change_summary JSON,
        outcome ENUM('success', 'failure') NOT NULL,
        created_at DATETIME NOT NULL,
        CONSTRAINT pk_audit_logs PRIMARY KEY (id),
        CONSTRAINT fk_audit_logs_actor_id_users
            FOREIGN KEY (actor_id) REFERENCES users (id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE chat_conversations (
        id INTEGER NOT NULL AUTO_INCREMENT,
        user_id INTEGER NOT NULL,
        title VARCHAR(200),
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        CONSTRAINT pk_chat_conversations PRIMARY KEY (id),
        CONSTRAINT fk_chat_conversations_user_id_users
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE task_tags (
        id INTEGER NOT NULL AUTO_INCREMENT,
        user_id INTEGER NOT NULL,
        name VARCHAR(64) NOT NULL,
        slug VARCHAR(80) NOT NULL,
        created_at DATETIME NOT NULL,
        CONSTRAINT pk_task_tags PRIMARY KEY (id),
        CONSTRAINT uq_task_tags_user_name UNIQUE (user_id, name),
        CONSTRAINT uq_task_tags_user_slug UNIQUE (user_id, slug),
        CONSTRAINT fk_task_tags_user_id_users
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE tasks (
        id INTEGER NOT NULL AUTO_INCREMENT,
        user_id INTEGER NOT NULL,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        status ENUM('pending', 'in_progress', 'completed') NOT NULL,
        priority ENUM('low', 'medium', 'high') NOT NULL,
        category VARCHAR(80),
        due_date DATETIME,
        completed_at DATETIME,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        CONSTRAINT pk_tasks PRIMARY KEY (id),
        CONSTRAINT fk_tasks_user_id_users
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE uploaded_files (
        id INTEGER NOT NULL AUTO_INCREMENT,
        user_id INTEGER NOT NULL,
        original_filename VARCHAR(255) NOT NULL,
        stored_filename VARCHAR(255) NOT NULL,
        relative_path VARCHAR(512) NOT NULL,
        extension VARCHAR(16) NOT NULL,
        mime_type VARCHAR(127) NOT NULL,
        file_size BIGINT NOT NULL,
        processing_status ENUM('pending', 'processing', 'ready', 'failed') NOT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        CONSTRAINT pk_uploaded_files PRIMARY KEY (id),
        CONSTRAINT uq_uploaded_files_stored_filename UNIQUE (stored_filename),
        CONSTRAINT fk_uploaded_files_user_id_users
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE chat_messages (
        id INTEGER NOT NULL AUTO_INCREMENT,
        conversation_id INTEGER NOT NULL,
        `role` ENUM('system', 'user', 'assistant') NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        CONSTRAINT pk_chat_messages PRIMARY KEY (id),
        CONSTRAINT fk_chat_messages_conversation_id_chat_conversations
            FOREIGN KEY (conversation_id)
            REFERENCES chat_conversations (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE file_index_entries (
        id INTEGER NOT NULL AUTO_INCREMENT,
        uploaded_file_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        worksheet_name VARCHAR(128) NOT NULL,
        `row_number` INTEGER NOT NULL,
        column_name VARCHAR(64) NOT NULL,
        searchable_content TEXT NOT NULL,
        normalized_content VARCHAR(512) NOT NULL,
        created_at DATETIME NOT NULL,
        CONSTRAINT pk_file_index_entries PRIMARY KEY (id),
        CONSTRAINT uq_file_index_file_sheet_row_column
            UNIQUE (
                uploaded_file_id, worksheet_name, `row_number`, column_name
            ),
        CONSTRAINT fk_file_index_entries_uploaded_file_id_uploaded_files
            FOREIGN KEY (uploaded_file_id)
            REFERENCES uploaded_files (id) ON DELETE CASCADE,
        CONSTRAINT fk_file_index_entries_user_id_users
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE task_tag_associations (
        task_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        CONSTRAINT pk_task_tag_associations PRIMARY KEY (task_id, tag_id),
        CONSTRAINT fk_task_tag_associations_task_id_tasks
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
        CONSTRAINT fk_task_tag_associations_tag_id_task_tags
            FOREIGN KEY (tag_id) REFERENCES task_tags (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "CREATE INDEX ix_users_role_active ON users (`role`, is_active)",
    "CREATE INDEX ix_audit_logs_actor_created ON audit_logs (actor_id, created_at)",
    "CREATE INDEX ix_audit_logs_target ON audit_logs (target_entity, target_id)",
    "CREATE INDEX ix_chat_conversations_user_updated ON chat_conversations (user_id, updated_at)",
    "CREATE INDEX ix_tasks_user_category ON tasks (user_id, category)",
    "CREATE INDEX ix_tasks_user_priority ON tasks (user_id, priority)",
    "CREATE INDEX ix_tasks_user_status_due ON tasks (user_id, status, due_date)",
    "CREATE INDEX ix_uploaded_files_user_created ON uploaded_files (user_id, created_at)",
    "CREATE INDEX ix_chat_messages_conversation_created ON chat_messages (conversation_id, created_at)",
    "CREATE FULLTEXT INDEX ix_file_index_searchable_content ON file_index_entries (searchable_content, normalized_content)",
    "CREATE INDEX ix_file_index_sheet_position ON file_index_entries (user_id, worksheet_name, `row_number`, column_name)",
    "CREATE INDEX ix_file_index_user_file ON file_index_entries (user_id, uploaded_file_id)",
    "CREATE INDEX ix_file_index_user_normalized ON file_index_entries (user_id, normalized_content(191))",
)


def upgrade() -> None:
    for statement in CREATE_STATEMENTS:
        op.execute(statement)


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
        op.execute(f"DROP TABLE {table}")

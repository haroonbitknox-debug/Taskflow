from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime


class PendingChatAction(Base):
    __tablename__ = "pending_chat_actions"
    __table_args__ = (
        Index("ix_pending_chat_actions_user_expiry", "user_id", "expires_at"),
        Index("ix_pending_chat_actions_task", "target_task_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False
    )
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    target_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE")
    )
    expected_updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), nullable=False
    )

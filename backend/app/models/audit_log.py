from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime


class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        Index("ix_audit_logs_target", "target_entity", "target_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64))
    change_summary: Mapped[dict[str, object] | None] = mapped_column(JSON)
    outcome: Mapped[AuditOutcome] = mapped_column(
        SQLAlchemyEnum(
            AuditOutcome,
            name="audit_outcome",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=AuditOutcome.SUCCESS,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), nullable=False
    )

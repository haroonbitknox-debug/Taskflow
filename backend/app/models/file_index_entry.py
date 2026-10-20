from datetime import UTC, datetime

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime


class FileIndexEntry(Base):
    __tablename__ = "file_index_entries"
    __table_args__ = (
        UniqueConstraint(
            "uploaded_file_id",
            "worksheet_name",
            "row_number",
            "column_name",
            name="uq_file_index_file_sheet_row_column",
        ),
        Index("ix_file_index_user_file", "user_id", "uploaded_file_id"),
        Index(
            "ix_file_index_user_normalized",
            "user_id",
            "normalized_content",
            mysql_length={"normalized_content": 191},
        ),
        Index(
            "ix_file_index_sheet_position",
            "user_id",
            "worksheet_name",
            "row_number",
            "column_name",
        ),
        Index(
            "ix_file_index_searchable_content",
            "searchable_content",
            "normalized_content",
            mysql_prefix="FULLTEXT",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_file_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    worksheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    column_name: Mapped[str] = mapped_column(String(64), nullable=False)
    searchable_content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), nullable=False
    )

    uploaded_file: Mapped["UploadedFile"] = relationship(
        back_populates="index_entries"
    )
    user: Mapped["User"] = relationship()

from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base import Base

task_tag_associations = Table(
    "task_tag_associations",
    Base.metadata,
    Column(
        "task_id",
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("task_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

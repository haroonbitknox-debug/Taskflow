from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, Enum as SQLAlchemyEnum, Index, String, event, select
from sqlalchemy.orm import Mapped, Session as SQLAlchemySession, mapped_column, relationship

from app.db.base import Base, UTCDateTime


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list["Tag"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    conversations: Mapped[list["ChatConversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


@event.listens_for(SQLAlchemySession, "before_flush")
def prevent_removing_last_active_admin(
    session: SQLAlchemySession, flush_context: object, instances: object
) -> None:
    from sqlalchemy import inspect

    removals: dict[int, User] = {}
    for user in session.deleted:
        if isinstance(user, User) and user.role == UserRole.ADMIN and user.is_active:
            removals[user.id] = user

    for user in session.dirty:
        if not isinstance(user, User) or user in session.deleted:
            continue
        state = inspect(user)
        previous_role = (
            state.attrs.role.history.deleted[0]
            if state.attrs.role.history.deleted
            else user.role
        )
        previous_active = (
            state.attrs.is_active.history.deleted[0]
            if state.attrs.is_active.history.deleted
            else user.is_active
        )
        loses_access = (
            previous_role == UserRole.ADMIN
            and previous_active
            and (user.role != UserRole.ADMIN or not user.is_active)
        )
        if loses_access:
            removals[user.id] = user

    if not removals:
        return

    active_admin_ids = session.scalars(
        select(User.id)
        .where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
        .with_for_update()
    ).all()
    active_admin_count = len(active_admin_ids)
    new_active_admin_count = sum(
        1
        for user in session.new
        if isinstance(user, User)
        and user.role == UserRole.ADMIN
        and user.is_active
    )
    if active_admin_count - len(removals) + new_active_admin_count < 1:
        raise ValueError("Cannot remove the last active administrator.")

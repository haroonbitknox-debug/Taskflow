from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuditLog, AuditOutcome, UploadedFile, User, UserRole
from app.schemas.admin import AdminUserCreate, AdminUserQuery, AdminUserUpdate
from app.utils.passwords import hash_password


class AdminUserNotFoundError(Exception):
    pass


class DuplicateAdminEmailError(Exception):
    pass


class LastAdminError(Exception):
    pass


class UnsafeUploadPathError(Exception):
    pass


UPLOADS_ROOT = Path(__file__).resolve().parents[2] / "uploads"


def list_admin_users(db: Session, query: AdminUserQuery) -> tuple[list[User], int]:
    statement = select(User)
    if query.search:
        search = f"%{query.search.strip()}%"
        statement = statement.where(
            or_(User.full_name.ilike(search), User.email.ilike(search))
        )
    if query.role is not None:
        statement = statement.where(User.role == query.role)
    if query.is_active is not None:
        statement = statement.where(User.is_active.is_(query.is_active))
    total = db.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    items = db.scalars(
        statement.order_by(User.created_at.desc(), User.id.asc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return items, total


def create_admin_user(
    db: Session,
    actor_id: int,
    request: AdminUserCreate,
) -> User:
    if db.scalar(select(User.id).where(User.email == request.email)):
        raise DuplicateAdminEmailError
    user = User(
        full_name=request.full_name,
        email=request.email,
        password_hash=hash_password(request.password),
        role=request.role,
        is_active=request.is_active,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditLog(
            actor_id=actor_id,
            action_type="create",
            target_entity="user",
            target_id=str(user.id),
            change_summary={"role": user.role.value, "is_active": user.is_active},
            outcome=AuditOutcome.SUCCESS,
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAdminEmailError from exc
    db.refresh(user)
    return user


def get_admin_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AdminUserNotFoundError
    return user


def update_admin_user(
    db: Session,
    actor_id: int,
    user_id: int,
    request: AdminUserUpdate,
) -> User:
    user = get_admin_user(db, user_id)
    changes = request.model_dump(exclude_unset=True)
    if not changes:
        raise ValueError("Provide at least one user field to update.")
    removes_active_admin = (
        user.role == UserRole.ADMIN
        and user.is_active
        and (
            changes.get("role", user.role) != UserRole.ADMIN
            or changes.get("is_active", user.is_active) is False
        )
    )
    if removes_active_admin and db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
    ) <= 1:
        raise LastAdminError
    if user_id == actor_id and (
        changes.get("role", user.role) != UserRole.ADMIN
        or changes.get("is_active", user.is_active) is False
    ):
        raise ValueError("Administrators cannot demote or deactivate their own account.")
    if "email" in changes and db.scalar(
        select(User.id).where(User.email == changes["email"], User.id != user_id)
    ):
        raise DuplicateAdminEmailError
    old_values = {
        field: user.role.value if field == "role" else getattr(user, field)
        for field in changes
    }
    for field, value in changes.items():
        setattr(user, field, value)
    summary = {
        field: {
            "from": old_values[field],
            "to": value.value if field == "role" else value,
        }
        for field, value in changes.items()
    }
    db.add(
        AuditLog(
            actor_id=actor_id,
            action_type="update",
            target_entity="user",
            target_id=str(user_id),
            change_summary=summary,
            outcome=AuditOutcome.SUCCESS,
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAdminEmailError from exc
    except ValueError as exc:
        db.rollback()
        if "last active administrator" in str(exc):
            raise LastAdminError from exc
        raise
    db.refresh(user)
    return user


def _user_upload_paths(user: User) -> list[Path]:
    upload_root = UPLOADS_ROOT.resolve()
    shared_fixture = (upload_root / "demo-fixtures").resolve()
    paths: list[Path] = []
    for uploaded_file in user.uploaded_files:
        relative_path = Path(uploaded_file.relative_path)
        candidate = (upload_root / relative_path).resolve()
        if candidate == shared_fixture or shared_fixture in candidate.parents:
            continue
        if upload_root not in candidate.parents:
            raise UnsafeUploadPathError(
                f"Refusing to delete an upload outside the upload directory: {relative_path}"
            )
        paths.append(candidate)
    return paths


def delete_admin_user(db: Session, actor_id: int, user_id: int) -> None:
    if actor_id == user_id:
        raise ValueError("Administrators cannot delete their own account.")
    user = get_admin_user(db, user_id)
    files_to_remove = _user_upload_paths(user)
    db.add(
        AuditLog(
            actor_id=actor_id,
            action_type="delete",
            target_entity="user",
            target_id=str(user_id),
            change_summary={"files_scheduled_for_deletion": len(files_to_remove)},
            outcome=AuditOutcome.SUCCESS,
        )
    )
    db.delete(user)
    try:
        db.flush()
        remove_user_files(files_to_remove)
        db.commit()
    except OSError:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        if "last active administrator" in str(exc):
            raise LastAdminError from exc
        raise
def remove_user_files(paths: list[Path]) -> None:
    for path in paths:
        if path.is_file():
            path.unlink()
        parent = path.parent
        while parent.name != "uploads" and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

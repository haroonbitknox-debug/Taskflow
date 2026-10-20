from datetime import UTC, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_active_user, require_admin
from app.db.session import get_db
from app.models import Task, TaskStatus, User
from app.schemas.dashboard import (
    AdminDashboardSummary,
    TaskStatusCounts,
    UserDashboardSummary,
)
from app.schemas.tasks import TaskResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
admin_router = APIRouter(prefix="/admin/dashboard", tags=["administrator dashboard"])


def _status_counts(db: Session, owner_id: int | None = None) -> TaskStatusCounts:
    counts = {status.value: 0 for status in TaskStatus}
    statement = select(Task.status, func.count(Task.id)).group_by(Task.status)
    if owner_id is not None:
        statement = statement.where(Task.user_id == owner_id)
    for task_status, count in db.execute(statement):
        counts[task_status.value] = count
    return TaskStatusCounts(**counts)


def _recent_tasks(
    db: Session,
    owner_id: int | None = None,
    limit: int = 5,
) -> list[TaskResponse]:
    statement = select(Task).options(joinedload(Task.tags))
    if owner_id is not None:
        statement = statement.where(Task.user_id == owner_id)
    tasks = (
        db.execute(statement.order_by(Task.updated_at.desc(), Task.id.asc()).limit(limit))
        .unique()
        .scalars()
        .all()
    )
    return [TaskResponse.from_task(task) for task in tasks]


def _overdue_count(db: Session, owner_id: int | None = None) -> int:
    now = datetime.now(UTC)
    statement = select(func.count(Task.id)).where(
        Task.due_date < now,
        Task.status != TaskStatus.COMPLETED,
    )
    if owner_id is not None:
        statement = statement.where(Task.user_id == owner_id)
    return db.scalar(statement) or 0


@router.get("/summary", response_model=UserDashboardSummary)
def user_summary(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserDashboardSummary:
    now = datetime.now(UTC)
    today_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
    tomorrow_start = today_start + timedelta(days=1)
    owner_filter = Task.user_id == user.id

    task_total = db.scalar(
        select(func.count(Task.id)).where(owner_filter)
    ) or 0
    due_today = db.scalar(
        select(func.count(Task.id)).where(
            owner_filter,
            Task.due_date >= today_start,
            Task.due_date < tomorrow_start,
            Task.status != TaskStatus.COMPLETED,
        )
    ) or 0
    upcoming = db.scalar(
        select(func.count(Task.id)).where(
            owner_filter,
            Task.due_date >= tomorrow_start,
            Task.status != TaskStatus.COMPLETED,
        )
    ) or 0
    counts = _status_counts(db, user.id)
    completion = (counts.completed / task_total * 100) if task_total else 0.0
    return UserDashboardSummary(
        task_total=task_total,
        status_counts=counts,
        overdue_tasks=_overdue_count(db, user.id),
        due_today=due_today,
        upcoming_tasks=upcoming,
        completion_percentage=round(completion, 2),
        recent_tasks=_recent_tasks(db, user.id),
    )


@admin_router.get("/summary", response_model=AdminDashboardSummary)
def administrator_summary(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminDashboardSummary:
    user_counts = dict(
        db.execute(
            select(User.is_active, func.count(User.id)).group_by(User.is_active)
        ).all()
    )
    user_total = sum(user_counts.values())
    task_total = db.scalar(select(func.count(Task.id))) or 0
    registrations = db.scalars(
        select(User).order_by(User.created_at.desc(), User.id.asc()).limit(5)
    ).all()
    return AdminDashboardSummary(
        user_total=user_total,
        active_users=user_counts.get(True, 0),
        inactive_users=user_counts.get(False, 0),
        task_total=task_total,
        task_status_counts=_status_counts(db),
        overdue_tasks=_overdue_count(db),
        recent_registrations=[
            {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at,
            }
            for user in registrations
        ],
        recent_tasks=_recent_tasks(db),
    )

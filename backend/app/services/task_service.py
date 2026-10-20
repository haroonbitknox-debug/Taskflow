import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload, lazyload

from app.models import Priority, Tag, Task, TaskStatus, User
from app.schemas.tasks import (
    SortDirection,
    TaskCreate,
    TaskListQuery,
    TaskSort,
    TaskUpdate,
)

PRIORITY_ORDER = case(
    (Task.priority == Priority.HIGH, 3),
    (Task.priority == Priority.MEDIUM, 2),
    else_=1,
)


class TaskNotFoundError(Exception):
    pass


class TaskOwnerError(Exception):
    pass


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug[:80] or "tag"


def _apply_tags(db: Session, task: Task, owner_id: int, names: list[str]) -> None:
    tags: list[Tag] = []
    for name in names:
        tag = db.scalar(
            select(Tag).where(
                Tag.user_id == owner_id,
                func.lower(Tag.name) == name.casefold(),
            )
        )
        if tag is None:
            base_slug = _slugify(name)
            slug = base_slug
            suffix = 2
            while db.scalar(
                select(Tag.id).where(Tag.user_id == owner_id, Tag.slug == slug)
            ):
                slug = f"{base_slug[:75]}-{suffix}"
                suffix += 1
            tag = Tag(user_id=owner_id, name=name, slug=slug)
            db.add(tag)
            db.flush()
        tags.append(tag)
    task.tags = tags


def create_task(
    db: Session,
    data: TaskCreate,
    owner_id: int,
    commit: bool = True,
) -> Task:
    owner = db.get(User, owner_id)
    if owner is None or not owner.is_active:
        raise TaskOwnerError("The task owner does not exist or is inactive.")
    now = datetime.now(UTC)
    task = Task(
        user_id=owner_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        category=data.category,
        due_date=data.due_date,
        completed_at=now if data.status == TaskStatus.COMPLETED else None,
    )
    db.add(task)
    _apply_tags(db, task, owner_id, data.tags)
    db.flush()
    if commit:
        db.commit()
        return get_task(db, task.id)
    return task


def get_task(
    db: Session,
    task_id: int,
    owner_id: int | None = None,
) -> Task:
    query = select(Task).options(joinedload(Task.tags)).where(Task.id == task_id)
    if owner_id is not None:
        query = query.where(Task.user_id == owner_id)
    task = db.execute(query).unique().scalar_one_or_none()
    if task is None:
        raise TaskNotFoundError
    return task


def update_task(
    db: Session,
    task_id: int,
    data: TaskUpdate,
    owner_id: int | None = None,
    commit: bool = True,
) -> Task:
    task = get_task(db, task_id, owner_id)
    changes = data.model_dump(exclude_unset=True)
    if "title" in changes and changes["title"] is None:
        raise ValueError("Task title cannot be null.")
    if "status" in changes:
        next_status = changes["status"]
        if next_status == TaskStatus.COMPLETED:
            if task.status != TaskStatus.COMPLETED:
                task.completed_at = datetime.now(UTC)
        else:
            task.completed_at = None
    if "tags" in changes:
        names = changes.pop("tags")
        if names is not None:
            _apply_tags(db, task, task.user_id, names)
    for field, value in changes.items():
        setattr(task, field, value)
    task.updated_at = datetime.now(UTC)
    db.flush()
    if commit:
        db.commit()
        return get_task(db, task.id, owner_id)
    return task


def update_admin_task(
    db: Session,
    task_id: int,
    data: TaskUpdate,
    target_owner_id: int | None = None,
    commit: bool = True,
) -> Task:
    task = get_task(db, task_id)
    changes = data.model_dump(exclude_unset=True)
    if "title" in changes and changes["title"] is None:
        raise ValueError("Task title cannot be null.")

    if target_owner_id is not None and target_owner_id != task.user_id:
        owner = db.get(User, target_owner_id)
        if owner is None or not owner.is_active:
            raise TaskOwnerError("The task owner does not exist or is inactive.")
        existing_tag_names = [tag.name for tag in task.tags]
        task.user_id = target_owner_id
        if "tags" not in changes:
            _apply_tags(db, task, target_owner_id, existing_tag_names)

    if "status" in changes:
        next_status = changes["status"]
        if next_status == TaskStatus.COMPLETED:
            if task.status != TaskStatus.COMPLETED:
                task.completed_at = datetime.now(UTC)
        else:
            task.completed_at = None
    if "tags" in changes:
        names = changes.pop("tags")
        if names is not None:
            _apply_tags(db, task, task.user_id, names)
    for field, value in changes.items():
        setattr(task, field, value)
    task.updated_at = datetime.now(UTC)
    db.flush()
    if commit:
        db.commit()
        return get_task(db, task.id)
    return task


def delete_task(
    db: Session,
    task_id: int,
    owner_id: int | None = None,
    commit: bool = True,
) -> int:
    task = get_task(db, task_id, owner_id)
    deleted_id = task.id
    db.delete(task)
    if commit:
        db.commit()
    else:
        db.flush()
    return deleted_id


def build_task_query(
    db: Session,
    query: TaskListQuery,
    owner_id: int | None = None,
    owner_filter: int | None = None,
):
    statement = select(Task).options(joinedload(Task.tags))
    if owner_id is not None:
        statement = statement.where(Task.user_id == owner_id)
    if owner_filter is not None:
        statement = statement.where(Task.user_id == owner_filter)
    if query.status is not None:
        statement = statement.where(Task.status == query.status)
    if query.priority is not None:
        statement = statement.where(Task.priority == query.priority)
    if query.due_from is not None:
        statement = statement.where(Task.due_date >= query.due_from)
    if query.due_to is not None:
        statement = statement.where(Task.due_date <= query.due_to)
    if query.overdue:
        statement = statement.where(
            Task.due_date < datetime.now(UTC),
            Task.status != TaskStatus.COMPLETED,
        )
    if query.search:
        search = f"%{query.search.strip()}%"
        conditions: list[Any] = [
            Task.title.ilike(search),
            Task.description.ilike(search),
            Task.category.ilike(search),
            Task.tags.any(Tag.name.ilike(search)),
        ]
        if query.search.strip().isdecimal():
            conditions.append(Task.id == int(query.search.strip()))
        statement = statement.where(or_(*conditions))

    if query.sort_by == TaskSort.PRIORITY:
        sort_column = PRIORITY_ORDER
    else:
        sort_column = {
            TaskSort.DUE_DATE: Task.due_date,
            TaskSort.TITLE: Task.title,
            TaskSort.CREATED_AT: Task.created_at,
        }[query.sort_by]
    sort_expression = (
        sort_column.asc()
        if query.sort_direction == SortDirection.ASC
        else sort_column.desc()
    )
    statement = statement.order_by(sort_expression, Task.id.asc())
    return statement


def list_tasks(
    db: Session,
    query: TaskListQuery,
    owner_id: int | None = None,
    owner_filter: int | None = None,
) -> tuple[list[Task], int]:
    statement = build_task_query(db, query, owner_id, owner_filter)
    count_statement = select(func.count()).select_from(
        statement.order_by(None).options(lazyload("*")).subquery()
    )
    total = db.scalar(count_statement) or 0
    items = (
        db.execute(
            statement.offset((query.page - 1) * query.page_size).limit(query.page_size)
        )
        .unique()
        .scalars()
        .all()
    )
    return items, total

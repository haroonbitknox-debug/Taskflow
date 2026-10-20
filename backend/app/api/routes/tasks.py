from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_active_user, require_admin, require_csrf
from app.db.session import get_db
from app.models import Task, User
from app.schemas.tasks import (
    AdminTaskCreate,
    AdminTaskUpdate,
    SortDirection,
    TaskCreate,
    TaskListQuery,
    TaskPage,
    TaskResponse,
    TaskSort,
    TaskUpdate,
)
from app.models import AuditLog, AuditOutcome
from app.services.audit_service import record_admin_mutation
from app.services.task_service import (
    TaskNotFoundError,
    TaskOwnerError,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_admin_task,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])
admin_router = APIRouter(prefix="/admin/tasks", tags=["administrator tasks"])


def _query(
    page: int,
    page_size: int,
    search: str | None,
    task_status: str | None,
    priority: str | None,
    due_from: datetime | None,
    due_to: datetime | None,
    overdue: bool,
    sort_by: TaskSort,
    sort_direction: SortDirection,
) -> TaskListQuery:
    if due_from is not None and due_from.tzinfo is None:
        raise HTTPException(status_code=422, detail="due_from must include a timezone.")
    if due_to is not None and due_to.tzinfo is None:
        raise HTTPException(status_code=422, detail="due_to must include a timezone.")
    if due_from is not None and due_to is not None and due_from > due_to:
        raise HTTPException(
            status_code=422, detail="due_from must be earlier than or equal to due_to."
        )
    try:
        return TaskListQuery(
            page=page,
            page_size=page_size,
            search=search,
            status=task_status,
            priority=priority,
            due_from=due_from,
            due_to=due_to,
            overdue=overdue,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _list_query(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    task_status: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    due_from: datetime | None = Query(default=None),
    due_to: datetime | None = Query(default=None),
    overdue: bool = False,
    sort_by: TaskSort = TaskSort.CREATED_AT,
    sort_direction: SortDirection = SortDirection.DESC,
) -> TaskListQuery:
    return _query(
        page, page_size, search, task_status, priority,
        due_from, due_to, overdue, sort_by, sort_direction,
    )


def _page(items: list[Task], total: int, query: TaskListQuery) -> TaskPage:
    return TaskPage(
        items=[TaskResponse.from_task(task) for task in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Task not found.",
    )


@router.get("", response_model=TaskPage)
def list_my_tasks(
    filters: TaskListQuery = Depends(_list_query),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> TaskPage:
    items, total = list_tasks(db, filters, owner_id=user.id)
    return _page(items, total, filters)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_my_task(
    request: TaskCreate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        return TaskResponse.from_task(create_task(db, request, user.id))
    except TaskOwnerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{task_id}", response_model=TaskResponse)
def get_my_task(
    task_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        return TaskResponse.from_task(get_task(db, task_id, owner_id=user.id))
    except TaskNotFoundError as exc:
        raise _not_found() from exc


@router.patch("/{task_id}", response_model=TaskResponse, dependencies=[Depends(require_csrf)])
def patch_my_task(
    task_id: int,
    request: TaskUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        return TaskResponse.from_task(update_task(db, task_id, request, user.id))
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def remove_my_task(
    task_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_task(db, task_id, owner_id=user.id)
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("", response_model=TaskPage)
def list_all_tasks(
    filters: TaskListQuery = Depends(_list_query),
    owner_id: int | None = Query(default=None, gt=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TaskPage:
    items, total = list_tasks(db, filters, owner_filter=owner_id)
    return _page(items, total, filters)


@admin_router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_task_for_user(
    request: AdminTaskCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TaskResponse:
    data = TaskCreate.model_validate(request.model_dump(exclude={"user_id"}))
    try:
        task = create_task(db, data, request.user_id, commit=False)
    except TaskOwnerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_admin_mutation(db, admin.id, "create", "task", task.id, {"user_id": task.user_id})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    return TaskResponse.from_task(get_task(db, task.id))


@admin_router.get("/{task_id}", response_model=TaskResponse)
def get_any_task(
    task_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        return TaskResponse.from_task(get_task(db, task_id))
    except TaskNotFoundError as exc:
        raise _not_found() from exc


@admin_router.patch("/{task_id}", response_model=TaskResponse, dependencies=[Depends(require_csrf)])
def patch_any_task(
    task_id: int,
    request: AdminTaskUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TaskResponse:
    target_owner_id = request.user_id
    task_data = TaskUpdate.model_validate(
        request.model_dump(exclude={"user_id"}, exclude_unset=True)
    )
    try:
        task = update_admin_task(db, task_id, task_data, target_owner_id, commit=False)
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_admin_mutation(
        db, admin.id, "update", "task", task.id,
        {"fields": sorted(request.model_dump(exclude_unset=True).keys())},
    )
    db.commit()
    return TaskResponse.from_task(get_task(db, task.id))


@admin_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def remove_any_task(
    task_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_task(db, task_id, commit=False)
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    db.add(
        AuditLog(
            actor_id=admin.id,
            action_type="delete",
            target_entity="task",
            target_id=str(task_id),
            change_summary={},
            outcome=AuditOutcome.SUCCESS,
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

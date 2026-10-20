from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models import Priority, TaskStatus

TaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
TaskCategory = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class TaskSort(str, Enum):
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    TITLE = "title"
    CREATED_AT = "created_at"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle
    description: Annotated[str, StringConstraints(max_length=10000)] | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    category: TaskCategory | None = None
    tags: list[TagName] = Field(default_factory=list, max_length=20)
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Due date must include a timezone.")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        unique: dict[str, str] = {}
        for value in values:
            normalized = value.casefold()
            unique.setdefault(normalized, value)
        return list(unique.values())


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle | None = None
    description: Annotated[str, StringConstraints(max_length=10000)] | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    category: TaskCategory | None = None
    tags: list[TagName] | None = Field(default=None, max_length=20)
    due_date: datetime | None = None

    @field_validator("title", "status", "priority", "tags")
    @classmethod
    def reject_null_updates(cls, value):
        if value is None:
            raise ValueError("Task title, status, priority, and tags cannot be null.")
        return value

    @field_validator("due_date")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Due date must include a timezone.")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return values
        unique: dict[str, str] = {}
        for value in values:
            unique.setdefault(value.casefold(), value)
        return list(unique.values())


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    category: str | None
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tags: list[str]

    @classmethod
    def from_task(cls, task) -> "TaskResponse":
        return cls(
            id=task.id,
            user_id=task.user_id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            category=task.category,
            due_date=task.due_date,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            tags=[tag.name for tag in task.tags],
        )


class TaskPage(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Annotated[str | None, StringConstraints(max_length=200)] = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    due_from: datetime | None = None
    due_to: datetime | None = None
    overdue: bool = False
    sort_by: TaskSort = TaskSort.CREATED_AT
    sort_direction: SortDirection = SortDirection.DESC

    @field_validator("due_from", "due_to")
    @classmethod
    def require_range_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Due-date filters must include a timezone.")
        return value


class AdminTaskCreate(TaskCreate):
    user_id: int = Field(gt=0)


class AdminTaskUpdate(TaskUpdate):
    user_id: int | None = Field(default=None, gt=0)

    @field_validator("user_id")
    @classmethod
    def reject_null_owner(cls, value: int | None) -> int | None:
        if value is None:
            raise ValueError("Task owner cannot be null.")
        return value

from datetime import datetime

from pydantic import BaseModel

from app.schemas.tasks import TaskResponse


class TaskStatusCounts(BaseModel):
    pending: int
    in_progress: int
    completed: int


class UserDashboardSummary(BaseModel):
    task_total: int
    status_counts: TaskStatusCounts
    overdue_tasks: int
    due_today: int
    upcoming_tasks: int
    completion_percentage: float
    recent_tasks: list[TaskResponse]


class AdminDashboardSummary(BaseModel):
    user_total: int
    active_users: int
    inactive_users: int
    task_total: int
    task_status_counts: TaskStatusCounts
    overdue_tasks: int
    recent_registrations: list[dict[str, object]]
    recent_tasks: list[TaskResponse]

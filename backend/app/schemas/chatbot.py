from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing import Annotated

from app.schemas.files import FileSearchHit
from app.schemas.tasks import TaskResponse

ChatIntent = Literal[
    "search_tasks",
    "get_task",
    "create_task",
    "update_task",
    "delete_task",
    "search_files",
    "search_spreadsheet_content",
    "clarify_request",
    "unsupported_request",
]


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: int | None = Field(default=None, gt=0)
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ChatTaskResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    status: str
    priority: str
    due_date: datetime | None
    owner_name: str | None = None


class PendingActionInfo(BaseModel):
    challenge: str
    operation: Literal["create", "update", "delete"]
    expires_at: datetime
    preview: str
    task: TaskResponse | None = None
    changes: dict[str, object] = Field(default_factory=dict)
    owner_name: str | None = None


class ChatMessageResponse(BaseModel):
    conversation_id: int
    intent: ChatIntent
    assistant_message: str
    tasks: list[ChatTaskResult] = Field(default_factory=list)
    files: list[FileSearchHit] = Field(default_factory=list)
    search_query: str | None = None
    pending_action: PendingActionInfo | None = None


class ChatHistoryMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    conversation_id: int
    messages: list[ChatHistoryMessage]

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    AuditOutcome,
    ChatConversation,
    ChatMessage,
    ChatMessage,
    MessageRole,
    PendingChatAction,
    Priority,
    Task,
    TaskStatus,
    User,
    UserRole,
)
from app.schemas.chatbot import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatTaskResult,
    PendingActionInfo,
)
from app.schemas.files import FileSearchHit
from app.schemas.tasks import TaskCreate, TaskListQuery, TaskResponse, TaskUpdate
from app.services.file_service import search_files
from app.services.spreadsheet_chat_service import answer_spreadsheet_question
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
from app.utils.chatbot_intents import ParsedIntent, parse_intent

MAX_CHAT_RESULTS = 10
ACTION_LIFETIME = timedelta(minutes=5)


class ChatAccessError(Exception):
    pass


class ChatActionError(Exception):
    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


def _task_result(task: Task, user: User) -> ChatTaskResult:
    return ChatTaskResult(
        id=task.id,
        user_id=task.user_id,
        title=task.title,
        status=task.status.value,
        priority=task.priority.value,
        due_date=task.due_date,
        owner_name=task.user.full_name if user.role == UserRole.ADMIN else None,
    )


def _conversation(
    db: Session,
    user: User,
    conversation_id: int | None,
    first_message: str,
) -> ChatConversation:
    if conversation_id is not None:
        conversation = db.scalar(
            select(ChatConversation).where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user.id,
            )
        )
        if conversation is None:
            raise ChatAccessError("Conversation not found.")
        return conversation
    conversation = ChatConversation(
        user_id=user.id,
        title=first_message[:200],
    )
    db.add(conversation)
    db.flush()
    return conversation


def _save_message(
    db: Session,
    conversation: ChatConversation,
    role: MessageRole,
    content: str,
) -> None:
    conversation.updated_at = datetime.now(UTC)
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            role=role,
            content=content[:4000],
        )
    )


def _redact_sensitive_text(value: str) -> str:
    value = re.sub(
        r"(?i)\b(password|passphrase|secret|api[_ -]?key|access[_ -]?token|refresh[_ -]?token)\b(?:\s+is)?(?:\s*[:=]\s*|\s+)\S+",
        r"\1=[redacted]",
        value,
    )
    return re.sub(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)


def _save_audit(
    db: Session,
    user: User,
    operation: str,
    task_id: int | None,
    outcome: AuditOutcome,
    fields: list[str],
) -> None:
    db.add(
        AuditLog(
            actor_id=user.id,
            action_type=f"chatbot.task.{operation}",
            target_entity="task",
            target_id=str(task_id) if task_id is not None else None,
            change_summary={
                "actor_role": user.role.value,
                "changed_fields": fields,
            },
            outcome=outcome,
        )
    )


def _create_pending_action(
    db: Session,
    user: User,
    conversation: ChatConversation,
    operation: str,
    payload: dict[str, object],
    task: Task | None = None,
    owner_name: str | None = None,
) -> PendingActionInfo:
    challenge = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + ACTION_LIFETIME
    db.add(
        PendingChatAction(
            challenge_hash=hashlib.sha256(challenge.encode("utf-8")).hexdigest(),
            user_id=user.id,
            conversation_id=conversation.id,
            operation=operation,
            target_task_id=task.id if task else None,
            expected_updated_at=task.updated_at if task else None,
            payload=payload,
            expires_at=expires_at,
        )
    )
    changes = payload.get("changes", payload)
    if not isinstance(changes, dict):
        changes = {}
    if operation == "create":
        changes = {
            key: payload[key]
            for key in ("title", "priority", "due_date")
            if key in payload
        }
    elif operation == "delete":
        changes = {}
    if operation == "delete" and task:
        preview = f"Delete task {task.id}: {task.title} ({task.status.value})?"
    elif operation == "create":
        preview = f"Create task “{payload.get('title', '')}”?"
    else:
        preview = f"Update task {task.id if task else ''}: {', '.join(changes.keys())}?"
    return PendingActionInfo(
        challenge=challenge,
        operation=operation,  # type: ignore[arg-type]
        expires_at=expires_at,
        preview=preview,
        task=TaskResponse.from_task(task) if task else None,
        changes=changes,
        owner_name=owner_name,
    )


def _task_search(
    db: Session,
    intent: ParsedIntent,
    user: User,
) -> list[Task]:
    query = TaskListQuery(
        page=1,
        page_size=MAX_CHAT_RESULTS,
        search=intent.search_text,
        status=TaskStatus(intent.status) if intent.status else None,
        priority=Priority(intent.priority) if intent.priority else None,
        overdue=intent.overdue,
        due_from=intent.due_range[0] if intent.due_range else None,
        due_to=intent.due_range[1] if intent.due_range else None,
    )
    tasks, _ = list_tasks(
        db,
        query,
        owner_id=None if user.role == UserRole.ADMIN else user.id,
    )
    return tasks


def _resolve_intent_task(
    db: Session,
    intent: ParsedIntent,
    user: User,
) -> tuple[Task | None, list[Task]]:
    if intent.task_id is not None:
        try:
            return get_task(
                db,
                intent.task_id,
                owner_id=None if user.role == UserRole.ADMIN else user.id,
            ), []
        except TaskNotFoundError:
            return None, []
    if intent.search_text:
        candidates = _task_search(db, ParsedIntent("search_tasks", search_text=intent.search_text), user)
        return (candidates[0] if len(candidates) == 1 else None), candidates
    return None, []


def _prepare_task_update(
    db: Session,
    user: User,
    conversation: ChatConversation,
    intent: ParsedIntent,
) -> tuple[str, list[Task], PendingActionInfo | None]:
    task, candidates = _resolve_intent_task(db, intent, user)
    if len(candidates) > 1:
        return "I found several matching tasks. Choose one by its task ID, then repeat the update.", candidates, None
    if task is None:
        return "I couldn't find an accessible task matching that request.", [], None
    data = TaskUpdate.model_validate(intent.changes)
    payload: dict[str, object] = {
        "changes": data.model_dump(mode="json", exclude_unset=True),
        "actor_role": user.role.value,
    }
    pending = _create_pending_action(
        db, user, conversation, "update", payload, task=task
    )
    return f"Review this proposed update and confirm to apply it. {pending.preview}", [], pending


def _prepare_task_delete(
    db: Session,
    user: User,
    conversation: ChatConversation,
    intent: ParsedIntent,
) -> tuple[str, list[Task], PendingActionInfo | None]:
    task, _ = _resolve_intent_task(db, intent, user)
    if task is None:
        return "I couldn't find an accessible task with that ID.", [], None
    owner = db.get(User, task.user_id)
    pending = _create_pending_action(
        db,
        user,
        conversation,
        "delete",
        {"actor_role": user.role.value},
        task=task,
        owner_name=owner.full_name if owner else None,
    )
    return f"Review the exact task before confirming deletion. {pending.preview}", [], pending


def _prepare_task_create(
    db: Session,
    user: User,
    conversation: ChatConversation,
    intent: ParsedIntent,
    message: str,
) -> tuple[str, PendingActionInfo | None]:
    owner_id = user.id
    owner_match = __import__("re").search(r"\bfor user(?: id)?\s+#?(\d+)\b", message, __import__("re").IGNORECASE)
    if owner_match:
        if user.role != UserRole.ADMIN:
            return "Only administrators can assign a task to another user.", None
        owner_id = int(owner_match.group(1))
        target_owner = db.get(User, owner_id)
        if target_owner is None or not target_owner.is_active:
            return "The requested task owner does not exist or is inactive.", None
    data = TaskCreate(
        title=intent.title or "",
        priority=Priority(intent.priority or "medium"),
        due_date=intent.due_date,
    )
    payload = data.model_dump(mode="json")
    payload["owner_id"] = owner_id
    payload["actor_role"] = user.role.value
    pending = _create_pending_action(db, user, conversation, "create", payload)
    return f"Review the proposed task and confirm to create it. {pending.preview}", pending


def _search_tasks_response(
    db: Session,
    user: User,
    intent: ParsedIntent,
) -> tuple[str, list[Task]]:
    results = _task_search(db, intent, user)
    if not results:
        return "I couldn't find any matching tasks.", []
    return f"I found {len(results)} matching task(s).", results


def _search_files_response(
    db: Session,
    user: User,
    intent: ParsedIntent,
) -> tuple[str, list[FileSearchHit]]:
    results = search_files(
        db,
        user_id=user.id,
        query=intent.search_text or "",
        page=1,
        page_size=MAX_CHAT_RESULTS,
    )
    if not results.items:
        return "I couldn't find matching files or spreadsheet content in your private files.", []
    return f"I found {len(results.items)} matching file result(s).", results.items


def handle_message(
    db: Session,
    user: User,
    message: str,
    conversation_id: int | None = None,
) -> ChatMessageResponse:
    conversation = _conversation(db, user, conversation_id, _redact_sensitive_text(message))
    _save_message(db, conversation, MessageRole.USER, _redact_sensitive_text(message))
    intent = parse_intent(message)
    tasks: list[Task] = []
    files: list[FileSearchHit] = []
    pending: PendingActionInfo | None = None

    if intent.name == "clarify_request":
        response = intent.clarification or "Could you clarify what you would like me to do?"
    elif intent.name in {"search_tasks", "get_task"}:
        if intent.name == "get_task":
            task, _ = _resolve_intent_task(db, intent, user)
            tasks = [task] if task else []
            response = "Here are the task details." if task else "I couldn't find an accessible task with that ID."
        else:
            response, tasks = _search_tasks_response(db, user, intent)
    elif intent.name in {"search_files", "search_spreadsheet_content"}:
        if intent.name == "search_spreadsheet_content":
            response, files = answer_spreadsheet_question(
                db, user, _redact_sensitive_text(message)
            )
        else:
            response, files = _search_files_response(db, user, intent)
    elif intent.name == "create_task":
        response, pending = _prepare_task_create(db, user, conversation, intent, message)
    elif intent.name == "update_task":
        response, tasks, pending = _prepare_task_update(db, user, conversation, intent)
    elif intent.name == "delete_task":
        response, tasks, pending = _prepare_task_delete(db, user, conversation, intent)
    else:
        response = "I can search tasks and your uploaded spreadsheets, or prepare task creation, updates, and deletions for your confirmation."

    _save_message(db, conversation, MessageRole.ASSISTANT, response)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return ChatMessageResponse(
        conversation_id=conversation.id,
        intent=intent.name,  # type: ignore[arg-type]
        assistant_message=response,
        tasks=[_task_result(task, user) for task in tasks],
        files=files,
        search_query=(
            (
                intent.search_text
                if intent.search_text and intent.search_text != message
                else None
            )
            if intent.name == "search_spreadsheet_content"
            else intent.search_text
        ) if files else None,
        pending_action=pending,
    )


def _load_pending_action(
    db: Session,
    user: User,
    challenge: str,
) -> PendingChatAction:
    challenge_hash = hashlib.sha256(challenge.encode("utf-8")).hexdigest()
    action = db.scalar(
        select(PendingChatAction)
        .where(
            PendingChatAction.challenge_hash == challenge_hash,
            PendingChatAction.user_id == user.id,
        )
        .with_for_update()
    )
    if action is None:
        raise ChatActionError(
            "Confirmation is invalid or does not belong to your account.",
            status_code=404,
        )
    return action


def _stale_action_preview(
    db: Session,
    user: User,
    action: PendingChatAction,
    task: Task,
) -> PendingActionInfo:
    action.cancelled_at = datetime.now(UTC)
    return _create_pending_action(
        db,
        user,
        db.get(ChatConversation, action.conversation_id),
        action.operation,
        dict(action.payload),
        task=task,
        owner_name=task.user.full_name if action.operation == "delete" else None,
    )


def confirm_action(
    db: Session,
    user: User,
    challenge: str,
) -> ChatMessageResponse:
    action = _load_pending_action(db, user, challenge)
    now = datetime.now(UTC)
    if action.consumed_at is not None or action.cancelled_at is not None:
        raise ChatActionError("This confirmation has already been used or cancelled.")
    if action.expires_at <= now:
        action.cancelled_at = now
        _save_audit(db, user, action.operation, action.target_task_id, AuditOutcome.FAILURE, [])
        db.commit()
        raise ChatActionError(
            "This confirmation expired. Please prepare the action again.",
            status_code=410,
        )

    conversation = db.get(ChatConversation, action.conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise ChatActionError("Conversation not found.")

    tasks: list[Task] = []
    files: list[FileSearchHit] = []
    if action.operation == "create":
        payload = dict(action.payload)
        owner_id = int(payload.pop("owner_id", user.id))
        payload.pop("actor_role", None)
        if owner_id != user.id and user.role != UserRole.ADMIN:
            action.cancelled_at = now
            _save_audit(
                db,
                user,
                "create",
                None,
                AuditOutcome.FAILURE,
                ["unauthorized_owner_assignment"],
            )
            db.commit()
            raise ChatActionError("Administrator access is required to assign this task.", status_code=403)
        data = TaskCreate.model_validate(payload)
        try:
            task = create_task(db, data, owner_id, commit=False)
        except TaskOwnerError as exc:
            action.cancelled_at = now
            _save_audit(
                db,
                user,
                "create",
                None,
                AuditOutcome.FAILURE,
                ["ineligible_owner"],
            )
            db.commit()
            raise ChatActionError(str(exc), status_code=409) from exc
        db.flush()
        action.target_task_id = task.id
        _save_audit(db, user, "create", task.id, AuditOutcome.SUCCESS, list(data.model_fields_set))
        response = f"Task {task.id} was created: {task.title}."
        tasks = [task]
    else:
        task_id = action.target_task_id
        if task_id is None:
            raise ChatActionError("The pending action has no task target.")
        task_query = select(Task).where(Task.id == task_id)
        if user.role != UserRole.ADMIN:
            task_query = task_query.where(Task.user_id == user.id)
        task = db.execute(
            task_query.with_for_update().execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if task is None:
            action.cancelled_at = now
            _save_audit(
                db,
                user,
                action.operation,
                task_id,
                AuditOutcome.FAILURE,
                ["target_no_longer_authorized"],
            )
            db.commit()
            raise ChatActionError("The task is no longer available to your account.", status_code=404)
        if task.updated_at != action.expected_updated_at:
            replacement = _stale_action_preview(db, user, action, task)
            _save_audit(db, user, action.operation, task_id, AuditOutcome.FAILURE, ["stale_record"])
            _save_message(
                db,
                conversation,
                MessageRole.ASSISTANT,
                "The task changed after the preview. Review the updated details and confirm again.",
            )
            db.commit()
            return ChatMessageResponse(
                conversation_id=conversation.id,
                intent="clarify_request",
                assistant_message="The task changed after the preview. Review the updated details and confirm again.",
                tasks=[_task_result(task, user)],
                pending_action=replacement,
            )
        if action.operation == "delete":
            action.target_task_id = None
            deleted_id = delete_task(
                db,
                task_id,
                owner_id=None if user.role == UserRole.ADMIN else user.id,
                commit=False,
            )
            tasks = []
            response = f"Task {deleted_id} was deleted."
            changed_fields = ["deleted"]
        elif action.operation == "update":
            changes = action.payload.get("changes")
            if not isinstance(changes, dict):
                raise ChatActionError("The pending update is invalid.")
            update_data = TaskUpdate.model_validate(changes)
            if user.role == UserRole.ADMIN:
                task = update_admin_task(db, task_id, update_data, commit=False)
            else:
                task = update_task(db, task_id, update_data, owner_id=user.id, commit=False)
            tasks = [task]
            response = f"Task {task.id} was updated."
            changed_fields = list(update_data.model_fields_set)
        else:
            raise ChatActionError("Unsupported pending action.")
        _save_audit(db, user, action.operation, task_id, AuditOutcome.SUCCESS, changed_fields)

    action.consumed_at = now
    _save_message(db, conversation, MessageRole.ASSISTANT, response)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return ChatMessageResponse(
        conversation_id=conversation.id,
        intent=f"{action.operation}_task",  # type: ignore[arg-type]
        assistant_message=response,
        tasks=[_task_result(task, user) for task in tasks],
        files=files,
    )


def cancel_action(db: Session, user: User, challenge: str) -> None:
    action = _load_pending_action(db, user, challenge)
    if action.consumed_at is not None or action.cancelled_at is not None:
        raise ChatActionError("This confirmation has already been used or cancelled.")
    action.cancelled_at = datetime.now(UTC)
    db.commit()


def get_conversation_history(
    db: Session,
    user: User,
    conversation_id: int,
) -> ChatHistoryResponse:
    conversation = db.scalar(
        select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise ChatAccessError("Conversation not found.")
    messages = db.scalars(
        select(ChatMessage)
        .where(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.role.in_((MessageRole.USER, MessageRole.ASSISTANT)),
        )
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .limit(100)
    ).all()
    return ChatHistoryResponse(
        conversation_id=conversation.id,
        messages=[
            ChatHistoryMessage(
                id=message.id,
                role=message.role.value,  # type: ignore[arg-type]
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )

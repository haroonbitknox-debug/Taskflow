import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings

TASK_ID = re.compile(r"\btask(?:\s+id)?\s*#?(\d+)\b", re.IGNORECASE)
STATUS = re.compile(r"\b(pending|in[\s_-]+progress|completed|complete|done)\b", re.IGNORECASE)
RELATIVE_DUE = re.compile(r"\b(?:due\s+)?(today|tomorrow|next week)\b", re.IGNORECASE)


def _extract_priority(message: str) -> str | None:
    match = re.search(
        r"\b(low|medium|high)[- ]priority\b|\bpriority\s+(?:to\s+)?(low|medium|high)\b",
        message,
        re.IGNORECASE,
    )
    if match is None:
        return None
    return (match.group(1) or match.group(2)).casefold()


@dataclass
class ParsedIntent:
    name: str
    task_id: int | None = None
    search_text: str | None = None
    priority: str | None = None
    status: str | None = None
    overdue: bool = False
    due_range: tuple[datetime, datetime] | None = None
    due_date: datetime | None = None
    changes: dict[str, object] = field(default_factory=dict)
    title: str | None = None
    clarification: str | None = None


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.app_timezone))


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=ZoneInfo(settings.app_timezone)).astimezone(UTC)


def _next_week_range(now: datetime) -> tuple[datetime, datetime]:
    days_to_monday = (7 - now.weekday()) % 7
    if days_to_monday == 0:
        days_to_monday = 7
    monday = now.date() + timedelta(days=days_to_monday)
    sunday = monday + timedelta(days=6)
    zone = ZoneInfo(settings.app_timezone)
    start = datetime.combine(monday, time.min, tzinfo=zone).astimezone(UTC)
    end = _end_of_day(sunday)
    return start, end


def _day_range(now: datetime, offset: int) -> tuple[datetime, datetime]:
    due_day = now.date() + timedelta(days=offset)
    zone = ZoneInfo(settings.app_timezone)
    return (
        datetime.combine(due_day, time.min, tzinfo=zone).astimezone(UTC),
        _end_of_day(due_day),
    )


def _parse_due_date(message: str) -> tuple[datetime | None, str | None]:
    lowered = message.casefold()
    now = _local_now()
    if re.search(r"\bnext week\b", lowered):
        return None, "“Next week” could mean any day. Which day should the task be due?"
    match = re.search(r"\b(?:due\s+)?(today|tomorrow)\b", lowered)
    if match:
        due_day = now.date() + (timedelta(days=1) if match.group(1) == "tomorrow" else timedelta())
        return _end_of_day(due_day), None
    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", message)
    if iso_match:
        try:
            due_day = date.fromisoformat(iso_match.group(1))
        except ValueError:
            return None, "I couldn't read that due date. Please provide a valid date."
        return _end_of_day(due_day), None
    return None, None


def _extract_task_title(message: str) -> str | None:
    match = re.search(
        r"\b(?:called|named|titled)\s+(.+?)(?=(?:,\s*|\s+)(?:due\b|with\b|for user(?: id)?\b|\b(?:low|medium|high)[- ]priority\b)|[.!?]*$)",
        message,
        re.IGNORECASE,
    )
    if match:
        title = match.group(1).strip(" ,.!?")
    else:
        match = re.search(
            r"\b(?:create|add|make)\s+(?:(?:a|an)\s+)?(?:(?:low|medium|high)[- ]priority\s+)?task\s+(?:to|for)\s+(.+?)(?=(?:,\s*|\s+)(?:due\b|with\b)|[.!?]*$)",
            message,
            re.IGNORECASE,
        )
        if not match:
            return None
        title = match.group(1).strip(" ,.!?")
        title = re.sub(r"\s+(?:today|tomorrow|next week)$", "", title, flags=re.IGNORECASE)
    return title[:200] if title else None


def _search_text(message: str) -> str | None:
    value = message.strip()
    replacements = (
        r"^(?:please\s+)?(?:find|search for|search|show|list|which|what are|tell me)\s+",
        r"\b(?:all|my|the|tasks?|that are|with|priority\s+(?:to\s+)?(?:low|medium|high)|priority|overdue|due (?:today|tomorrow|next week)|today|tomorrow|pending|in[\s_-]+progress|completed|complete|done|high[- ]priority|low[- ]priority|medium[- ]priority)\b",
    )
    value = re.sub(replacements[0], "", value, flags=re.IGNORECASE)
    value = re.sub(replacements[1], " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" ?.!,'\"")
    return value or None


def _file_search_text(message: str) -> str | None:
    value = message.strip()
    value = re.sub(
        r"^(?:please\s+)?(?:search|find|look for|which worksheet contains|which sheet contains|find rows containing)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\bmy\s+(?:uploaded\s+)?(?:excel\s+)?(?:files?|spreadsheets?|workbooks?)\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\b(?:uploaded\s+files?|spreadsheet contents?|file contents?)\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\bfor\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\bnumber\s+(?=\w)", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" ?.!,'\"")
    return value or None


def parse_intent(message: str) -> ParsedIntent:
    text = message.strip()
    lowered = text.casefold()
    task_id_match = TASK_ID.search(text)
    task_id = int(task_id_match.group(1)) if task_id_match else None

    if re.search(r"\b(delete|remove|discard)\b", lowered):
        if task_id is None:
            return ParsedIntent(
                "clarify_request",
                clarification="Please include the exact task ID you want to delete.",
            )
        return ParsedIntent("delete_task", task_id=task_id)

    if re.search(r"\b(change|update|set|mark|rename|reschedule)\b", lowered) and "task" in lowered:
        changes: dict[str, object] = {}
        priority = _extract_priority(text)
        status = STATUS.search(text)
        if priority:
            changes["priority"] = priority
        if status:
            parsed_status = re.sub(r"[\s-]+", "_", status.group(1).casefold())
            changes["status"] = {
                "complete": "completed",
                "done": "completed",
            }.get(parsed_status, parsed_status)
        if re.search(r"\btitle\b", lowered):
            title_match = re.search(r"\b(?:title|rename)(?:\s+to)?\s+(.+?)[.!?]*$", text, re.IGNORECASE)
            if title_match:
                changes["title"] = title_match.group(1).strip(" .!?")[:200]
        due_date, clarification = _parse_due_date(text)
        if due_date:
            changes["due_date"] = due_date.isoformat()
        if clarification:
            return ParsedIntent("clarify_request", clarification=clarification)
        if not changes:
            return ParsedIntent("clarify_request", clarification="What task field should I change?")
        target_text = None
        if task_id is None:
            target_match = re.search(
                r"\btask\s+(.+?)(?:['’]s)\s+(?:priority|status|title|due(?: date)?|deadline)\b",
                text,
                re.IGNORECASE,
            )
            if target_match:
                target_text = target_match.group(1).strip(" '\"")
        if task_id is None and not target_text:
            return ParsedIntent(
                "clarify_request",
                clarification="Please include a task ID or a distinctive part of its title.",
            )
        return ParsedIntent("update_task", task_id=task_id, search_text=target_text, changes=changes)

    if re.search(r"\b(create|add|make)\b", lowered) and "task" in lowered:
        title = _extract_task_title(text)
        if not title:
            return ParsedIntent(
                "clarify_request",
                clarification="What should the new task be called?",
            )
        due_date, clarification = _parse_due_date(text)
        if clarification:
            return ParsedIntent("clarify_request", clarification=clarification)
        priority = _extract_priority(text) or "medium"
        return ParsedIntent("create_task", title=title, priority=priority, due_date=due_date)

    if re.search(r"\b(file|files|spreadsheet|spreadsheets|excel|workbook|worksheet|sheet|rows?|cells?|invoice|customer|email)\b", lowered) and re.search(r"\b(find|search|look|which|where|show|list|count|total|sum|average|group|compare|how many|number of|percent(?:age)?)\b", lowered):
        intent_name = (
            "search_spreadsheet_content"
            if re.search(r"\b(spreadsheet|excel|workbook|worksheet|sheet|rows?|cells?|invoice|customer|email|contents?)\b", lowered)
            else "search_files"
        )
        query = _file_search_text(text)
        if not query:
            return ParsedIntent("clarify_request", clarification="What should I search for in your files?")
        return ParsedIntent(intent_name, search_text=query)

    if (
        re.search(r"\b(projects?|records?|entries|deals|invoices?)\b", lowered)
        and not re.search(r"\btasks?\b", lowered)
        and re.search(
            r"\b(find|search|show|list|count|total|sum|average|group|compare|how many|number of|percent(?:age)?)\b",
            lowered,
        )
    ):
        return ParsedIntent("search_spreadsheet_content", search_text=text)

    if re.search(r"\b(?:who owns|owner of)\b", lowered) and not re.search(
        r"\btasks?\b", lowered
    ):
        return ParsedIntent("search_spreadsheet_content", search_text=text)

    if task_id is not None and re.search(r"\b(show|get|open|details?|find)\b", lowered):
        return ParsedIntent("get_task", task_id=task_id)

    if re.search(r"\b(task|tasks|overdue|pending|in[\s_-]+progress|completed|priority|due next week)\b", lowered) and re.search(r"\b(find|search|show|list|which|what|overdue|due)\b", lowered):
        priority = _extract_priority(text)
        status_match = STATUS.search(text)
        status = None
        if status_match:
            raw_status = re.sub(r"[\s-]+", "_", status_match.group(1).casefold())
            status = {"complete": "completed", "done": "completed"}.get(raw_status, raw_status)
        overdue = "overdue" in lowered
        due_range = _next_week_range(_local_now()) if re.search(r"\bnext week\b", lowered) else None
        day_match = re.search(r"\b(?:due\s+)?(today|tomorrow)\b", lowered)
        if due_range is None and day_match:
            due_range = _day_range(_local_now(), 1 if day_match.group(1) == "tomorrow" else 0)
        return ParsedIntent(
            "search_tasks",
            search_text=None if overdue or due_range else _search_text(text),
            priority=priority,
            status=status,
            overdue=overdue,
            due_range=due_range,
        )

    if re.search(r"\b(find|search for|search|show|list)\b", lowered):
        query = _search_text(text)
        if query:
            return ParsedIntent("search_tasks", search_text=query)

    return ParsedIntent("unsupported_request")

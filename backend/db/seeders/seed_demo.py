import csv
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    FileIndexEntry,
    FileProcessingStatus,
    Priority,
    Tag,
    Task,
    TaskStatus,
    UploadedFile,
    User,
    UserRole,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    BACKEND_DIR / "uploads" / "demo-fixtures" / "taskflow_sample.csv"
)
FIXTURE_RELATIVE_PATH = Path("demo-fixtures") / FIXTURE_PATH.name
ADMIN_EMAIL = "admin@taskflow.local"
ADMIN_PASSWORD = "TaskFlow-Admin-Dev-2026!"
USER_PASSWORD = "TaskFlow-User-Dev-2026!"

DEMO_USERS = [
    ("Alex Morgan", "alex@taskflow.local"),
    ("Jordan Lee", "jordan@taskflow.local"),
    ("Sam Rivera", "sam@taskflow.local"),
    ("Taylor Kim", "taylor@taskflow.local"),
    ("Casey Patel", "casey@taskflow.local"),
]
TASK_TEMPLATES = [
    (
        "Prepare weekly plan",
        TaskStatus.PENDING,
        Priority.MEDIUM,
        "Planning",
        -4,
        ["planning"],
    ),
    (
        "Review project milestones",
        TaskStatus.IN_PROGRESS,
        Priority.HIGH,
        "Projects",
        -1,
        ["work", "urgent"],
    ),
    (
        "Update task checklist",
        TaskStatus.COMPLETED,
        Priority.LOW,
        "Admin",
        -3,
        ["work"],
    ),
    (
        "Schedule team check-in",
        TaskStatus.PENDING,
        Priority.HIGH,
        "Meetings",
        2,
        ["planning", "urgent"],
    ),
    (
        "Draft project notes",
        TaskStatus.IN_PROGRESS,
        Priority.MEDIUM,
        "Projects",
        6,
        ["work"],
    ),
    (
        "Organize reference files",
        TaskStatus.PENDING,
        Priority.LOW,
        "Personal",
        12,
        ["personal"],
    ),
]
TAG_NAMES = ("planning", "work", "urgent", "personal")


def ensure_development_environment() -> None:
    if (
        "app_env" not in settings.model_fields_set
        or settings.app_env.casefold() != "development"
    ):
        raise RuntimeError(
            "Demo seeding is allowed only when APP_ENV=development is explicitly "
            "set in backend/.env or the process environment."
        )


def get_or_create_user(
    db: Session,
    hasher: PasswordHasher,
    name: str,
    email: str,
    role: UserRole,
    password: str,
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            full_name=name,
            email=email,
            password_hash=hasher.hash(password),
            role=role,
        )
        db.add(user)
        db.flush()
    return user


def seed_tags(db: Session, user: User) -> dict[str, Tag]:
    tags: dict[str, Tag] = {}
    for name in TAG_NAMES:
        tag = db.scalar(
            select(Tag).where(Tag.user_id == user.id, Tag.name == name)
        )
        if tag is None:
            tag = Tag(user_id=user.id, name=name, slug=name)
            db.add(tag)
            db.flush()
        tags[name] = tag
    return tags


def seed_tasks(
    db: Session, user: User, tags: dict[str, Tag], now: datetime
) -> int:
    added = 0
    for title, status, priority, category, due_offset, tag_names in TASK_TEMPLATES:
        task_title = f"Demo: {title}"
        task = db.scalar(
            select(Task).where(Task.user_id == user.id, Task.title == task_title)
        )
        if task is None:
            task = Task(user_id=user.id, title=task_title)
            db.add(task)
            added += 1
        task.description = "Sample development task. No real user data is used."
        task.status = status
        task.priority = priority
        task.category = category
        task.due_date = now + timedelta(days=due_offset)
        task.completed_at = (
            now - timedelta(days=1) if status == TaskStatus.COMPLETED else None
        )
        task.tags = [tags[name] for name in tag_names]
    return added


def seed_spreadsheet_fixture(db: Session, user: User) -> int:
    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"Demo spreadsheet fixture not found: {FIXTURE_PATH}")

    stored_filename = FIXTURE_PATH.name
    uploaded_file = db.scalar(
        select(UploadedFile).where(
            UploadedFile.stored_filename == stored_filename
        )
    )
    if uploaded_file is None:
        uploaded_file = UploadedFile(
            user_id=user.id,
            original_filename="TaskFlow Sample Project Tracker.csv",
            stored_filename=stored_filename,
            relative_path=FIXTURE_RELATIVE_PATH.as_posix(),
            extension=".csv",
            mime_type="text/csv",
            file_size=FIXTURE_PATH.stat().st_size,
            processing_status=FileProcessingStatus.READY,
        )
        db.add(uploaded_file)
        db.flush()

    existing_entry_id = db.scalar(
        select(FileIndexEntry.id)
        .where(FileIndexEntry.uploaded_file_id == uploaded_file.id)
        .limit(1)
    )
    if existing_entry_id is not None:
        return 0

    with FIXTURE_PATH.open(encoding="utf-8", newline="") as fixture:
        rows = list(csv.reader(fixture))
    headers = rows[0]
    added = 0
    for row_number, row in enumerate(rows[1:], start=2):
        for column_name, content in zip(headers, row):
            normalized = re.sub(r"\s+", " ", content).strip().casefold()
            db.add(
                FileIndexEntry(
                    uploaded_file_id=uploaded_file.id,
                    user_id=user.id,
                    worksheet_name="Projects",
                    row_number=row_number,
                    column_name=column_name,
                    searchable_content=content,
                    normalized_content=normalized[:512],
                )
            )
            added += 1
    return added


def main() -> None:
    ensure_development_environment()
    hasher = PasswordHasher()
    now = datetime.now(UTC)

    with SessionLocal.begin() as db:
        admin = get_or_create_user(
            db,
            hasher,
            "TaskFlow Development Admin",
            ADMIN_EMAIL,
            UserRole.ADMIN,
            ADMIN_PASSWORD,
        )
        users = [
            get_or_create_user(
                db, hasher, name, email, UserRole.USER, USER_PASSWORD
            )
            for name, email in DEMO_USERS
        ]

        task_count = 0
        for user in [admin, *users]:
            task_count += seed_tasks(db, user, seed_tags(db, user), now)
        index_count = seed_spreadsheet_fixture(db, admin)

    print(
        f"Seeded {len(users) + 1} demo users; added {task_count} tasks "
        f"and {index_count} spreadsheet index entries."
    )
    print("Existing demo users and tasks were retained/updated on rerun.")


if __name__ == "__main__":
    main()

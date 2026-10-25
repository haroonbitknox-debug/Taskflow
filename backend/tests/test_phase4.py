from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    FileProcessingStatus,
    UploadedFile,
    User,
    UserRole,
)
from app.utils.passwords import hash_password
from app.utils.tokens import create_access_token

USER_PASSWORD = "Phase-Four-Test-Password-84!"


def csrf(client: TestClient) -> dict[str, str]:
    token = client.get("/api/auth/csrf").json()["csrf_token"]
    return {"X-CSRF-Token": token}


def create_account(
    client: TestClient,
    full_name: str,
    email: str,
) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": USER_PASSWORD,
        },
        headers=csrf(client),
    )
    assert response.status_code == 201, response.text
    return response.json()["user"]


def authenticate_as(client: TestClient, user: User) -> None:
    client.cookies.set("taskflow_access", create_access_token(str(user.id)))
    csrf(client)


@pytest.fixture()
def admin_user(db_session: Session) -> User:
    user = User(
        full_name="Phase 4 Admin",
        email="phase4.admin@example.test",
        password_hash=hash_password(USER_PASSWORD),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_task_crud_status_tags_and_validation(
    client: TestClient,
) -> None:
    create_account(client, "Task Owner", "task.owner@example.test")
    headers = csrf(client)
    created = client.post(
        "/api/tasks",
        json={
            "title": "Write unit tests",
            "description": "Cover task lifecycle",
            "priority": "high",
            "category": "Engineering",
            "tags": ["backend", "quality", "Backend"],
            "due_date": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["tags"] == ["backend", "quality"]
    assert task["completed_at"] is None
    assert task["created_at"] and task["updated_at"]

    fetched = client.get(f"/api/tasks/{task['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Write unit tests"

    completed = client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "completed"},
        headers=csrf(client),
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None
    assert completed.json()["updated_at"] >= task["updated_at"]

    reopened = client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "pending", "tags": []},
        headers=csrf(client),
    )
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None
    assert reopened.json()["tags"] == []

    invalid = client.post(
        "/api/tasks",
        json={"title": "", "status": "finished", "user_id": 999},
        headers=csrf(client),
    )
    assert invalid.status_code == 422
    invalid_update = client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": None},
        headers=csrf(client),
    )
    assert invalid_update.status_code == 422

    deleted = client.delete(f"/api/tasks/{task['id']}", headers=csrf(client))
    assert deleted.status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


def test_task_id_cannot_bypass_ownership(
    client: TestClient,
    db_session: Session,
) -> None:
    first = create_account(client, "First Owner", "first.owner@example.test")
    first_task = client.post(
        "/api/tasks", json={"title": "Private first task"}, headers=csrf(client)
    ).json()
    second_user = User(
        full_name="Second Owner",
        email="second.owner@example.test",
        password_hash=hash_password(USER_PASSWORD),
        role=UserRole.USER,
    )
    db_session.add(second_user)
    db_session.commit()

    second_client = TestClient(client.app)
    second_client.cookies.set(
        "taskflow_access", create_access_token(str(second_user.id))
    )
    csrf(second_client)
    assert second_client.get(f"/api/tasks/{first_task['id']}").status_code == 404
    assert second_client.patch(
        f"/api/tasks/{first_task['id']}",
        json={"title": "stolen"},
        headers=csrf(second_client),
    ).status_code == 404
    assert second_client.delete(
        f"/api/tasks/{first_task['id']}", headers=csrf(second_client)
    ).status_code == 404
    assert second_client.get("/api/tasks").json()["total"] == 0
    assert first["id"] != second_user.id
    second_client.close()


def test_task_filters_search_pagination_and_order(
    client: TestClient,
) -> None:
    create_account(client, "Filter Owner", "filter.owner@example.test")
    now = datetime.now(UTC)
    payloads = [
        {
            "title": "Overdue high task",
            "description": "needle in details",
            "status": "pending",
            "priority": "high",
            "category": "Ops",
            "tags": ["urgent"],
            "due_date": (now - timedelta(days=1)).isoformat(),
        },
        {
            "title": "Upcoming medium task",
            "status": "in_progress",
            "priority": "medium",
            "category": "Ops",
            "tags": ["planning"],
            "due_date": (now + timedelta(days=3)).isoformat(),
        },
        {
            "title": "Completed low task",
            "status": "completed",
            "priority": "low",
            "category": "Home",
        },
    ]
    for payload in payloads:
        response = client.post("/api/tasks", json=payload, headers=csrf(client))
        assert response.status_code == 201, response.text

    listed = client.get("/api/tasks?page=1&page_size=2&sort_by=title&sort_direction=asc")
    assert listed.status_code == 200
    assert listed.json()["total"] == 3
    assert listed.json()["page"] == 1
    assert listed.json()["page_size"] == 2
    assert len(listed.json()["items"]) == 2

    next_page = client.get("/api/tasks?page=2&page_size=2&sort_by=title&sort_direction=asc")
    assert len(next_page.json()["items"]) == 1
    assert listed.json()["items"][0]["id"] != next_page.json()["items"][0]["id"]
    assert client.get("/api/tasks?page_size=101").status_code == 422

    overdue = client.get("/api/tasks?overdue=true")
    assert overdue.json()["total"] == 1
    assert overdue.json()["items"][0]["title"] == "Overdue high task"
    assert client.get("/api/tasks?status=pending&priority=high").json()["total"] == 1
    assert client.get("/api/tasks?search=needle").json()["total"] == 1
    assert client.get("/api/tasks?search=urgent").json()["total"] == 1
    assert client.get("/api/tasks?search=Ops").json()["total"] == 2
    assert client.get("/api/tasks?sort_by=unknown").status_code == 422
    assert client.get("/api/tasks?due_from=2026-10-21T12:00:00&due_to=2026-10-20T12:00:00").status_code == 422


def test_admin_user_management_and_last_admin_safeguard(
    client: TestClient,
    db_session: Session,
    admin_user: User,
) -> None:
    authenticate_as(client, admin_user)
    target = create_account(client, "Managed User", "managed.user@example.test")
    listing = client.get("/api/admin/users?search=managed&role=user&is_active=true")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["registered_total"] == 2
    assert listing.json()["admin_total"] == 1
    assert listing.json()["regular_user_total"] == 1
    assert "password_hash" not in listing.json()["items"][0]
    assert "password_hash" not in listing.json()

    second_page = client.get("/api/admin/users?page=2&page_size=1")
    assert second_page.status_code == 200
    assert second_page.json()["total"] == 2
    assert second_page.json()["registered_total"] == 2
    assert second_page.json()["admin_total"] == 1
    assert second_page.json()["regular_user_total"] == 1
    assert len(second_page.json()["items"]) == 1

    details = client.get(f"/api/admin/users/{target['id']}")
    assert details.status_code == 200
    created = client.post(
        "/api/admin/users",
        json={
            "full_name": "Admin Created",
            "email": "admin.created@example.test",
            "password": USER_PASSWORD,
            "role": "user",
        },
        headers=csrf(client),
    )
    assert created.status_code == 201
    assert "password_hash" not in created.json()
    assert client.patch(
        f"/api/admin/users/{target['id']}",
        json={"is_active": False},
        headers=csrf(client),
    ).json()["is_active"] is False

    last_admin = client.patch(
        f"/api/admin/users/{admin_user.id}",
        json={"is_active": False},
        headers=csrf(client),
    )
    assert last_admin.status_code == 409
    self_delete = client.delete(
        f"/api/admin/users/{admin_user.id}", headers=csrf(client)
    )
    assert self_delete.status_code == 422
    assert client.delete(
        f"/api/admin/users/{target['id']}", headers=csrf(client)
    ).status_code == 204
    assert db_session.get(User, target["id"]) is None
    assert db_session.scalar(
        select(AuditLog.id).where(AuditLog.target_entity == "user")
    )


def test_regular_user_cannot_access_admin_routes(client: TestClient) -> None:
    create_account(client, "Regular Account", "regular.account@example.test")
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/tasks").status_code == 403
    assert client.get("/api/admin/dashboard/summary").status_code == 403


def test_admin_user_list_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/admin/users")
    assert response.status_code == 401


def test_admin_task_routes_and_audit_logs(
    client: TestClient,
    db_session: Session,
    admin_user: User,
) -> None:
    authenticate_as(client, admin_user)
    target = create_account(client, "Task Target", "task.target@example.test")
    created = client.post(
        "/api/admin/tasks",
        json={"user_id": target["id"], "title": "Assigned by admin", "tags": ["admin"]},
        headers=csrf(client),
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["user_id"] == target["id"]
    assert client.get(f"/api/admin/tasks/{task['id']}").status_code == 200
    assert client.patch(
        f"/api/admin/tasks/{task['id']}",
        json={"user_id": admin_user.id, "title": "Reassigned"},
        headers=csrf(client),
    ).json()["user_id"] == admin_user.id
    assert client.get(f"/api/admin/tasks?owner_id={admin_user.id}").json()["total"] == 1
    assert client.post(
        "/api/admin/tasks",
        json={"user_id": 999999, "title": "Invalid owner"},
        headers=csrf(client),
    ).status_code == 422
    assert client.delete(
        f"/api/admin/tasks/{task['id']}", headers=csrf(client)
    ).status_code == 204
    actions = db_session.scalars(
        select(AuditLog.action_type)
        .where(
            AuditLog.target_entity == "task",
            AuditLog.actor_id == admin_user.id,
        )
        .order_by(AuditLog.id)
    ).all()
    assert actions == ["create", "update", "delete"]


def test_admin_user_delete_removes_private_files(
    client: TestClient,
    db_session: Session,
    admin_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import admin_user_service

    monkeypatch.setattr(admin_user_service, "UPLOADS_ROOT", tmp_path / "uploads")
    authenticate_as(client, admin_user)
    target = User(
        full_name="File Owner",
        email="file.owner@example.test",
        password_hash=hash_password(USER_PASSWORD),
    )
    db_session.add(target)
    db_session.commit()
    private_file = tmp_path / "uploads" / str(target.id) / "private.txt"
    private_file.parent.mkdir(parents=True)
    private_file.write_text("private sample", encoding="utf-8")
    metadata = UploadedFile(
        user_id=target.id,
        original_filename="private.txt",
        stored_filename=f"private-{target.id}.txt",
        relative_path=f"{target.id}/private.txt",
        extension=".txt",
        mime_type="text/plain",
        file_size=14,
        processing_status=FileProcessingStatus.READY,
    )
    db_session.add(metadata)
    db_session.commit()
    response = client.delete(
        f"/api/admin/users/{target.id}", headers=csrf(client)
    )
    assert response.status_code == 204
    assert not private_file.exists()


def test_dashboard_summaries_are_owner_scoped(
    client: TestClient,
    db_session: Session,
    admin_user: User,
) -> None:
    create_account(client, "Dashboard User", "dashboard.user@example.test")
    client.post("/api/tasks", json={"title": "My task"}, headers=csrf(client))
    user_summary = client.get("/api/dashboard/summary")
    assert user_summary.status_code == 200
    assert user_summary.json()["task_total"] == 1

    authenticate_as(client, admin_user)
    client.post("/api/tasks", json={"title": "Admin task"}, headers=csrf(client))
    expected_user_total = db_session.scalar(select(func.count(User.id)))
    admin_summary = client.get("/api/admin/dashboard/summary")
    assert admin_summary.status_code == 200
    assert admin_summary.json()["task_total"] == 2
    assert admin_summary.json()["user_total"] == expected_user_total
    assert "password_hash" not in str(admin_summary.json())


def test_dashboard_recent_tasks_are_ordered_by_update(
    client: TestClient,
) -> None:
    create_account(client, "Recent Tasks User", "recent.tasks@example.test")
    first = client.post(
        "/api/tasks", json={"title": "Created first"}, headers=csrf(client)
    ).json()
    client.post("/api/tasks", json={"title": "Created second"}, headers=csrf(client))
    updated = client.patch(
        f"/api/tasks/{first['id']}",
        json={"title": "Updated first"},
        headers=csrf(client),
    )
    assert updated.status_code == 200

    summary = client.get("/api/dashboard/summary")
    assert summary.status_code == 200
    assert [task["title"] for task in summary.json()["recent_tasks"]] == [
        "Updated first",
        "Created second",
    ]

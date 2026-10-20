from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, require_admin, require_csrf
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.db.session import get_db
from app.models import User, UserRole
from app.utils.passwords import hash_password, verify_password
from app.utils.tokens import create_access_token

PASSWORD = "Passphrase-For-TaskFlow-42!"
ANOTHER_PASSWORD = "A-Different-Passphrase-61!"
REGISTER_PAYLOAD = {
    "full_name": "Test User",
    "email": "test.user@example.test",
    "password": PASSWORD,
}


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/auth/csrf")
    token = response.json()["csrf_token"]
    return {"X-CSRF-Token": token}


def register_user(client: TestClient, **overrides: object):
    payload = {**REGISTER_PAYLOAD, **overrides}
    return client.post(
        "/api/auth/register", json=payload, headers=csrf_headers(client)
    )


@pytest.fixture()
def admin_probe_client(db_session: Session):
    probe = FastAPI()
    probe.include_router(auth_router, prefix="/api")
    probe.include_router(users_router, prefix="/api")

    @probe.get("/api/test-admin")
    def test_admin(user: User = Depends(require_admin)) -> dict[str, bool]:
        return {"ok": True}

    def override_get_db():
        yield db_session

    probe.dependency_overrides[get_db] = override_get_db
    with TestClient(probe) as test_client:
        test_client.get("/api/auth/csrf")
        yield test_client
    probe.dependency_overrides.clear()


def test_successful_registration(client: TestClient, db_session: Session) -> None:
    response = register_user(client)
    assert response.status_code == 201
    result = response.json()
    assert result["user"]["email"] == REGISTER_PAYLOAD["email"]
    assert result["user"]["role"] == "user"
    assert "password_hash" not in result["user"]
    user = db_session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    assert user is not None
    assert verify_password(PASSWORD, user.password_hash)


def test_duplicate_email_rejected(client: TestClient) -> None:
    assert register_user(client).status_code == 201
    response = register_user(client, full_name="Duplicate User")
    assert response.status_code == 409


def test_password_hashing_uses_argon2() -> None:
    hashed = hash_password(PASSWORD)
    assert hashed.startswith("$argon2id$")
    assert hashed != PASSWORD
    assert verify_password(PASSWORD, hashed)
    assert not verify_password(ANOTHER_PASSWORD, hashed)


def test_successful_and_failed_login(client: TestClient) -> None:
    assert register_user(client).status_code == 201
    response = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": PASSWORD},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == REGISTER_PAYLOAD["email"]
    assert "taskflow_access" in response.cookies

    failed = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": ANOTHER_PASSWORD},
        headers=csrf_headers(client),
    )
    assert failed.status_code == 401


def test_expired_and_invalid_tokens(client: TestClient) -> None:
    csrf_headers(client)
    client.cookies.set(
        "taskflow_access",
        create_access_token("1", expires_delta=timedelta(seconds=-1)),
    )
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("taskflow_access", "not.a.valid.jwt")
    assert client.get("/api/auth/me").status_code == 401


def test_profile_access_and_update(client: TestClient) -> None:
    assert register_user(client).status_code == 201
    response = client.get("/api/users/me")
    assert response.status_code == 200
    assert response.json()["full_name"] == "Test User"

    updated = client.patch(
        "/api/users/me",
        json={"full_name": "Updated Test User"},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Test User"

    escalation = client.patch(
        "/api/users/me",
        json={"role": "admin"},
        headers=csrf_headers(client),
    )
    assert escalation.status_code == 422


def test_password_change_requires_current_password(client: TestClient) -> None:
    assert register_user(client).status_code == 201
    wrong = client.post(
        "/api/auth/change-password",
        json={"current_password": ANOTHER_PASSWORD, "new_password": "Another-Strong-Pass-73!"},
        headers=csrf_headers(client),
    )
    assert wrong.status_code == 400

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD, "new_password": ANOTHER_PASSWORD},
        headers=csrf_headers(client),
    )
    assert changed.status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    logged_in = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": ANOTHER_PASSWORD},
        headers=csrf_headers(client),
    )
    assert logged_in.status_code == 200


def test_regular_user_denied_admin_access(admin_probe_client: TestClient) -> None:
    assert register_user(admin_probe_client).status_code == 201
    response = admin_probe_client.get("/api/test-admin")
    assert response.status_code == 403


def test_inactive_account_rejected(
    client: TestClient, db_session: Session
) -> None:
    assert register_user(client).status_code == 201
    user = db_session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    assert user is not None
    user.is_active = False
    db_session.commit()
    assert client.get("/api/auth/me").status_code == 403
    login = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": PASSWORD},
        headers=csrf_headers(client),
    )
    assert login.status_code == 403


def test_registration_cannot_assign_admin_role(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={**REGISTER_PAYLOAD, "role": "admin"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
    assert client.get("/api/auth/me").status_code == 401


def test_state_changing_requests_require_csrf(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 403


def test_last_active_admin_cannot_be_demoted(db_session: Session) -> None:
    admin = User(
        full_name="Only Admin",
        email="only.admin@example.test",
        password_hash=hash_password(PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    admin.role = UserRole.USER
    with pytest.raises(ValueError, match="last active administrator"):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(User, admin.id).role == UserRole.ADMIN

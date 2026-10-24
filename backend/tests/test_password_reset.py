import hashlib
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import PasswordResetToken, User
from app.services import email_service
from app.services import password_reset_service
from app.utils.passwords import hash_password, verify_password

CURRENT_PASSWORD = "Existing-Passphrase-31!"
NEW_PASSWORD = "Replacement-Passphrase-48!"
ACCOUNT_EMAIL = "recovery.user@example.test"


@pytest.fixture()
def recovery_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        class_=Session,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    db = factory()
    db.add(
        User(
            full_name="Recovery User",
            email=ACCOUNT_EMAIL,
            password_hash=hash_password(CURRENT_PASSWORD),
        )
    )
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "mail_host", "smtp.example.test")
    monkeypatch.setattr(settings, "mail_from", "TaskFlow <no-reply@example.test>")
    monkeypatch.setattr(settings, "password_reset_request_limit", 3)
    monkeypatch.setattr(settings, "password_reset_verify_limit", 30)
    with TestClient(app) as client:
        client.get("/api/auth/csrf")
        yield client, db
    app.dependency_overrides.clear()
    db.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


def _csrf(client: TestClient) -> dict[str, str]:
    token = client.get("/api/auth/csrf").json()["csrf_token"]
    return {"X-CSRF-Token": token}


def test_reset_changes_password_and_token_is_single_use(
    recovery_client: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = recovery_client
    sent_tokens: list[str] = []
    monkeypatch.setattr(
        password_reset_service,
        "send_password_reset_email",
        lambda recipient, token: sent_tokens.append(token),
    )

    requested = client.post(
        "/api/auth/password-reset/request",
        json={"email": ACCOUNT_EMAIL},
        headers=_csrf(client),
    )
    assert requested.status_code == 200
    assert requested.json()["message"] == password_reset_service.GENERIC_RESET_MESSAGE
    assert len(sent_tokens) == 1

    reset = db.query(PasswordResetToken).one()
    assert reset.token_hash == hashlib.sha256(sent_tokens[0].encode()).hexdigest()
    assert sent_tokens[0] not in reset.token_hash

    confirmed = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": sent_tokens[0], "new_password": NEW_PASSWORD},
        headers=_csrf(client),
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["message"].endswith("sign in.")
    user = db.query(User).filter_by(email=ACCOUNT_EMAIL).one()
    assert verify_password(NEW_PASSWORD, user.password_hash)
    assert not verify_password(CURRENT_PASSWORD, user.password_hash)
    assert reset.used_at is not None

    replayed = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": sent_tokens[0], "new_password": CURRENT_PASSWORD},
        headers=_csrf(client),
    )
    assert replayed.status_code == 400
    assert verify_password(NEW_PASSWORD, user.password_hash)


def test_expired_or_invalid_tokens_cannot_reset_password(
    recovery_client: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = recovery_client
    sent_tokens: list[str] = []
    monkeypatch.setattr(
        password_reset_service,
        "send_password_reset_email",
        lambda recipient, token: sent_tokens.append(token),
    )
    client.post(
        "/api/auth/password-reset/request",
        json={"email": ACCOUNT_EMAIL},
        headers=_csrf(client),
    )
    reset = db.query(PasswordResetToken).one()
    reset.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    expired = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": sent_tokens[0], "new_password": NEW_PASSWORD},
        headers=_csrf(client),
    )
    invalid = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "x" * 43, "new_password": NEW_PASSWORD},
        headers=_csrf(client),
    )
    assert expired.status_code == invalid.status_code == 400
    user = db.query(User).filter_by(email=ACCOUNT_EMAIL).one()
    assert verify_password(CURRENT_PASSWORD, user.password_hash)


def test_reset_request_does_not_reveal_account_existence(
    recovery_client: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = recovery_client
    monkeypatch.setattr(password_reset_service, "send_password_reset_email", lambda *_: None)
    headers = _csrf(client)
    existing = client.post(
        "/api/auth/password-reset/request",
        json={"email": ACCOUNT_EMAIL},
        headers=headers,
    )
    unknown = client.post(
        "/api/auth/password-reset/request",
        json={"email": "unknown.user@example.test"},
        headers=headers,
    )
    assert existing.status_code == unknown.status_code == 200
    assert existing.json() == unknown.json()


def test_new_reset_request_invalidates_the_previous_token(
    recovery_client: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = recovery_client
    sent_tokens: list[str] = []
    monkeypatch.setattr(
        password_reset_service,
        "send_password_reset_email",
        lambda recipient, token: sent_tokens.append(token),
    )
    for _ in range(2):
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": ACCOUNT_EMAIL},
            headers=_csrf(client),
        )
        assert response.status_code == 200

    old_token = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": sent_tokens[0], "new_password": NEW_PASSWORD},
        headers=_csrf(client),
    )
    new_token = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": sent_tokens[1], "new_password": NEW_PASSWORD},
        headers=_csrf(client),
    )
    assert old_token.status_code == 400
    assert new_token.status_code == 200


def test_unconfigured_mail_provider_fails_before_account_lookup(
    recovery_client: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = recovery_client
    monkeypatch.setattr(settings, "mail_host", None)
    headers = _csrf(client)
    existing = client.post(
        "/api/auth/password-reset/request",
        json={"email": ACCOUNT_EMAIL},
        headers=headers,
    )
    unknown = client.post(
        "/api/auth/password-reset/request",
        json={"email": "unknown.user@example.test"},
        headers=headers,
    )
    assert existing.status_code == unknown.status_code == 503
    assert existing.json() == unknown.json()


def test_reset_requests_are_rate_limited(
    recovery_client: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = recovery_client
    monkeypatch.setattr(password_reset_service, "send_password_reset_email", lambda *_: None)
    for _ in range(settings.password_reset_request_limit):
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": ACCOUNT_EMAIL},
            headers=_csrf(client),
        )
        assert response.status_code == 200
    limited = client.post(
        "/api/auth/password-reset/request",
        json={"email": ACCOUNT_EMAIL},
        headers=_csrf(client),
    )
    assert limited.status_code == 429


def test_invalid_reset_verification_is_rate_limited(
    recovery_client: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = recovery_client
    monkeypatch.setattr(settings, "password_reset_verify_limit", 2)
    for _ in range(2):
        response = client.post(
            "/api/auth/password-reset/confirm",
            json={"token": "x" * 43, "new_password": NEW_PASSWORD},
            headers=_csrf(client),
        )
        assert response.status_code == 400
    limited = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "x" * 43, "new_password": NEW_PASSWORD},
        headers=_csrf(client),
    )
    assert limited.status_code == 429


def test_reset_email_uses_trusted_url_and_verified_starttls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSmtp:
        message = None
        starttls_called = False

        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            pass

        def ehlo(self) -> None:
            pass

        def starttls(self, context) -> None:
            self.starttls_called = True

        def send_message(self, message) -> None:
            self.message = message

    smtp = FakeSmtp()
    monkeypatch.setattr(email_service.smtplib, "SMTP", lambda *args, **kwargs: smtp)
    monkeypatch.setattr(settings, "app_base_url", "https://taskflow.example")
    monkeypatch.setattr(settings, "mail_host", "smtp.example.test")
    monkeypatch.setattr(settings, "mail_from", "TaskFlow <no-reply@example.test>")
    email_service.send_password_reset_email(
        "recovery.user@example.test",
        "sensitive-reset-token",
    )

    assert smtp.starttls_called
    assert "https://taskflow.example/reset-password?token=sensitive-reset-token" in smtp.message.get_content()

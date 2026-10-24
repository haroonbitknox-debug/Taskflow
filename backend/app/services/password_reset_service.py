import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import PasswordResetToken, RateLimitBucket, User
from app.services.email_service import (
    EmailConfigurationError,
    EmailDeliveryError,
    send_password_reset_email,
    validate_email_configuration,
)
from app.services.auth_service import normalize_email
from app.utils.passwords import hash_password

logger = logging.getLogger(__name__)
GENERIC_RESET_MESSAGE = (
    "If an account exists for that email, password reset instructions will be sent."
)


class ResetRequestRateLimitError(Exception):
    pass


class ResetVerificationRateLimitError(Exception):
    pass


def _rate_limit_key(identifier: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        identifier.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _increment_rate_limit(
    db: Session,
    identifier: str,
    limit: int,
    window: timedelta,
) -> bool:
    now = datetime.now(UTC)
    key_hash = _rate_limit_key(identifier)
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert = postgres_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise RuntimeError(f"Rate limiting is unsupported for database {dialect!r}.")

    statement = insert(RateLimitBucket).values(
        key_hash=key_hash,
        window_started_at=now,
        attempts=1,
    )
    reset_window = RateLimitBucket.window_started_at <= now - window
    statement = statement.on_conflict_do_update(
        index_elements=[RateLimitBucket.key_hash],
        set_={
            "window_started_at": case(
                (reset_window, now),
                else_=RateLimitBucket.window_started_at,
            ),
            "attempts": case(
                (reset_window, 1),
                else_=RateLimitBucket.attempts + 1,
            ),
        },
    ).returning(RateLimitBucket.attempts)
    db.execute(
        delete(RateLimitBucket).where(
            RateLimitBucket.window_started_at < now - timedelta(days=2)
        )
    )
    attempts = db.scalar(statement)
    db.commit()
    return attempts is not None and attempts <= limit


def request_password_reset(
    db: Session,
    email: str,
    client_ip: str,
) -> str:
    validate_email_configuration()

    normalized_email = normalize_email(email)
    request_window = timedelta(minutes=settings.password_reset_request_window_minutes)
    email_allowed = _increment_rate_limit(
        db,
        f"reset-email:{normalized_email}",
        settings.password_reset_request_limit,
        request_window,
    )
    ip_allowed = _increment_rate_limit(
        db,
        f"reset-request-ip:{client_ip}",
        settings.password_reset_request_limit * 3,
        request_window,
    )
    if not email_allowed or not ip_allowed:
        raise ResetRequestRateLimitError

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not user.is_active:
        return GENERIC_RESET_MESSAGE

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    values = {
        "user_id": user.id,
        "token_hash": token_hash,
        "expires_at": now + timedelta(minutes=settings.password_reset_token_expire_minutes),
        "created_at": now,
        "used_at": None,
    }
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert = postgres_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise RuntimeError(f"Password recovery is unsupported for database {dialect!r}.")
    statement = insert(PasswordResetToken).values(**values)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[PasswordResetToken.user_id],
            set_={
                "token_hash": values["token_hash"],
                "expires_at": values["expires_at"],
                "created_at": values["created_at"],
                "used_at": None,
            },
        )
    )
    db.commit()
    try:
        send_password_reset_email(user.email, token)
    except EmailConfigurationError:
        db.rollback()
        raise
    except EmailDeliveryError:
        db.execute(
            PasswordResetToken.__table__.update()
            .where(PasswordResetToken.token_hash == token_hash)
            .values(used_at=datetime.now(UTC))
        )
        db.commit()
        logger.error("Password reset email delivery failed; no reset token was retained.")
    return GENERIC_RESET_MESSAGE


def confirm_password_reset(
    db: Session,
    token: str,
    new_password: str,
    client_ip: str,
) -> bool:
    allowed = _increment_rate_limit(
        db,
        f"reset-verify-ip:{client_ip}",
        settings.password_reset_verify_limit,
        timedelta(minutes=settings.password_reset_verify_window_minutes),
    )
    if not allowed:
        raise ResetVerificationRateLimitError

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    reset = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .with_for_update()
    )
    if reset is None:
        return False
    user = db.get(User, reset.user_id)
    if user is None or not user.is_active:
        return False

    user.password_hash = hash_password(new_password)
    reset.used_at = now
    db.commit()
    return True

from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import certifi
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


def _normalize_database_url(value: str, setting_name: str, app_env: str) -> str:
    try:
        database_url = make_url(value)
    except (ArgumentError, ValueError) as exc:
        raise ValueError(
            f"{setting_name} must be a valid PostgreSQL connection URL."
        ) from exc
    if database_url.drivername not in {
        "postgresql",
        "postgresql+psycopg",
    }:
        raise ValueError(f"{setting_name} must use PostgreSQL with the psycopg driver.")

    host = (database_url.host or "").casefold()
    is_local_database = host in {"localhost", "127.0.0.1", "::1"}
    query = dict(database_url.query)
    sslmode = query.get("sslmode")
    local_development = app_env.casefold() == "development" and is_local_database
    if local_development and sslmode in {None, "disable"}:
        query["sslmode"] = "disable"
    else:
        if sslmode == "disable":
            raise ValueError(f"{setting_name} must use TLS outside local development.")
        query["sslmode"] = "verify-full"
        query.setdefault("sslrootcert", certifi.where())

    return database_url.set(query=query).set(
        drivername="postgresql+psycopg"
    ).render_as_string(hide_password=False)


class Settings(BaseSettings):
    app_env: str = "development"
    app_timezone: str = "UTC"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173","https://taskflow-seven-mocha.vercel.app"]
    database_url_env: str | None = Field(
        default=None,
        validation_alias="DATABASE_URL",
        repr=False,
    )
    database_url_unpooled_env: str | None = Field(
        default=None,
        validation_alias="DATABASE_URL_UNPOOLED",
        repr=False,
    )
    app_base_url: str = "http://localhost:5173"
    jwt_secret_key: str = "taskflow-development-only-insecure-signing-key"
    access_token_expire_minutes: int = 15
    auth_cookie_name: str = "taskflow_access"
    csrf_cookie_name: str = "taskflow_csrf"
    upload_storage_dir: str = "uploads/user-files"
    file_max_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    file_max_rows: int = Field(default=20000, gt=0)
    file_max_columns: int = Field(default=100, gt=0)
    file_max_worksheets: int = Field(default=20, gt=0)
    file_max_processing_seconds: int = Field(default=30, gt=0)
    file_max_extracted_text_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    openrouter_timeout_seconds: float = Field(default=30, gt=0, le=120)
    openrouter_max_tokens: int = Field(default=1200, gt=0, le=4096)
    mail_host: str | None = None
    mail_port: int = Field(default=587, gt=0, le=65535)
    mail_username: str | None = None
    mail_password: SecretStr | None = None
    mail_from: str | None = None
    mail_starttls: bool = True
    mail_use_ssl: bool = False
    password_reset_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    password_reset_request_limit: int = Field(default=3, gt=0)
    password_reset_request_window_minutes: int = Field(default=60, gt=0)
    password_reset_verify_limit: int = Field(default=30, gt=0)
    password_reset_verify_window_minutes: int = Field(default=15, gt=0)

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parents[2] / ".env",
            Path(__file__).resolve().parents[3] / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        if not self.database_url_env and self.app_env.casefold() != "development":
            raise ValueError("DATABASE_URL must be set outside development.")
        database_url_value = self.database_url_env or (
            "postgresql+psycopg://127.0.0.1:5432/taskflow?sslmode=disable"
        )
        self.database_url_env = _normalize_database_url(
            database_url_value, "DATABASE_URL", self.app_env
        )
        if self.database_url_unpooled_env:
            self.database_url_unpooled_env = _normalize_database_url(
                self.database_url_unpooled_env,
                "DATABASE_URL_UNPOOLED",
                self.app_env,
            )

        base_url = self.app_base_url.rstrip("/")
        parsed_base_url = urlsplit(base_url)
        if (
            parsed_base_url.scheme not in {"http", "https"}
            or not parsed_base_url.hostname
            or parsed_base_url.username
            or parsed_base_url.password
            or parsed_base_url.query
            or parsed_base_url.fragment
        ):
            raise ValueError("APP_BASE_URL must be an HTTP or HTTPS URL.")
        if self.app_env.casefold() != "development" and parsed_base_url.scheme != "https":
            raise ValueError("APP_BASE_URL must use HTTPS outside development.")
        self.app_base_url = base_url

        try:
            ZoneInfo(self.app_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("APP_TIMEZONE must be a valid IANA timezone.") from exc
        if self.access_token_expire_minutes < 1:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 1.")
        if self.app_env.casefold() == "development":
            if not self.jwt_secret_key:
                self.jwt_secret_key = "taskflow-development-only-insecure-signing-key"
            return self

        if len(self.jwt_secret_key) < 32 or len(set(self.jwt_secret_key)) < 16:
            raise ValueError(
                "JWT_SECRET_KEY must be a strong secret of at least 32 characters "
                "outside development."
            )
        if any(
            marker in self.jwt_secret_key.casefold()
            for marker in ("change-me", "replace", "example", "development", "secret")
        ):
            raise ValueError(
                "JWT_SECRET_KEY must not contain a placeholder or development secret."
            )
        return self

    @property
    def database_url(self) -> URL:
        if self.database_url_env is None:
            raise RuntimeError("DATABASE_URL is not configured.")
        return make_url(self.database_url_env)

    @property
    def database_url_string(self) -> str:
        return self.database_url.render_as_string(hide_password=False)

    @property
    def migration_database_url(self) -> URL:
        value = self.database_url_unpooled_env or self.database_url_env
        if value is None:
            raise RuntimeError("DATABASE_URL is not configured.")
        return make_url(value)

    @property
    def mail_is_configured(self) -> bool:
        return bool(self.mail_host and self.mail_from)

    @property
    def secure_cookies(self) -> bool:
        return self.app_env.casefold() != "development"


settings = Settings()

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_env: str = "development"
    app_timezone: str = "UTC"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173"]
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "taskflow_db"
    db_user: str = "root"
    db_password: str = ""
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

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
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
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @property
    def database_url_string(self) -> str:
        return self.database_url.render_as_string(hide_password=False)

    @property
    def secure_cookies(self) -> bool:
        return self.app_env.casefold() != "development"


settings = Settings()

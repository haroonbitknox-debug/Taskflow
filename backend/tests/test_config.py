import certifi
import pytest

from app.core.config import Settings


def test_neon_database_url_uses_full_certificate_verification() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_secret_key="StrongUniqueProductionSigningKey-7a9B-2026-TaskFlow",
        database_url_env="postgresql://user:private-password@ep-neon.example/db?sslmode=require",
        app_base_url="https://taskflow.example",
    )

    assert settings.database_url.drivername == "postgresql+psycopg"
    assert settings.database_url.query["sslmode"] == "verify-full"
    assert settings.database_url.query["sslrootcert"] == certifi.where()
    assert "private-password" not in repr(settings)


def test_unpooled_neon_url_is_available_for_migrations() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_secret_key="StrongUniqueProductionSigningKey-7a9B-2026-TaskFlow",
        database_url_env=(
            "postgresql://username:runtime-password@ep-pooler.example/db"
            "?sslmode=require"
        ),
        database_url_unpooled_env=(
            "postgresql://username:migration-password@ep-direct.example/db"
            "?sslmode=require"
        ),
        app_base_url="https://taskflow.example",
    )

    assert settings.database_url.host == "ep-pooler.example"
    assert settings.database_url.query["sslmode"] == "verify-full"
    assert settings.database_url.query["sslrootcert"] == certifi.where()
    assert settings.migration_database_url.host == "ep-direct.example"
    assert settings.migration_database_url.query["sslmode"] == "verify-full"
    assert "runtime-password" not in repr(settings)
    assert "migration-password" not in repr(settings)


def test_production_rejects_local_tls_disable() -> None:
    with pytest.raises(ValueError, match="must use TLS"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="StrongUniqueProductionSigningKey-7a9B-2026-TaskFlow",
            database_url_env="postgresql://user:password@database.example/db?sslmode=disable",
            app_base_url="https://taskflow.example",
        )


def test_production_requires_database_url() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL must be set"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="StrongUniqueProductionSigningKey-7a9B-2026-TaskFlow",
            app_base_url="https://taskflow.example",
        )

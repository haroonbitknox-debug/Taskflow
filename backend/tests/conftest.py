import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User  # noqa: F401

TEST_DATABASE_URL = os.getenv("TASKFLOW_TEST_DATABASE_URL")


def _same_database(first, second) -> bool:
    return (
        first.host,
        first.port,
        first.database,
        first.username,
    ) == (
        second.host,
        second.port,
        second.database,
        second.username,
    )


def _test_engine():
    if os.getenv("TASKFLOW_RUN_AUTH_TESTS") != "1":
        pytest.skip(
            "Set TASKFLOW_RUN_AUTH_TESTS=1 to explicitly enable PostgreSQL integration tests."
        )
    if not TEST_DATABASE_URL:
        pytest.skip("Set TASKFLOW_TEST_DATABASE_URL to a dedicated PostgreSQL test database.")
    test_url = make_url(TEST_DATABASE_URL)
    if test_url.drivername not in {"postgresql", "postgresql+psycopg"}:
        pytest.fail("The auth test database must use PostgreSQL.")
    normalized_test_url = test_url.set(drivername="postgresql+psycopg")
    if _same_database(normalized_test_url, settings.database_url):
        pytest.fail("The auth test database must not be the application database.")
    return create_engine(
        normalized_test_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None, "connect_timeout": 10},
    )


@pytest.fixture(scope="session")
def test_engine():
    engine = _test_engine()
    try:
        with engine.connect():
            pass
        Base.metadata.create_all(bind=engine)
    except Exception:
        engine.dispose()
        raise
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    if _same_database(
        make_url(TEST_DATABASE_URL).set(drivername="postgresql+psycopg"),
        settings.database_url,
    ):
        pytest.fail("Refusing to alter the development database.")
    connection = test_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        class_=Session,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    with factory() as session:
        yield session
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.get("/api/auth/csrf")
        yield test_client
    app.dependency_overrides.clear()

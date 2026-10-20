import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User  # noqa: F401

TEST_DB_NAME = os.getenv("TASKFLOW_TEST_DB_NAME")


def _test_engine():
    if os.getenv("TASKFLOW_RUN_AUTH_TESTS") != "1":
        pytest.skip(
            "Set TASKFLOW_RUN_AUTH_TESTS=1 to explicitly enable MySQL auth tests."
        )
    if not TEST_DB_NAME:
        pytest.skip("Set TASKFLOW_TEST_DB_NAME to a dedicated test database.")
    if TEST_DB_NAME == settings.db_name:
        pytest.fail("The auth test database must not be the development database.")
    url = URL.create(
        "mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=TEST_DB_NAME,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True)


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
    if TEST_DB_NAME == settings.db_name:
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

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
)


@event.listens_for(engine, "connect")
def set_mysql_session_timezone(
    dbapi_connection: Any, connection_record: Any
) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET time_zone = '+00:00'")
    finally:
        cursor.close()


def create_session_factory(bind=engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=bind,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


SessionLocal = create_session_factory()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

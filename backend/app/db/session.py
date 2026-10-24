from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 10, "prepare_threshold": None},
)


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

"""Database engine and session.

Nothing here is SQLite-specific beyond the connect_args guard, so moving to
Postgres (Neon) is a DATABASE_URL change and nothing else.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Good enough for the pilot. Introduce Alembic before the schema stabilises."""
    from . import models  # noqa: F401  (registers the mappers)

    Base.metadata.create_all(engine)

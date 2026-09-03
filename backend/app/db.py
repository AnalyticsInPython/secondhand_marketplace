"""Database engine and session.

Nothing here is SQLite-specific beyond the connect_args guard, so moving to
Postgres is a DATABASE_URL change and nothing else.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

if _is_sqlite:
    # SQLite ignores ON DELETE CASCADE unless asked. Postgres enforces it by default.
    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record) -> None:  # pragma: no cover
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


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


def reset_all() -> None:
    """Drop and recreate every table. Used by the seed's --reset and by tests."""
    from . import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

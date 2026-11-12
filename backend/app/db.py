from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

engine = None
SessionLocal: sessionmaker | None = None


class Base(DeclarativeBase):
    pass


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def init_engine(database_url: str, **kwargs):
    global engine, SessionLocal
    connect_args = dict(kwargs.pop("connect_args", {}))
    if _is_sqlite(database_url):
        connect_args.setdefault("check_same_thread", False)
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args, **kwargs)
    if _is_sqlite(database_url):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SessionLocal = sessionmaker(bind=engine, autoflush=True, autocommit=False, expire_on_commit=False)
    return engine


def init_db():
    assert engine is not None
    if not _is_sqlite(str(engine.url)):
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            except Exception:
                pass
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_all():
    assert engine is not None
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

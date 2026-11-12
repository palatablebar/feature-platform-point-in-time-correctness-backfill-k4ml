"""Engine / session factory shared by the API and the Celery worker."""
import time

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config.settings import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=8,
    max_overflow=4,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# create_all 只建缺失的表；这里为已存在的库补列（幂等，可重复执行）。
_PATCH_COLUMNS = (
    ("sample_row", "sources", "ALTER TABLE sample_row ADD COLUMN sources JSON NOT NULL DEFAULT '[]'::json"),
)


def _apply_column_patches() -> None:
    with engine.begin() as conn:
        existing_tables = set(inspect(conn).get_table_names())
        for table, column, ddl in _PATCH_COLUMNS:
            if table not in existing_tables:
                continue
            columns = {col["name"] for col in inspect(conn).get_columns(table)}
            if column not in columns:
                conn.execute(text(ddl))


def init_db(max_attempts: int = 30, delay: float = 2.0) -> None:
    """Create all tables, waiting for PostgreSQL to accept connections."""
    import src.models  # noqa: F401  (register mappers)

    last_error = None
    for _ in range(max_attempts):
        try:
            Base.metadata.create_all(bind=engine)
            _apply_column_patches()
            return
        except Exception as exc:  # pragma: no cover - infra retry
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"database bootstrap failed: {last_error}")

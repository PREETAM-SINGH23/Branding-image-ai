from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = (
    {"check_same_thread": False, "timeout": 60} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA journal_mode=DELETE")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_sqlite_dir_writable() -> None:
    """Fail fast with a clear message if SQLite cannot create journal files (common 'readonly' error)."""
    if not settings.database_url.startswith("sqlite"):
        return
    url = make_url(settings.database_url)
    if not url.database or url.database == ":memory:":
        return
    from pathlib import Path

    db_path = Path(url.database)
    parent = db_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    probe = parent / ".write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        raise RuntimeError(
            f"SQLite directory is not writable: {parent} ({e}). "
            "Fix permissions (e.g. chmod -R u+w backend/data) or set DATABASE_URL to a writable path."
        ) from e


class Base(DeclarativeBase):
    pass


def migrate_sqlite_schema() -> None:
    """Add columns missing from older SQLite files (create_all does not ALTER)."""
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "creative_jobs" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("creative_jobs")}
    stmts: list[str] = []
    if "promo_word" not in cols:
        stmts.append("ALTER TABLE creative_jobs ADD COLUMN promo_word VARCHAR(32)")
    if "price_display" not in cols:
        stmts.append("ALTER TABLE creative_jobs ADD COLUMN price_display VARCHAR(48)")
    if "accent_hex" not in cols:
        stmts.append("ALTER TABLE creative_jobs ADD COLUMN accent_hex VARCHAR(16)")
    if "creative_template" not in cols:
        stmts.append("ALTER TABLE creative_jobs ADD COLUMN creative_template VARCHAR(24) NOT NULL DEFAULT 'promo_split'")
    if "logo_file_ids_json" not in cols:
        stmts.append("ALTER TABLE creative_jobs ADD COLUMN logo_file_ids_json TEXT")
    if "ai_generate_background" not in cols:
        stmts.append(
            "ALTER TABLE creative_jobs ADD COLUMN ai_generate_background BOOLEAN NOT NULL DEFAULT 0"
        )
    if "warning_message" not in cols:
        stmts.append("ALTER TABLE creative_jobs ADD COLUMN warning_message TEXT")
    if not stmts:
        return
    with engine.begin() as conn:
        for sql in stmts:
            conn.execute(text(sql))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

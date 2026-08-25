import os
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.core.config import settings
from backend.database.migrations import apply_cr004_migration

Base = declarative_base()


def _ensure_sqlite_parent_dir(db_url: str) -> None:
    if not db_url.startswith("sqlite:///"):
        return

    parsed = urlparse(db_url)
    if parsed.netloc or parsed.path in ("", "/:memory:"):
        return

    raw_path = unquote(parsed.path)
    if len(raw_path) >= 4 and raw_path[0] == "/" and raw_path[2] == ":":
        raw_path = raw_path[1:]
    db_path = Path(raw_path)
    if db_path.name:
        db_path.parent.mkdir(parents=True, exist_ok=True)


def get_sqlite_engine(db_url: str = None):
    url = db_url or settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    _ensure_sqlite_parent_dir(url)
    
    engine = create_engine(url, connect_args=connect_args, echo=False)
    
    if "sqlite" in url:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()
            
    return engine

engine = get_sqlite_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(schema_sql_path: str = "docs/contracts/db/schema.sql", target_engine=None):
    """
    Initializes the database schema using DDL from schema.sql.
    """
    target_eng = target_engine or engine
    
    if os.path.exists(schema_sql_path):
        with open(schema_sql_path, "r", encoding="utf-8") as f:
            sql_script = f.read()
            
        raw_conn = target_eng.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF;")
            try:
                cursor.executescript(sql_script)
            except sqlite3.OperationalError as exc:
                if "label_key" not in str(exc) and "storage_path" not in str(exc):
                    raise
                raw_conn.rollback()
                cursor.execute("PRAGMA foreign_keys=ON;")
                apply_cr004_migration(raw_conn)
                cursor.execute("PRAGMA foreign_keys=OFF;")
                cursor.executescript(sql_script)
            cursor.execute("PRAGMA foreign_keys=ON;")
            raw_conn.commit()
            apply_cr004_migration(raw_conn)
        finally:
            raw_conn.close()

    else:
        # Fallback to SQLAlchemy create_all if schema.sql path is not found directly
        Base.metadata.create_all(bind=target_eng)

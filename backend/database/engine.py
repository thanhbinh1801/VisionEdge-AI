import os
import sqlite3
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.core.config import settings

Base = declarative_base()

def get_sqlite_engine(db_url: str = None):
    url = db_url or settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    
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
            cursor.executescript(sql_script)
            cursor.execute("PRAGMA foreign_keys=ON;")
            raw_conn.commit()
        finally:
            raw_conn.close()

    else:
        # Fallback to SQLAlchemy create_all if schema.sql path is not found directly
        Base.metadata.create_all(bind=target_eng)

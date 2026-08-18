import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("SENTRIAI_DB_PATH", str(Path(__file__).parent / "sentriai.db"))

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    schema_file = Path(__file__).parent / "schema.sql"
    seed_file = Path(__file__).parent / "seed_events.sql"
    
    if schema_file.exists():
        with open(schema_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
            
    if seed_file.exists():
        with open(seed_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

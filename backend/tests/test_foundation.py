import os
import json
import pytest
from backend.db.connection import get_db_connection, init_db

def test_foundation_contracts_and_db():
    # Verify contract files exist
    assert os.path.exists("docs/contracts/api-schema.json")
    assert os.path.exists("docs/contracts/websocket-events.json")
    assert os.path.exists("docs/contracts/db-schema.sql")
    assert os.path.exists("docs/contracts/ui-design-contract.md")
    assert os.path.exists(".delivery/ADR-005-Custom-Label-Matching-Architecture.md")
    
    # Verify JSON schemas
    with open("docs/contracts/api-schema.json", "r", encoding="utf-8") as f:
        api_spec = json.load(f)
        assert "PATCH /api/events/{id}/correct-plate" in api_spec["endpoints"]
        
    # Verify DB initialization
    init_db()
    conn = get_db_connection()
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    assert "events" in tables
    assert "vehicles" in tables
    assert "zones" in tables
    assert "cameras" in tables
    assert "custom_labels" in tables
    conn.close()

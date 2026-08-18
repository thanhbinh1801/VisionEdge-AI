import pytest
import os
import tempfile
from backend.db.connection import init_db, get_db_connection
from backend.db.crud import get_all_events, correct_event_plate, get_vehicle
from backend.db.models import EventModel

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_file = tmp.name
    monkeypatch.setenv("SENTRIAI_DB_PATH", db_file)
    init_db()
    yield db_file
    if os.path.exists(db_file):
        os.remove(db_file)

def test_seed_events_and_crud():
    events = get_all_events()
    assert len(events) >= 3
    
    # Test plate correction
    evt_id = events[0]["id"]
    success = correct_event_plate(evt_id, "29A-88888")
    assert success is True
    
    updated_events = get_all_events()
    corrected_evt = next(e for e in updated_events if e["id"] == evt_id)
    assert corrected_evt["corrected_plate"] == "29A-88888"
    assert corrected_evt["is_corrected"] == 1

def test_get_vehicle():
    veh = get_vehicle("29A-12345")
    assert veh is not None
    assert veh["list_type"] == "whitelist"

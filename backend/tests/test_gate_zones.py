import os
import pytest
from backend.database.engine import get_sqlite_engine, init_db, SessionLocal
from backend.database.models import Zone
from backend.database.repository import ZoneRepository

TEST_DB_URL = "sqlite:///./test_gate_zones.db"

@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path="docs/contracts/db/schema.sql", target_engine=engine)
    yield engine
    engine.dispose()
    if os.path.exists("test_gate_zones.db"):
        try:
            os.remove("test_gate_zones.db")
        except PermissionError:
            pass

@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

def test_gate_zones_seeded(db_session):
    repo = ZoneRepository(db_session)
    gate_zones = repo.get_by_camera("GATE-01")
    assert len(gate_zones) >= 2
    zone_names = [z.name for z in gate_zones]
    assert "Làn IN 1" in zone_names
    assert "Làn IN 2" in zone_names

def test_gate_zone_create_and_update(db_session):
    repo = ZoneRepository(db_session)
    new_zone = Zone(
        id="zone-gate-test-01",
        camera_id="GATE-01",
        name="Làn IN 3 Mới",
        vertices=[{"x": 10, "y": 10}, {"x": 30, "y": 10}, {"x": 30, "y": 50}, {"x": 10, "y": 50}],
        allowed_classes=["container"],
        forbidden_classes=["car", "motorbike"],
        color="#30d158"
    )
    created = repo.create(new_zone)
    assert created.id == "zone-gate-test-01"
    assert created.camera_id == "GATE-01"

    updated = repo.update_zone(
        zone_id="zone-gate-test-01",
        name="Làn IN VIP",
        color="#ff9f0a"
    )
    assert updated is not None
    assert updated.name == "Làn IN VIP"
    assert updated.color == "#ff9f0a"

def test_gate_zone_delete(db_session):
    repo = ZoneRepository(db_session)
    success = repo.delete("zA")
    assert success is True
    assert repo.get_by_id("zA") is None

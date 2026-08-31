import os
import pytest
from backend.database.engine import get_sqlite_engine, init_db, SessionLocal
from backend.tests.conftest import SCHEMA_SQL_PATH
from backend.database.models import Zone
from backend.database.repository import ZoneRepository

TEST_DB_URL = "sqlite:///./test_gate_zones.db"

@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path=str(SCHEMA_SQL_PATH), target_engine=engine)
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
    """Camera cổng có đúng một làn vào, cộng một zone đánh dấu khu bốt.

    Bộ cũ seed 'Làn IN 1' và 'Làn IN 2' theo camera toàn cảnh hai làn. Camera biển số
    hiện dùng (`Cvao-Bien-L2`) chỉ ngắm một làn, nên zone làn thứ hai sẽ luôn rỗng —
    xem ghi chú ở docs/contracts/db/schema.sql.
    """
    repo = ZoneRepository(db_session)
    gate_zones = repo.get_by_camera("GATE-01")
    assert len(gate_zones) >= 2
    zone_names = [z.name for z in gate_zones]
    assert "Làn IN" in zone_names
    assert "Bốt kiểm soát" in zone_names


def test_only_one_gate_zone_feeds_the_lpr_pipeline(db_session):
    """Đúng một zone của cổng được `_is_inbound_lane()` nhận là làn vào.

    Zone khu bốt phải nằm ngoài luồng LPR: chỗ đó có bình cứu hoả và vật màu vàng trên
    cột, đủ giống một tấm biển để tốn công OCR mỗi frame.
    """
    from backend.app.api.v1.events import _is_inbound_lane

    gate_zones = ZoneRepository(db_session).get_by_camera("GATE-01")
    inbound = [z.name for z in gate_zones if _is_inbound_lane(z.name)]
    assert inbound == ["Làn IN"]

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

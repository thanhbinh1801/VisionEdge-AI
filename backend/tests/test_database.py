import os
import pytest
from datetime import datetime
from backend.database.engine import get_sqlite_engine, init_db, SessionLocal
from backend.database.models import Base, Camera, Zone, Vehicle, Event, CustomLabel, KpiRealtimeCache
from backend.database.repository import (
    CameraRepository,
    ZoneRepository,
    VehicleRepository,
    EventRepository,
    CustomLabelRepository,
    KpiRepository,
)

TEST_DB_URL = "sqlite:///./test_sentri_ai.db"

@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path="docs/contracts/db/schema.sql", target_engine=engine)
    yield engine
    # Cleanup after tests
    engine.dispose()
    if os.path.exists("test_sentri_ai.db"):
        try:
            os.remove("test_sentri_ai.db")
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

def test_camera_repository(db_session):
    repo = CameraRepository(db_session)
    cam = Camera(
        id="TEST-CAM-01",
        name="Test Camera 1",
        location="Cổng Cát",
        stream_url="/videos/test.mp4",
        status="online",
        fps=15.0,
    )
    saved = repo.create(cam)
    assert saved.id == "TEST-CAM-01"

    fetched = repo.get_by_id("TEST-CAM-01")
    assert fetched is not None
    assert fetched.name == "Test Camera 1"

def test_zone_repository(db_session):
    cam_repo = CameraRepository(db_session)
    cam_repo.create(Camera(id="CAM-Z1", name="Zone Cam", location="Loc", stream_url="url"))

    zone_repo = ZoneRepository(db_session)
    zone = Zone(
        id="zone-test-1",
        camera_id="CAM-Z1",
        name="Vùng Cấm Test",
        vertices=[[0.1, 0.1], [0.9, 0.1], [0.8, 0.8], [0.2, 0.8]],
        allowed_classes=["person"],
        forbidden_classes=["forklift"],
        is_active=True,
    )
    saved = zone_repo.create(zone)
    assert saved.id == "zone-test-1"

    zones = zone_repo.get_by_camera("CAM-Z1")
    assert len(zones) >= 1

def test_vehicle_repository(db_session):
    repo = VehicleRepository(db_session)
    v1 = Vehicle(
        id="v-test-1",
        license_plate="29A-999.99",
        vehicle_type="Truck",
        tag_label="blacklisted",
        notes="Xe nghi vấn",
    )
    saved = repo.upsert(v1)
    assert saved.license_plate == "29A-999.99"
    assert saved.total_entries == 1

    # Upsert again -> increment total_entries
    saved_again = repo.upsert(v1)
    assert saved_again.total_entries == 2

    blacklisted = repo.list_all(tag_label="blacklisted")
    assert len(blacklisted) >= 1

def test_event_repository(db_session):
    cam_repo = CameraRepository(db_session)
    cam_repo.create(Camera(id="CAM-EV1", name="Ev Cam", location="Loc", stream_url="url"))

    event_repo = EventRepository(db_session)
    evt = Event(
        id="evt-test-100",
        timestamp=datetime.utcnow(),
        camera_id="CAM-EV1",
        event_type="ZONE_VIOLATION",
        severity_level=3,
        license_plate="30B-123.45",
        object_class="person",
        confidence=0.98,
        bbox=[100, 150, 300, 400],
    )
    saved = event_repo.create(evt)
    assert saved.id == "evt-test-100"

    recent = event_repo.get_recent_events(severity_level=3)
    assert len(recent) >= 1
    assert recent[0].severity_level == 3

def test_custom_label_repository(db_session):
    repo = CustomLabelRepository(db_session)
    lbl = repo.create_or_increment("xe_nang_ui", category="machinery")
    assert lbl.sample_count == 1

    lbl2 = repo.create_or_increment("xe_nang_ui", category="machinery")
    assert lbl2.sample_count == 2

def test_kpi_repository(db_session):
    repo = KpiRepository(db_session)
    kpi = repo.update_kpi(gate_vehicles_total=150, area_zone_violations=5)
    assert kpi.gate_vehicles_total == 150
    assert kpi.area_zone_violations == 5

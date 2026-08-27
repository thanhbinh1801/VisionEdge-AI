import os
import pytest
from datetime import datetime
from backend.database.engine import get_sqlite_engine, init_db, SessionLocal
from backend.tests.conftest import SCHEMA_SQL_PATH
from backend.database.models import Camera, Zone, Vehicle, Event, DatasetSource
from backend.database.repository import (
    CameraRepository,
    ZoneRepository,
    VehicleRepository,
    EventRepository,
    CustomLabelRepository,
    DatasetRepository,
    KpiRepository,
)

TEST_DB_URL = "sqlite:///./test_sentri_ai.db"

@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path=str(SCHEMA_SQL_PATH), target_engine=engine)
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
        vertices=[{"x": 10.0, "y": 10.0}, {"x": 90.0, "y": 10.0}, {"x": 80.0, "y": 80.0}],
        allowed_classes=["person", "car"],
        forbidden_classes=["forklift", "truck", "container"],
        is_active=True,
    )
    saved = zone_repo.create(zone)
    assert saved.id == "zone-test-1"

    # Test update polygon zone vertices (4-thao tác SVG polygon editing)
    updated = zone_repo.update_zone(
        zone_id="zone-test-1",
        name="Vùng Cấm Xe Nâng Updated",
        vertices=[{"x": 12.0, "y": 12.0}, {"x": 95.0, "y": 10.0}, {"x": 85.0, "y": 85.0}, {"x": 15.0, "y": 80.0}],
        forbidden_classes=["forklift", "truck", "container", "crane"]
    )
    assert updated is not None
    assert updated.name == "Vùng Cấm Xe Nâng Updated"
    assert len(updated.vertices) == 4
    assert "crane" in updated.forbidden_classes

def test_vehicle_repository_known_unknown(db_session):
    repo = VehicleRepository(db_session)
    v1 = Vehicle(
        id="v-test-1",
        license_plate="29A-999.99",
        vehicle_type="truck",
        tag_label="unknown",
        notes="Xe mới xuất hiện",
    )
    saved = repo.upsert(v1)
    assert saved.license_plate == "29A-999.99"
    assert saved.tag_label == "unknown"

    # 1-click update tag label to Xe quen ('known')
    updated = repo.update_tag("29A-999.99", tag_label="known", notes="Đã xác minh xe công ty")
    assert updated is not None
    assert updated.tag_label == "known"

    stats = repo.get_stats()
    assert stats["known"] >= 1

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

def test_dataset_bbox_samples_and_zone_sync(db_session):
    # Setup camera and zone
    cam_repo = CameraRepository(db_session)
    cam_repo.create(Camera(id="CAM-DS1", name="Dataset Cam", location="Loc", stream_url="url"))
    
    zone_repo = ZoneRepository(db_session)
    zone_repo.create(Zone(
        id="zone-ds-1",
        camera_id="CAM-DS1",
        name="Zone Dataset Sync",
        vertices=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
        allowed_classes=["car"],
        forbidden_classes=["truck"],
        is_active=True,
    ))

    dataset_repo = DatasetRepository(db_session)
    # Create dataset source
    src = dataset_repo.create_source(DatasetSource(
        id="src-video-01",
        name="Demo Frame Clip 01",
        kind="video",
        url="/videos/BAI-KIEM.mp4",
        duration_seconds=120.0,
        total_frames=1200
    ))
    assert src.id == "src-video-01"

    label = CustomLabelRepository(db_session).create_custom(
        label_name="container_20ft_custom",
        category="vehicle_shape",
    )

    # Batch save BBox annotation samples
    samples_payload = [
        {
            "id": "bbox-sample-01",
            "label_id": label.id,
            "source_id": "src-video-01",
            "frame_index": 45,
            "x": 20.5,
            "y": 30.0,
            "w": 40.0,
            "h": 50.0,
            "category": "vehicle_shape",
            "label_name": "container_20ft_custom"
        }
    ]
    saved_samples = dataset_repo.save_samples_batch(samples_payload)
    assert len(saved_samples) == 1
    assert saved_samples[0].label_name == "container_20ft_custom"

    # Sync custom labels to zones
    sync_res = dataset_repo.sync_custom_labels_to_zones()
    assert "container_20ft_custom" in [label.label_name for label in CustomLabelRepository(db_session).get_all(include_deleted=True)]
    assert label.label_key in sync_res["synced_labels"]
    assert len(sync_res["affected_zones"]) >= 1

def test_kpi_repository(db_session):
    repo = KpiRepository(db_session)
    kpi = repo.update_kpi(gate_vehicles_total=150, area_zone_violations=5)
    assert kpi.gate_vehicles_total == 150
    assert kpi.area_zone_violations == 5

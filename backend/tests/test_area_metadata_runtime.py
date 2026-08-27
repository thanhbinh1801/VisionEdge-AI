from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.services.area_metadata import build_area_metadata_event
from backend.app.services.video_stream import ProcessedFrameSnapshot
from backend.app.services.zone_cache import ZoneCacheState, zone_cache_service
from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.tests.conftest import SCHEMA_SQL_PATH
from backend.database.models import Camera, Zone

TEST_DB_URL = "sqlite:///./test_area_metadata_runtime.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path=str(SCHEMA_SQL_PATH), target_engine=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def test_build_area_metadata_event_uses_normalized_payload():
    snapshot = ProcessedFrameSnapshot(
        frame_id=7,
        captured_at="2026-08-20T12:00:00+00:00",
        frame="frame",
        detections=(
            {
                "id": "det-01",
                "object_class": "forklift",
                "vietnamese_name": "Xe nâng",
                "confidence": 0.95,
                "bbox": [10.0, 20.0, 30.0, 40.0],
                "zone_violation": True,
                "zone_name": "Khu xe nâng",
                "zone_id": "zone-1",
            },
        ),
        pipeline_latency_ms=42.5,
    )
    zone_state = ZoneCacheState(
        camera_id="BAI-KIEM",
        zone_version=3,
        cache_status="hot",
        refreshed_at=datetime.now(timezone.utc).isoformat(),
        zones=({"id": "zone-1"},),
    )

    event = build_area_metadata_event(
        camera_id="BAI-KIEM",
        snapshot=snapshot,
        zone_state=zone_state,
        confidence_threshold=0.35,
    )

    assert event["event_type"] == "AREA_FRAME_METADATA"
    assert event["payload"]["zone_version"] == 3
    assert event["payload"]["kpi_delta"]["area_zone_violations"] == 1
    assert event["payload"]["objects"][0]["bbox"] == [0.1, 0.2, 0.4, 0.6]


def test_zone_cache_refresh_increments_version(db_session):
    db_session.add(Camera(id="CACHE-CAM", name="Cache Cam", location="Loc", stream_url="url"))
    db_session.add(
        Zone(
            id="cache-zone-1",
            camera_id="CACHE-CAM",
            name="Zone 1",
            vertices=[{"x": 0, "y": 0}, {"x": 50, "y": 0}, {"x": 50, "y": 50}],
            allowed_classes=["person"],
            forbidden_classes=["forklift"],
            is_active=True,
        )
    )
    db_session.commit()

    first = zone_cache_service.refresh_camera(db_session, "CACHE-CAM")
    second = zone_cache_service.refresh_camera(db_session, "CACHE-CAM")

    assert first.zone_version == 1
    assert second.zone_version == 2
    assert second.zones[0]["name"] == "Zone 1"


def test_metadata_lane_is_separate_from_event_persistence():
    snapshot = ProcessedFrameSnapshot(
        frame_id=11,
        captured_at="2026-08-20T12:00:00+00:00",
        frame="frame",
        detections=(
            {
                "id": "det-1",
                "object_class": "forklift",
                "vietnamese_name": "Xe nâng",
                "confidence": 0.9,
                "bbox": [10.0, 20.0, 30.0, 40.0],
                "zone_violation": True,
                "zone_name": "Yard A",
                "zone_id": "zone-a",
            },
        ),
        pipeline_latency_ms=9.0,
    )
    zone_state = ZoneCacheState(
        camera_id="BAI-KIEM",
        zone_version=4,
        cache_status="hot",
        refreshed_at="2026-08-20T12:00:00+00:00",
        zones=(
            {
                "id": "zone-a",
                "name": "Yard A",
                "vertices": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
                "allowed_classes": [],
                "forbidden_classes": ["forklift"],
                "is_active": True,
                "color": "#EF4444",
                "version": 4,
            },
        ),
    )

    event = build_area_metadata_event(
        camera_id="BAI-KIEM",
        snapshot=snapshot,
        zone_state=zone_state,
        confidence_threshold=0.35,
    )

    assert event["payload"]["objects"][0]["zone_hits"][0]["rule_result"] == "prohibited"
    assert "event_id" not in event["payload"]
    assert event["payload"]["kpi_delta"]["area_active_objects"] == 1

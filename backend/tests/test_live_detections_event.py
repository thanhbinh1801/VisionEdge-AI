from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import events
from backend.main import app
from backend.app.services.event_manager import EventManager
from backend.app.services.video_stream import (
    CameraFramePipeline,
    LatestFrameProvider,
    VideoStreamService,
    get_latest_frame_provider,
)
from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.database.models import Camera, Zone
from backend.database.models import Event as EventModel


def _write_fixture_video(path: Path, *, fps: int = 10, seconds: int = 12) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (64, 48),
    )
    assert writer.isOpened()
    try:
        for index in range(fps * seconds):
            frame = np.full((48, 64, 3), index % 255, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def _assert_playable_mp4(path: Path, *, expected_seconds: float) -> None:
    capture = cv2.VideoCapture(str(path))
    try:
        assert capture.isOpened()
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        ok, first_frame = capture.read()
        assert ok
        assert first_frame is not None
        assert fps > 0
        assert frames > 0
        assert (frames / fps) == pytest.approx(expected_seconds, abs=0.35)
    finally:
        capture.release()


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "events.db"
    engine = get_sqlite_engine(f"sqlite:///{db_path}")
    init_db(schema_sql_path="docs/contracts/db/schema.sql", target_engine=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_event_model_instantiation_with_zone_id_succeeds():
    """
    Verifies EventModel instantiation with zone_id succeeds and valid schema fields work cleanly.
    """
    evt = EventModel(
        id="evt-live-test-01",
        timestamp=datetime.now(timezone.utc),
        camera_id="BAI-KIEM",
        zone_id="zone-001",
        event_type="ZONE_VIOLATION",
        severity_level=3,
        object_class="người",
        confidence=0.95,
        crop_image_url="/media/crops/crop_live.jpg",
        video_clip_url="/videos/BAI_KIEM.mp4",
    )
    assert evt.id == "evt-live-test-01"
    assert evt.zone_id == "zone-001"
    assert evt.event_type == "ZONE_VIOLATION"


def test_persist_violation_event_writes_10s_clip_for_chatbot(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="CHATBOT-CAM", name="Chatbot Cam", location="Loc", stream_url="url"))
    db_session.commit()

    clips_dir = tmp_path / "clips"
    source_video = tmp_path / "source.mp4"
    _write_fixture_video(source_video, seconds=12)
    monkeypatch.setattr(events, "event_manager", EventManager(cooldown_seconds=15, clips_dir=str(clips_dir)))
    violation_time = datetime(2026, 8, 21, 3, 0, 0, tzinfo=timezone.utc)
    clip_name = f"clip_CHATBOT-CAM_{int(violation_time.timestamp())}.mp4"

    event = events._persist_violation_event(
        db_session,
        camera_id="CHATBOT-CAM",
        detection={
            "object_class": "person",
            "vietnamese_name": "Người",
            "confidence": 0.91,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "zone_id": None,
        },
        timestamp=violation_time,
        source_video_path=str(source_video),
        source_timestamp_seconds=6.0,
    )

    assert event is not None
    assert event.event_type == "ZONE_VIOLATION"
    assert event.severity_level == 3
    assert event.video_clip_url == f"/media/clips/{clip_name}"
    assert event.bbox == [10.0, 20.0, 30.0, 40.0]
    assert (clips_dir / clip_name).exists()
    _assert_playable_mp4(clips_dir / clip_name, expected_seconds=10.0)

    duplicate = events._persist_violation_event(
        db_session,
        camera_id="CHATBOT-CAM",
        detection={
            "object_class": "person",
            "vietnamese_name": "Người",
            "confidence": 0.91,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "zone_id": None,
        },
        timestamp=datetime(2026, 8, 21, 3, 0, 5, tzinfo=timezone.utc),
        source_video_path=str(source_video),
        source_timestamp_seconds=6.5,
    )

    assert duplicate is None


def test_area_metadata_violation_persistence_writes_chatbot_clip(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="WS-CAM", name="WebSocket Cam", location="Loc", stream_url="url"))
    db_session.commit()

    clips_dir = tmp_path / "metadata-clips"
    source_video = tmp_path / "metadata-source.mp4"
    _write_fixture_video(source_video, seconds=12)
    monkeypatch.setattr(events, "event_manager", EventManager(cooldown_seconds=15, clips_dir=str(clips_dir)))
    monkeypatch.setattr(events, "resolve_video_path", lambda _camera_id=None: str(source_video))
    metadata_event = {
        "event_type": "AREA_FRAME_METADATA",
        "payload": {
            "camera_id": "WS-CAM",
            "captured_at": "2026-08-21T03:00:00+00:00",
            "objects": [
                {
                    "track_id": "track-1",
                    "object_class": "forklift",
                    "display_name": "Xe nâng",
                    "confidence": 0.93,
                    "bbox": [0.1, 0.2, 0.4, 0.6],
                    "zone_hits": [
                        {"zone_id": None, "zone_name": "Zone A", "rule_result": "prohibited"}
                    ],
                }
            ],
        },
    }

    persisted = events.persist_area_metadata_violations(
        db_session,
        camera_id="WS-CAM",
        metadata_event=metadata_event,
    )

    assert len(persisted) == 1
    assert persisted[0].event_type == "ZONE_VIOLATION"
    assert persisted[0].object_class == "Xe nâng"
    assert persisted[0].bbox == [10.0, 20.0, 30.0, 40.0]
    assert persisted[0].video_clip_url.startswith("/media/clips/clip_WS-CAM_")
    clip_path = clips_dir / persisted[0].video_clip_url.rsplit("/", 1)[-1]
    _assert_playable_mp4(clip_path, expected_seconds=10.0)


def test_events_api_response_includes_zone_name_and_zone_id(db_session):
    camera = Camera(id="API-ZONE-CAM", name="API Zone Cam", location="Loc", stream_url="url")
    zone = Zone(
        id="api-zone-2",
        camera_id="API-ZONE-CAM",
        name="Khu xe nang",
        vertices=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
        allowed_classes=["car"],
        forbidden_classes=["forklift"],
        is_active=True,
    )
    event = EventModel(
        id="evt-zone-name-001",
        timestamp=datetime(2026, 8, 23, 8, 0, 0, tzinfo=timezone.utc),
        camera_id="API-ZONE-CAM",
        zone_id="api-zone-2",
        event_type="ZONE_VIOLATION",
        severity_level=3,
        object_class="Xe nang",
        confidence=0.96,
        bbox=[10, 20, 30, 40],
    )
    db_session.add_all([camera, zone, event])
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[events.get_db] = override_get_db
    try:
        response = TestClient(app).get("/api/v1/events", params={"camera_id": "API-ZONE-CAM"})
    finally:
        app.dependency_overrides.pop(events.get_db, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == "evt-zone-name-001"
    assert payload[0]["zone_id"] == "api-zone-2"
    assert payload[0]["zone_name"] == "Khu xe nang"


def test_slice_10s_ring_buffer_clip_clamps_near_source_start(tmp_path):
    source_video = tmp_path / "short-source.mp4"
    clips_dir = tmp_path / "edge-clips"
    _write_fixture_video(source_video, fps=10, seconds=6)

    manager = EventManager(cooldown_seconds=15, clips_dir=str(clips_dir))
    clip_url = manager.slice_10s_ring_buffer_clip(
        "EDGE-CAM",
        timestamp=1800000000,
        source_video_path=str(source_video),
        source_timestamp_seconds=1.0,
    )

    clip_path = clips_dir / clip_url.rsplit("/", 1)[-1]
    assert clip_path.exists()
    _assert_playable_mp4(clip_path, expected_seconds=6.0)

def test_video_stream_service_respects_env_video_path(monkeypatch, tmp_path):
    """
    Verifies VideoStreamService reads single video path from VIDEO_PATH environment variable.
    """
    fake_video = tmp_path / "test_env_video.mp4"
    fake_video.write_bytes(b"dummy_video_bytes")
    
    monkeypatch.setenv("VIDEO_PATH", str(fake_video))
    stream = VideoStreamService(camera_id="BAI-KIEM")
    assert stream.video_path == str(fake_video)


def test_video_stream_decodes_sequentially_and_releases_capture(monkeypatch, tmp_path):
    fake_video = tmp_path / "test_hevc.mp4"
    fake_video.write_bytes(b"dummy_video_bytes")

    class RecordingCapture:
        def __init__(self, path):
            self.path = path
            self.opened = True
            self.read_count = 0
            self.seek_calls = []
            self.released = False

        def isOpened(self):
            return self.opened

        def read(self):
            self.read_count += 1
            return True, f"frame-{self.read_count}"

        def set(self, prop, value):
            self.seek_calls.append((prop, value))
            return True

        def release(self):
            self.released = True
            self.opened = False

    capture = RecordingCapture(str(fake_video))
    fake_cv2 = SimpleNamespace(
        VideoCapture=lambda path: capture,
        CAP_PROP_POS_FRAMES=1,
    )
    monkeypatch.setitem(__import__("sys").modules, "cv2", fake_cv2)
    monkeypatch.setattr("backend.app.services.video_stream.time.sleep", lambda _: None)

    stream = VideoStreamService("BAI-KIEM", video_path=str(fake_video), target_fps=15)
    generator = stream.get_frame_generator()

    assert [next(generator), next(generator), next(generator)] == ["frame-1", "frame-2", "frame-3"]
    assert capture.seek_calls == []

    generator.close()
    assert capture.released is True
    assert stream.is_running is False


def test_video_stream_seeks_only_when_looping_after_eof(monkeypatch, tmp_path):
    fake_video = tmp_path / "test_loop.mp4"
    fake_video.write_bytes(b"dummy_video_bytes")

    class EofCapture:
        def __init__(self):
            self.opened = True
            self.responses = iter([(True, "last-frame"), (False, None), (True, "first-frame")])
            self.seek_calls = []

        def isOpened(self):
            return self.opened

        def read(self):
            return next(self.responses)

        def set(self, prop, value):
            self.seek_calls.append((prop, value))
            return True

        def release(self):
            self.opened = False

    capture = EofCapture()
    fake_cv2 = SimpleNamespace(VideoCapture=lambda path: capture, CAP_PROP_POS_FRAMES=1)
    monkeypatch.setitem(__import__("sys").modules, "cv2", fake_cv2)
    monkeypatch.setattr("backend.app.services.video_stream.time.sleep", lambda _: None)

    stream = VideoStreamService("BAI-KIEM", video_path=str(fake_video), target_fps=15)
    generator = stream.get_frame_generator()

    assert next(generator) == "last-frame"
    assert capture.seek_calls == []
    assert next(generator) == "first-frame"
    assert capture.seek_calls == [(1, 0)]
    generator.close()


def test_latest_frame_provider_reuses_one_sequential_capture(monkeypatch, tmp_path):
    fake_video = tmp_path / "shared_hevc.mp4"
    fake_video.write_bytes(b"dummy_video_bytes")

    class SequentialCapture:
        def __init__(self, path):
            self.path = path
            self.opened = True
            self.read_count = 0
            self.seek_calls = []

        def isOpened(self):
            return self.opened

        def get(self, prop):
            return 1000.0

        def read(self):
            self.read_count += 1
            return True, f"frame-{self.read_count}"

        def set(self, prop, value):
            self.seek_calls.append((prop, value))
            return True

        def release(self):
            self.opened = False

    captures = []

    def make_capture(path):
        capture = SequentialCapture(path)
        captures.append(capture)
        return capture

    fake_cv2 = SimpleNamespace(
        VideoCapture=make_capture,
        CAP_PROP_FPS=5,
        CAP_PROP_POS_FRAMES=1,
    )
    monkeypatch.setitem(__import__("sys").modules, "cv2", fake_cv2)

    provider = LatestFrameProvider(str(fake_video), target_fps=1000)
    try:
        first = provider.get_latest_frame()
        second = provider.get_latest_frame()
    finally:
        provider.stop()

    assert first is not None
    assert second is not None
    assert len(captures) == 1
    assert captures[0].seek_calls == []


def test_provider_registry_returns_same_provider_for_same_source(tmp_path):
    fake_video = tmp_path / "registry.mp4"
    first = get_latest_frame_provider(str(fake_video))
    second = get_latest_frame_provider(str(fake_video))

    assert first is second


def test_camera_pipeline_decodes_and_infers_once_for_shared_snapshot(monkeypatch, tmp_path):
    fake_video = tmp_path / "camera.hevc.mp4"
    fake_video.write_bytes(b"dummy-video")

    class Frame:
        shape = (100, 200, 3)

        def copy(self):
            return self

    class Capture:
        def __init__(self):
            self.read_count = 0
            self.seek_calls = []
            self.released = False

        def isOpened(self):
            return not self.released

        def get(self, _prop):
            return 1000.0

        def read(self):
            self.read_count += 1
            return True, Frame()

        def set(self, prop, value):
            self.seek_calls.append((prop, value))

        def release(self):
            self.released = True

    class Vision:
        def __init__(self):
            self.calls = 0

        def process_frame(self, frame, zones, conf_threshold):
            self.calls += 1
            return [{"id": "object-1", "bbox": [10, 20, 30, 40]}]

    capture = Capture()
    vision = Vision()
    fake_cv2 = SimpleNamespace(
        VideoCapture=lambda _path: capture,
        CAP_PROP_FPS=5,
        CAP_PROP_POS_FRAMES=1,
    )
    monkeypatch.setitem(__import__("sys").modules, "cv2", fake_cv2)

    pipeline = CameraFramePipeline(
        camera_id="BAI-KIEM",
        video_path=str(fake_video),
        vision_pipeline=vision,
        target_fps=1000,
    )
    pipeline.update_zones([])
    try:
        streamed = pipeline.wait_for_snapshot(after_frame_id=None, timeout=1.0)
        polled = pipeline.get_latest_snapshot(timeout=1.0)
    finally:
        pipeline.stop()

    assert streamed is not None
    assert polled is not None
    assert streamed.frame_id == polled.frame_id
    assert streamed.captured_at == polled.captured_at
    assert streamed.detections == polled.detections
    assert vision.calls == capture.read_count
    assert capture.seek_calls == []


def test_demo_mode_is_explicitly_disabled_by_default():
    from backend.app.core.config import Settings

    assert Settings(_env_file=None).DEMO_MODE is False

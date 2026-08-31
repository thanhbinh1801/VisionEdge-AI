import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import events

# events.py import qua namespace `app.services.*`. Dưới pytest, `app.services.frame_extractor`
# và `backend.app.services.frame_extractor` là hai module object khác nhau, nên phải patch
# đúng module mà API đang dùng thì monkeypatch mới có tác dụng.
from backend.app.services import frame_extractor as api_frame_extractor
from backend.app.services.event_manager import EventManager
from backend.app.services.video_stream import (
    CameraFramePipeline,
    LatestFrameProvider,
    VideoStreamService,
    get_camera_pipeline,
    get_latest_frame_provider,
)
from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.database.models import Camera, Zone
from backend.database.models import Event as EventModel
from backend.main import app
from backend.tests.conftest import SCHEMA_SQL_PATH

VideoSourceUnavailableError = api_frame_extractor.VideoSourceUnavailableError


@pytest.fixture(autouse=True)
def mock_telegram_dispatcher_for_live_tests(monkeypatch):
    monkeypatch.setattr(
        events.alert_dispatcher,
        "send_telegram_notification_sync",
        lambda event_data: {"status": "sent", "dispatched_at": "2026-08-24T23:36:00+07:00"},
    )
    yield
    events._wait_for_background_alert_jobs(timeout=10.0)


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


def _first_frame_mean(path: Path) -> float:
    capture = cv2.VideoCapture(str(path))
    try:
        assert capture.isOpened()
        ok, frame = capture.read()
        assert ok
        assert frame is not None
        return float(frame.mean())
    finally:
        capture.release()


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "events.db"
    engine = get_sqlite_engine(f"sqlite:///{db_path}")
    init_db(schema_sql_path=str(SCHEMA_SQL_PATH), target_engine=engine)
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
    _write_fixture_video(source_video, seconds=20)
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
    events._wait_for_background_alert_jobs(timeout=10.0)
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


def test_violation_persistence_does_not_wait_for_slow_telegram_dispatch(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="SLOW-ALERT-CAM", name="Slow Alert Cam", location="Loc", stream_url="url"))
    db_session.commit()

    clips_dir = tmp_path / "slow-alert-clips"
    source_video = tmp_path / "slow-alert-source.mp4"
    _write_fixture_video(source_video, seconds=20)
    monkeypatch.setattr(events, "event_manager", EventManager(cooldown_seconds=0, clips_dir=str(clips_dir)))

    class SlowDispatcher:
        def send_telegram_notification_sync(self, event_data):
            time.sleep(1.25)
            return {"status": "sent", "error": None, "dispatched_at": "2026-08-27T12:00:00+00:00"}

    monkeypatch.setattr(events, "alert_dispatcher", SlowDispatcher())

    started = time.perf_counter()
    event = events._persist_violation_event(
        db_session,
        camera_id="SLOW-ALERT-CAM",
        detection={
            "object_class": "person",
            "vietnamese_name": "Người",
            "confidence": 0.91,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "zone_id": None,
        },
        timestamp=datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc),
        source_video_path=str(source_video),
        source_timestamp_seconds=6.0,
    )
    elapsed = time.perf_counter() - started

    assert event is not None
    assert elapsed < 0.75
    events._wait_for_background_alert_jobs(timeout=10.0)


def test_area_metadata_violation_persistence_writes_chatbot_clip(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="WS-CAM", name="WebSocket Cam", location="Loc", stream_url="url"))
    db_session.commit()

    clips_dir = tmp_path / "metadata-clips"
    source_video = tmp_path / "metadata-source.mp4"
    _write_fixture_video(source_video, seconds=20)
    monkeypatch.setattr(events, "event_manager", EventManager(cooldown_seconds=15, clips_dir=str(clips_dir)))
    monkeypatch.setattr(events, "resolve_video_path", lambda _camera_id=None: str(source_video))
    metadata_event = {
        "event_type": "AREA_FRAME_METADATA",
        "payload": {
            "camera_id": "WS-CAM",
            "captured_at": "2026-08-21T03:00:00+00:00",
            "source_timestamp_seconds": 8.0,
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
    # CR-005: cột lưu khoá lớp, không lưu tên hiển thị. Lưu "Xe nâng" khiến mọi bộ
    # lọc `WHERE object_class = 'forklift'` của trợ lý hỏi đáp trả về 0 dòng.
    assert persisted[0].object_class == "forklift"
    assert persisted[0].bbox == [10.0, 20.0, 30.0, 40.0]
    assert persisted[0].video_clip_url.startswith("/media/clips/clip_WS-CAM_")
    events._wait_for_background_alert_jobs(timeout=10.0)
    clip_path = clips_dir / persisted[0].video_clip_url.rsplit("/", 1)[-1]
    _assert_playable_mp4(clip_path, expected_seconds=10.0)
    assert _first_frame_mean(clip_path) == pytest.approx(30.0, abs=8.0)

    # Tên tiếng Việt không mất đi — nó được dựng lại ở tầng đọc cho client.
    payload = events._event_response_from_model(persisted[0])
    assert payload["object_class"] == "forklift"
    assert payload["vietnamese_name"] == "Xe nâng"


def test_violation_evidence_job_overwrites_stale_source_start_clip(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="STALE-CLIP-CAM", name="Stale Clip Cam", location="Loc", stream_url="url"))
    db_session.commit()

    clips_dir = tmp_path / "stale-clips"
    source_video = tmp_path / "stale-source.mp4"
    _write_fixture_video(source_video, seconds=20)
    monkeypatch.setattr(events, "event_manager", EventManager(cooldown_seconds=0, clips_dir=str(clips_dir)))
    violation_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
    clip_name = f"clip_STALE-CLIP-CAM_{int(violation_time.timestamp())}.mp4"

    stale_url = events.event_manager.slice_10s_ring_buffer_clip(
        "STALE-CLIP-CAM",
        timestamp=violation_time.timestamp(),
        source_video_path=str(source_video),
        source_timestamp_seconds=0.0,
    )
    assert stale_url == f"/media/clips/{clip_name}"
    assert _first_frame_mean(clips_dir / clip_name) == pytest.approx(0.0, abs=8.0)

    event = events._persist_violation_event(
        db_session,
        camera_id="STALE-CLIP-CAM",
        detection={
            "object_class": "person",
            "vietnamese_name": "Người",
            "confidence": 0.91,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "zone_id": None,
        },
        timestamp=violation_time,
        source_video_path=str(source_video),
        source_timestamp_seconds=8.0,
    )

    assert event is not None
    assert event.video_clip_url == f"/media/clips/{clip_name}"
    events._wait_for_background_alert_jobs(timeout=10.0)
    _assert_playable_mp4(clips_dir / clip_name, expected_seconds=10.0)
    assert _first_frame_mean(clips_dir / clip_name) == pytest.approx(30.0, abs=8.0)


def test_violation_evidence_job_fails_without_source_timestamp(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="MISSING-TS-CAM", name="Missing Timestamp Cam", location="Loc", stream_url="url"))
    db_session.commit()

    clips_dir = tmp_path / "missing-timestamp-clips"
    source_video = tmp_path / "missing-timestamp-source.mp4"
    _write_fixture_video(source_video, seconds=20)
    monkeypatch.setattr(events, "event_manager", EventManager(cooldown_seconds=0, clips_dir=str(clips_dir)))
    violation_time = datetime(2026, 8, 27, 12, 5, 0, tzinfo=timezone.utc)

    event = events._persist_violation_event(
        db_session,
        camera_id="MISSING-TS-CAM",
        detection={
            "object_class": "person",
            "vietnamese_name": "Người",
            "confidence": 0.91,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "zone_id": None,
        },
        timestamp=violation_time,
        source_video_path=str(source_video),
        source_timestamp_seconds=None,
    )

    assert event is not None
    events._wait_for_background_alert_jobs(timeout=10.0)
    assert not any(clips_dir.glob("clip_MISSING-TS-CAM_*.mp4"))
    assert events._event_telegram_status_cache[event.id]["status"] == "failed"
    assert events._event_telegram_status_cache[event.id]["error"] == "VIDEO_CLIP_UNAVAILABLE"


def test_container_metadata_violation_is_detect_only_not_persisted(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="CONTAINER-CAM", name="Container Cam", location="Loc", stream_url="url"))
    db_session.commit()

    source_video = tmp_path / "container-source.mp4"
    _write_fixture_video(source_video, seconds=12)
    monkeypatch.setattr(events, "resolve_video_path", lambda _camera_id=None: str(source_video))
    metadata_event = {
        "event_type": "AREA_FRAME_METADATA",
        "payload": {
            "camera_id": "CONTAINER-CAM",
            "captured_at": "2026-08-21T03:00:00+00:00",
            "objects": [
                {
                    "track_id": "container-1",
                    "object_class": "shipping_container",
                    "display_name": "Thùng container",
                    "confidence": 0.93,
                    "bbox": [0.1, 0.2, 0.4, 0.6],
                    "zone_hits": [
                        {"zone_id": "zone-a", "zone_name": "Zone A", "rule_result": "prohibited"}
                    ],
                }
            ],
        },
    }

    persisted = events.persist_area_metadata_violations(
        db_session,
        camera_id="CONTAINER-CAM",
        metadata_event=metadata_event,
    )

    assert persisted == []


def test_legacy_container_metadata_violation_is_detect_only_not_persisted(db_session, monkeypatch, tmp_path):
    db_session.add(Camera(id="LEGACY-CONTAINER-CAM", name="Legacy Container Cam", location="Loc", stream_url="url"))
    db_session.commit()

    source_video = tmp_path / "legacy-container-source.mp4"
    _write_fixture_video(source_video, seconds=12)
    monkeypatch.setattr(events, "resolve_video_path", lambda _camera_id=None: str(source_video))
    metadata_event = {
        "event_type": "AREA_FRAME_METADATA",
        "payload": {
            "camera_id": "LEGACY-CONTAINER-CAM",
            "captured_at": "2026-08-27T15:41:00+00:00",
            "source_timestamp_seconds": 8.0,
            "objects": [
                {
                    "track_id": "container-legacy-1",
                    "object_class": "container",
                    "display_name": "Container",
                    "confidence": 0.93,
                    "bbox": [0.1, 0.2, 0.4, 0.6],
                    "zone_hits": [
                        {"zone_id": "zone-personal", "zone_name": "Zone cấm PT cá nhân", "rule_result": "prohibited"}
                    ],
                }
            ],
        },
    }

    persisted = events.persist_area_metadata_violations(
        db_session,
        camera_id="LEGACY-CONTAINER-CAM",
        metadata_event=metadata_event,
    )

    assert persisted == []


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


def test_slice_10s_ring_buffer_clip_uses_event_position_not_source_start(tmp_path):
    source_video = tmp_path / "source.mp4"
    clips_dir = tmp_path / "position-clips"
    _write_fixture_video(source_video, fps=10, seconds=20)

    manager = EventManager(cooldown_seconds=15, clips_dir=str(clips_dir))
    clip_url = manager.slice_10s_ring_buffer_clip(
        "POSITION-CAM",
        timestamp=1800000001,
        source_video_path=str(source_video),
        source_timestamp_seconds=8.0,
    )

    clip_path = clips_dir / clip_url.rsplit("/", 1)[-1]
    assert clip_path.exists()
    _assert_playable_mp4(clip_path, expected_seconds=10.0)
    # A 10s clip centered on second 8 starts near second 3. If the event timestamp
    # is lost, the old behavior starts at frame zero instead.
    assert _first_frame_mean(clip_path) == pytest.approx(30.0, abs=8.0)

def test_video_stream_service_respects_env_video_path(monkeypatch, tmp_path):
    """
    Verifies VideoStreamService reads single video path from VIDEO_PATH environment variable.
    """
    fake_video = tmp_path / "test_env_video.mp4"
    fake_video.write_bytes(b"dummy_video_bytes")
    
    monkeypatch.delenv("VIDEO_BAI_KIEM_PATH", raising=False)
    monkeypatch.setattr(api_frame_extractor.settings, "VIDEO_BAI_KIEM_PATH", "")
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
        polled = pipeline.wait_for_detection_update(after_detection_seq=None, timeout=1.0)
    finally:
        pipeline.stop()

    assert streamed is not None
    assert polled is not None
    assert streamed.frame_id == polled.frame_id
    assert streamed.captured_at == polled.captured_at
    assert polled.detections == ({"id": "object-1", "bbox": [10, 20, 30, 40]},)
    assert polled.detection_source_timestamp_seconds > 0.0
    assert vision.calls == capture.read_count
    assert capture.seek_calls == []


def _client_with_db(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[events.get_db] = override_get_db
    return TestClient(app)


def test_live_detections_returns_503_when_video_source_missing(db_session, monkeypatch):
    """BUG-005: thiếu nguồn video phải là 503 có thông điệp, không phải 500 unhandled."""
    def unavailable(camera_id=None):
        raise VideoSourceUnavailableError(camera_id, ["/tmp/khong-co.mp4"])

    monkeypatch.setattr(events, "resolve_video_path", unavailable)

    client = _client_with_db(db_session)
    try:
        response = client.get(
            "/api/v1/events/live-detections", params={"camera_id": "BAI-KIEM"}
        )
    finally:
        app.dependency_overrides.pop(events.get_db, None)

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "BAI-KIEM" in detail
    assert "VIDEO_BAI_KIEM_PATH" in detail


def test_live_detections_returns_200_with_real_video(db_session, monkeypatch, tmp_path):
    source_video = tmp_path / "live-source.mp4"
    _write_fixture_video(source_video, seconds=2)
    monkeypatch.setattr(events, "resolve_video_path", lambda camera_id=None: str(source_video))
    monkeypatch.setattr(events.vision_pipeline, "process_frame", lambda *a, **kw: [])

    client = _client_with_db(db_session)
    try:
        response = client.get(
            "/api/v1/events/live-detections", params={"camera_id": "LIVE-CAM"}
        )
    finally:
        app.dependency_overrides.pop(events.get_db, None)
        get_camera_pipeline("LIVE-CAM", events.vision_pipeline, str(source_video)).stop()

    assert response.status_code == 200
    assert response.json() == []


def test_live_detections_uses_fallback_video_when_env_unset(db_session, monkeypatch, tmp_path):
    """VIDEO_PATH chưa set vẫn stream được nhờ quét video mẫu trong repo."""
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()
    _write_fixture_video(videos_dir / "FALLBACK-CAM.mp4", seconds=2)

    monkeypatch.delenv("VIDEO_PATH", raising=False)
    monkeypatch.setattr(api_frame_extractor.settings, "VIDEO_PATH", "")
    monkeypatch.setattr(api_frame_extractor, "_video_search_dirs", lambda: [videos_dir])
    monkeypatch.setattr(events.vision_pipeline, "process_frame", lambda *a, **kw: [])

    resolved = api_frame_extractor.resolve_video_path("FALLBACK-CAM")
    assert Path(resolved).name == "FALLBACK-CAM.mp4"

    client = _client_with_db(db_session)
    try:
        response = client.get(
            "/api/v1/events/live-detections", params={"camera_id": "FALLBACK-CAM"}
        )
    finally:
        app.dependency_overrides.pop(events.get_db, None)
        get_camera_pipeline("FALLBACK-CAM", events.vision_pipeline, resolved).stop()

    assert response.status_code == 200


def test_live_detections_survives_pipeline_decode_failure(db_session, monkeypatch, tmp_path):
    """Decoder chết không được kéo theo 500: metadata lane trả danh sách rỗng."""
    broken_video = tmp_path / "broken-live.mp4"
    broken_video.write_bytes(b"not-a-real-video")
    monkeypatch.setattr(events, "resolve_video_path", lambda camera_id=None: str(broken_video))

    client = _client_with_db(db_session)
    try:
        response = client.get(
            "/api/v1/events/live-detections", params={"camera_id": "BROKEN-LIVE"}
        )
    finally:
        app.dependency_overrides.pop(events.get_db, None)
        get_camera_pipeline("BROKEN-LIVE", events.vision_pipeline, str(broken_video)).stop()

    assert response.status_code == 200
    assert response.json() == []


def test_demo_mode_is_explicitly_disabled_by_default():
    from backend.app.core.config import Settings

    assert Settings(_env_file=None).DEMO_MODE is False

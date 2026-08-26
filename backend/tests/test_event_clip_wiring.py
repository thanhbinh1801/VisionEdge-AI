"""
TASK-029: nối dây `events.py` với `vision_pipeline` và trạng thái clip pending.

Hai điều được canh ở đây, vì mất một trong hai là REQ-008 acceptance criteria 2
lại hỏng trong sản phẩm dù `EventManager` vẫn đúng:

1. Clip chứng cứ của luồng sản phẩm phải thật sự có bbox (`vision_pipeline` được
   truyền vào) và phải sinh ở thread nền (`background=True`) để không khoá
   `/live-detections`.
2. Trong ~14s clip còn đang render, API phải nói `processing` chứ không để client
   tải sớm rồi vấp file rỗng.
"""

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import events
from backend.app.services.event_manager import (
    CLIP_STATUS_MISSING,
    CLIP_STATUS_PROCESSING,
    CLIP_STATUS_READY,
    EventManager,
)
from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.database.models import Camera
from backend.database.models import Event as EventModel
from backend.main import app

# Hot path `/live-detections` bị client poll mỗi 2s; ngưỡng của TASK-029 là 0.05s
# cho toàn bộ phần ghi sự kiện. Đo thật đạt ~0.002s nên biên còn rất rộng.
HOT_PATH_BUDGET_SECONDS = 0.05

SOURCE_FPS = 10
SOURCE_SECONDS = 12
FRAME_W, FRAME_H = 64, 48


def _write_fixture_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        SOURCE_FPS,
        (FRAME_W, FRAME_H),
    )
    assert writer.isOpened()
    try:
        for index in range(SOURCE_FPS * SOURCE_SECONDS):
            writer.write(np.full((FRAME_H, FRAME_W, 3), index % 255, dtype=np.uint8))
    finally:
        writer.release()


@pytest.fixture
def source_video(tmp_path):
    path = tmp_path / "source.mp4"
    _write_fixture_video(path)
    return path


class _GatedPipeline:
    """
    Pipeline giả chặn ở lần suy luận đầu cho tới khi test mở cổng.

    Cần thế mới quan sát được trạng thái `processing`: với video fixture nhỏ,
    thread nền ghi xong nhanh hơn cả lời gọi kiểm tra kế tiếp, nên nếu không giữ
    lại thì test sẽ luôn thấy `ready` và không chứng minh được gì.
    """

    def __init__(self):
        self.gate = threading.Event()
        self.started = threading.Event()
        self.calls = 0

    def process_frame(self, frame, zones=None, conf_threshold=None):
        self.calls += 1
        self.started.set()
        self.gate.wait(timeout=30.0)
        return [
            {
                "object_class": "forklift",
                "vietnamese_name": "Xe nang",
                "confidence": 0.9,
                "bbox": [10.0, 10.0, 30.0, 30.0],
                "zone_violation": True,
            }
        ]


class _RecordingManager:
    """Ghi lại lời gọi `slice_10s_ring_buffer_clip` để soi đúng đối số truyền vào."""

    def __init__(self):
        self.calls = []
        self.vision_pipeline = object()

    def is_duplicate(self, camera_id, zone_id, object_class):
        return False

    def slice_10s_ring_buffer_clip(self, camera_id, **kwargs):
        self.calls.append((camera_id, kwargs))
        return f"/media/clips/clip_{camera_id}_1.mp4"

    def get_clip_status(self, video_clip_url):
        return CLIP_STATUS_PROCESSING


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "clip-wiring.db"
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


def _client_for(db_session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[events.get_db] = override_get_db
    return TestClient(app)


def _mounted_events_module():
    """
    Module `events` mà router thật đang dùng.

    `backend/main.py` nạp router qua `app.api.v1.events`, còn test import
    `backend.app.api.v1.events`. Hai đường import cho ra hai module object riêng
    biệt với hai `event_manager` riêng, nên test đi qua HTTP phải thay đúng bản
    được mount, không thì route vẫn chạy manager cũ.
    """
    from app.api.v1 import events as mounted  # noqa: PLC0415

    return mounted


def _install_event_manager(manager):
    """Gắn `manager` vào cả hai bản sao module; trả về hàm khôi phục."""
    mounted = _mounted_events_module()
    previous = (events.event_manager, mounted.event_manager)

    events.event_manager = manager
    mounted.event_manager = manager

    def restore():
        events.event_manager, mounted.event_manager = previous

    return restore


# --- 1. Nối dây vision_pipeline + background ------------------------------


def test_module_event_manager_uses_the_shared_vision_pipeline():
    """
    Không có dòng này thì clip sản phẩm im lặng quay về không bbox — chính là sai
    lệch mà TASK-026 đã ghi nhận và TASK-029 sinh ra để đóng.
    """
    for module in (events, _mounted_events_module()):
        assert module.event_manager.vision_pipeline is not None
        assert module.event_manager.vision_pipeline is module.vision_pipeline


def test_persist_violation_event_slices_clip_in_background(db_session, monkeypatch):
    db_session.add(Camera(id="WIRE-CAM", name="Wire Cam", location="Loc", stream_url="url"))
    db_session.commit()

    manager = _RecordingManager()
    monkeypatch.setattr(events, "event_manager", manager)

    violation_time = datetime(2026, 8, 25, 4, 0, 0, tzinfo=timezone.utc)
    event = events._persist_violation_event(
        db_session,
        camera_id="WIRE-CAM",
        detection={
            "object_class": "forklift",
            "vietnamese_name": "Xe nang",
            "confidence": 0.93,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "zone_id": None,
        },
        timestamp=violation_time,
        source_video_path="/tmp/whatever.mp4",
        source_timestamp_seconds=6.0,
    )

    assert event is not None
    assert len(manager.calls) == 1
    camera_id, kwargs = manager.calls[0]
    assert camera_id == "WIRE-CAM"
    assert kwargs["background"] is True
    assert kwargs["source_video_path"] == "/tmp/whatever.mp4"
    assert kwargs["source_timestamp_seconds"] == 6.0
    assert event.video_clip_url == "/media/clips/clip_WIRE-CAM_1.mp4"


def test_persist_violation_event_keeps_hot_path_under_budget(db_session, tmp_path, source_video):
    """
    Chốt bằng số đo chứ không bằng lời hứa: pipeline giả ở đây cố tình chậm
    0.05s mỗi frame, nên nếu ai đó đổi về `background=False` thì clip 10s sẽ tốn
    hàng giây và test này đỏ ngay.
    """
    db_session.add(Camera(id="PERF-CAM", name="Perf Cam", location="Loc", stream_url="url"))
    db_session.commit()

    class SlowPipeline:
        def process_frame(self, frame, zones=None, conf_threshold=None):
            time.sleep(0.05)
            return []

    manager = EventManager(
        cooldown_seconds=15,
        clips_dir=str(tmp_path / "clips"),
        vision_pipeline=SlowPipeline(),
    )
    restore = _install_event_manager(manager)
    try:
        started = time.perf_counter()
        event = events._persist_violation_event(
            db_session,
            camera_id="PERF-CAM",
            detection={
                "object_class": "person",
                "vietnamese_name": "Nguoi",
                "confidence": 0.9,
                "bbox": [10.0, 20.0, 30.0, 40.0],
                "zone_id": None,
            },
            timestamp=datetime(2026, 8, 25, 5, 0, 0, tzinfo=timezone.utc),
            source_video_path=str(source_video),
            source_timestamp_seconds=6.0,
        )
        elapsed = time.perf_counter() - started

        assert event is not None
        assert elapsed < HOT_PATH_BUDGET_SECONDS, f"hot path tốn {elapsed:.3f}s, vượt ngưỡng"

        assert manager.wait_for_pending_clips(timeout=120.0)
        clip_path = manager.resolve_clip_path(event.video_clip_url)
        assert Path(clip_path).exists()
    finally:
        restore()


# --- 2. Trạng thái clip pending -------------------------------------------


def test_get_clip_status_transitions_from_processing_to_ready(tmp_path, source_video):
    pipeline = _GatedPipeline()
    manager = EventManager(clips_dir=str(tmp_path / "clips"), vision_pipeline=pipeline)

    clip_url = manager.slice_10s_ring_buffer_clip(
        "GATE-CAM",
        timestamp=1,
        source_video_path=str(source_video),
        source_timestamp_seconds=6.0,
        background=True,
    )

    assert pipeline.started.wait(timeout=10.0)
    # File đã được VideoWriter tạo nhưng chưa đóng: chỉ os.path.exists thì sẽ báo
    # nhầm là xong, nên trạng thái phải dựa vào thread nền còn sống hay không.
    assert manager.get_clip_status(clip_url) == CLIP_STATUS_PROCESSING

    pipeline.gate.set()
    assert manager.wait_for_pending_clips(timeout=60.0)
    assert manager.get_clip_status(clip_url) == CLIP_STATUS_READY


def test_get_clip_status_missing_for_unknown_or_empty_url(tmp_path):
    manager = EventManager(clips_dir=str(tmp_path / "clips"))

    assert manager.get_clip_status(None) == CLIP_STATUS_MISSING
    assert manager.get_clip_status("") == CLIP_STATUS_MISSING
    assert manager.get_clip_status("/media/clips/khong-ton-tai.mp4") == CLIP_STATUS_MISSING

    empty_clip = Path(manager.clips_dir) / "rong.mp4"
    empty_clip.write_bytes(b"")
    assert manager.get_clip_status("/media/clips/rong.mp4") == CLIP_STATUS_MISSING


def test_resolve_clip_path_does_not_escape_clips_dir(tmp_path):
    manager = EventManager(clips_dir=str(tmp_path / "clips"))

    resolved = manager.resolve_clip_path("/media/clips/../../../etc/passwd")
    assert Path(resolved).parent == Path(manager.clips_dir)


def test_clip_status_endpoint_reports_processing_then_ready(db_session, tmp_path, source_video):
    db_session.add(Camera(id="API-CAM", name="Api Cam", location="Loc", stream_url="url"))
    db_session.commit()

    pipeline = _GatedPipeline()
    manager = EventManager(clips_dir=str(tmp_path / "clips"), vision_pipeline=pipeline)
    clip_url = manager.slice_10s_ring_buffer_clip(
        "API-CAM",
        timestamp=2,
        source_video_path=str(source_video),
        source_timestamp_seconds=6.0,
        background=True,
    )
    db_session.add(
        EventModel(
            id="evt-clip-status-01",
            timestamp=datetime(2026, 8, 25, 6, 0, 0, tzinfo=timezone.utc),
            camera_id="API-CAM",
            event_type="ZONE_VIOLATION",
            severity_level=3,
            object_class="Xe nang",
            confidence=0.93,
            bbox=[10.0, 20.0, 30.0, 40.0],
            video_clip_url=clip_url,
        )
    )
    db_session.commit()

    restore = _install_event_manager(manager)
    client = _client_for(db_session)
    try:
        assert pipeline.started.wait(timeout=10.0)
        response = client.get("/api/v1/events/evt-clip-status-01/clip-status")
        assert response.status_code == 200
        assert response.json() == {
            "event_id": "evt-clip-status-01",
            "clip_status": CLIP_STATUS_PROCESSING,
            "video_clip_url": clip_url,
        }

        # Danh sách sự kiện cũng phải mang trạng thái, để UI không phải gọi thêm
        # một vòng cho từng dòng trong bảng.
        listed = client.get("/api/v1/events", params={"camera_id": "API-CAM"})
        assert listed.status_code == 200
        assert listed.json()[0]["clip_status"] == CLIP_STATUS_PROCESSING

        pipeline.gate.set()
        assert manager.wait_for_pending_clips(timeout=60.0)

        response = client.get("/api/v1/events/evt-clip-status-01/clip-status")
        assert response.status_code == 200
        assert response.json()["clip_status"] == CLIP_STATUS_READY
    finally:
        pipeline.gate.set()
        manager.wait_for_pending_clips(timeout=60.0)
        app.dependency_overrides.pop(events.get_db, None)
        restore()


def test_clip_status_endpoint_returns_404_for_unknown_event(db_session):
    client = _client_for(db_session)
    try:
        response = client.get("/api/v1/events/evt-khong-co/clip-status")
    finally:
        app.dependency_overrides.pop(events.get_db, None)

    assert response.status_code == 404


def test_clip_status_endpoint_reports_missing_when_file_never_written(db_session, tmp_path):
    db_session.add(Camera(id="MISS-CAM", name="Miss Cam", location="Loc", stream_url="url"))
    db_session.add(
        EventModel(
            id="evt-clip-missing-01",
            timestamp=datetime(2026, 8, 25, 7, 0, 0, tzinfo=timezone.utc),
            camera_id="MISS-CAM",
            event_type="ZONE_VIOLATION",
            severity_level=3,
            object_class="Nguoi",
            confidence=0.9,
            video_clip_url="/media/clips/clip_MISS-CAM_999.mp4",
        )
    )
    db_session.commit()

    restore = _install_event_manager(EventManager(clips_dir=str(tmp_path / "clips")))
    client = _client_for(db_session)
    try:
        response = client.get("/api/v1/events/evt-clip-missing-01/clip-status")
    finally:
        app.dependency_overrides.pop(events.get_db, None)
        restore()

    assert response.status_code == 200
    assert response.json()["clip_status"] == CLIP_STATUS_MISSING

"""
Phủ test cho endpoint GET /api/v1/events/live-detections.

Endpoint này là đường đi duy nhất đưa kết quả nhận dạng thật lên UI, nhưng trước
đây không có test nào chạm tới. Bốn thứ cần được khoá lại:

1. Ánh xạ camera -> đúng file video demo.
2. Frame đọc ra là frame sạch (footage nguồn từng bị nát do seek HEVC).
3. BBox trả về nằm trong [0, 100] vì frontend dùng trực tiếp làm % CSS.
4. Vi phạm chỉ được ghi vào CSDL khi đó là detection thật từ YOLO — không còn
   nhánh dữ liệu mô phỏng nào được phép tiêm vào.
"""

import os
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1 import events as events_module
from backend.database.engine import get_sqlite_engine, get_db, init_db, SessionLocal
from backend.database.models import Camera, Event, Zone
from backend.database.repository import EventRepository

TEST_DB_URL = "sqlite:///./test_live_detections.db"
TEST_CAMERA_ID = "TEST-LIVE-CAM"

# Zone phủ kín khung hình, cấm 'person' -> mọi detection person đều là vi phạm.
FULL_FRAME_ZONE_VERTICES = [
    {"x": 0.0, "y": 0.0},
    {"x": 100.0, "y": 0.0},
    {"x": 100.0, "y": 100.0},
    {"x": 0.0, "y": 100.0},
]


@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path="docs/contracts/db/schema.sql", target_engine=engine)
    yield engine
    engine.dispose()
    if os.path.exists("test_live_detections.db"):
        try:
            os.remove("test_live_detections.db")
        except PermissionError:
            pass


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    session.add(Camera(
        id=TEST_CAMERA_ID,
        name="Camera kiểm thử",
        location="Bãi kiểm",
        stream_url="file://test.mp4",
    ))
    session.add(Zone(
        id="zone-live-test",
        camera_id=TEST_CAMERA_ID,
        name="Vùng cấm người",
        vertices=FULL_FRAME_ZONE_VERTICES,
        allowed_classes=[],
        forbidden_classes=["person"],
        color="#ff453a",
    ))
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session, monkeypatch):
    """
    App tối giản chỉ gắn router events, dùng session test và frame giả.

    Không import backend/main.py để tránh init_db() chạy vào CSDL thật.
    """
    app = FastAPI()
    app.include_router(events_module.router, prefix="/api/v1/events")
    app.dependency_overrides[get_db] = lambda: db_session

    # Video thật không có trong repo (.gitignore loại *.mp4), nên trỏ endpoint vào
    # một file chắc chắn tồn tại và cấp frame giả thay cho decoder.
    fake_video = os.path.abspath(__file__)
    monkeypatch.setattr(
        events_module,
        "resolve_camera_video",
        lambda camera_id: (fake_video, "TEST.mp4"),
    )
    monkeypatch.setattr(
        events_module.frame_source,
        "read",
        lambda video_path: np.zeros((720, 1280, 3), dtype=np.uint8),
    )

    with TestClient(app) as c:
        yield c


def set_detections(monkeypatch, detections):
    """Cố định đầu ra của YOLO để test không phụ thuộc weights hay footage."""
    monkeypatch.setattr(
        events_module.vision_pipeline,
        "process_frame",
        lambda frame, zones: [dict(d) for d in detections],
    )


def person_violation_detection():
    return {
        "object_class": "person",
        "vietnamese_name": "Người",
        "confidence": 0.41,
        "bbox": [50.2, 39.5, 5.0, 11.0],
        "severity": 3,
        "zone_violation": True,
        "zone_name": "Vùng cấm người",
    }


# --- 1. Ánh xạ camera -> video -------------------------------------------------

def test_camera_video_mapping_points_to_expected_file(monkeypatch):
    """
    Mỗi camera phải trỏ vào đúng clip của nó.

    Đây là cái bẫy đã sập một lần: bật lại VIDEO_*_PATH trong .env với giá trị cũ
    thì toàn bộ ánh xạ âm thầm quay về footage cũ mà không có dấu hiệu gì.
    """
    for attr in ("VIDEO_BAI_KIEM_PATH", "VIDEO_GATE_01_PATH", "VIDEO_XUONG_AN_NINH_PATH"):
        monkeypatch.setattr(events_module.settings, attr, "")

    assert set(events_module.CAMERA_VIDEO_FILES) == {"BAI-KIEM", "XUONG-AN-NINH", "GATE-01"}

    for camera_id, expected_file in events_module.CAMERA_VIDEO_FILES.items():
        _path, filename = events_module.resolve_camera_video(camera_id)
        assert filename == expected_file


def test_unknown_camera_falls_back_to_default_video(monkeypatch):
    for attr in ("VIDEO_BAI_KIEM_PATH", "VIDEO_GATE_01_PATH", "VIDEO_XUONG_AN_NINH_PATH"):
        monkeypatch.setattr(events_module.settings, attr, "")
    _path, filename = events_module.resolve_camera_video("KHONG-TON-TAI")
    assert filename == events_module.DEFAULT_VIDEO_FILE


# --- 2. Frame đọc ra phải sạch -------------------------------------------------

def test_is_frame_usable_rejects_corrupted_flat_frame():
    """Frame hỏng do thiếu frame tham chiếu gần như phẳng một màu xám."""
    flat_gray = np.full((720, 1280, 3), 128, dtype=np.uint8)
    assert events_module.is_frame_usable(flat_gray) is False
    assert events_module.is_frame_usable(None) is False
    assert events_module.is_frame_usable(np.array([], dtype=np.uint8)) is False


def test_is_frame_usable_accepts_frame_with_content():
    rng = np.random.default_rng(seed=0)
    noisy = rng.integers(0, 256, size=(720, 1280, 3), dtype=np.uint8)
    assert events_module.is_frame_usable(noisy) is True


@pytest.mark.parametrize("camera_id", ["BAI-KIEM", "XUONG-AN-NINH", "GATE-01"])
def test_demo_video_yields_usable_frames(camera_id, monkeypatch):
    """
    Đọc tuần tự trên clip thật phải cho frame dùng được liên tục.

    Bỏ qua khi chưa có footage: .gitignore loại *.mp4 nên bản checkout sạch
    không có data/video/*.mp4.
    """
    for attr in ("VIDEO_BAI_KIEM_PATH", "VIDEO_GATE_01_PATH", "VIDEO_XUONG_AN_NINH_PATH"):
        monkeypatch.setattr(events_module.settings, attr, "")

    video_path, _ = events_module.resolve_camera_video(camera_id)
    if not os.path.exists(video_path):
        pytest.skip(f"Chưa có video demo cho {camera_id}: {video_path}")

    source = events_module.SequentialFrameSource()
    try:
        for _ in range(5):
            frame = source.read(video_path)
            assert frame is not None
            assert events_module.is_frame_usable(frame) is True
    finally:
        source.release()


@pytest.mark.parametrize("camera_id", ["BAI-KIEM", "XUONG-AN-NINH", "GATE-01"])
def test_read_at_returns_frame_near_requested_timestamp(camera_id, monkeypatch):
    """
    Seek theo mốc thời gian phải trả về đúng frame quanh mốc đó.

    Đây là điều kiện để overlay khớp với thẻ <video> phía client: bbox chỉ đúng
    khi frame backend suy luận cùng là frame trình duyệt đang hiển thị.
    """
    import cv2

    for attr in ("VIDEO_BAI_KIEM_PATH", "VIDEO_GATE_01_PATH", "VIDEO_XUONG_AN_NINH_PATH"):
        monkeypatch.setattr(events_module.settings, attr, "")

    video_path, _ = events_module.resolve_camera_video(camera_id)
    if not os.path.exists(video_path):
        pytest.skip(f"Chưa có video demo cho {camera_id}: {video_path}")

    source = events_module.SequentialFrameSource()
    try:
        for target in (0.5, 3.0, 7.5):
            frame = source.read_at(video_path, target)
            assert frame is not None, f"Không đọc được frame tại t={target}s"
            assert events_module.is_frame_usable(frame) is True

            # Vị trí decoder sau khi đọc phải nằm ngay sau mốc yêu cầu. Cho phép lệch
            # 0.5s vì read_at có thể phải bỏ qua vài frame hỏng quanh điểm seek.
            pos = source._caps[video_path].get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            assert target - 0.1 <= pos <= target + 0.5, f"t={target}s nhưng decoder ở {pos}s"
    finally:
        source.release()


def test_endpoint_uses_client_timestamp_when_t_is_given(client, db_session, monkeypatch):
    """Tham số `t` phải được chuyển thẳng xuống read_at, không bị đọc tuần tự chen ngang."""
    set_detections(monkeypatch, [])
    seen = []

    monkeypatch.setattr(
        events_module.frame_source,
        "read_at",
        lambda video_path, t_seconds: seen.append(t_seconds)
        or np.zeros((720, 1280, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(
        events_module.frame_source,
        "read",
        lambda video_path: pytest.fail("Đã có `t` thì không được lùi về đọc tuần tự"),
    )

    res = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}&t=12.5")

    assert res.status_code == 200
    assert seen == [12.5]


def test_endpoint_falls_back_to_sequential_when_seek_fails(client, db_session, monkeypatch):
    """
    Seek hỏng (footage HEVC thiếu frame tham chiếu) thì vẫn phải có detection.

    Overlay lệch còn hơn khung hình trống, miễn là backend ghi log cảnh báo.
    """
    set_detections(monkeypatch, [])
    monkeypatch.setattr(events_module.frame_source, "read_at", lambda video_path, t_seconds: None)

    res = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}&t=4.2")

    assert res.status_code == 200


def test_endpoint_rejects_negative_timestamp(client, db_session, monkeypatch):
    set_detections(monkeypatch, [])

    res = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}&t=-1")

    assert res.status_code == 422


# --- 3 & 4. Hợp đồng của endpoint ---------------------------------------------

def test_no_detection_returns_empty_list(client, db_session, monkeypatch):
    """
    YOLO im lặng thì endpoint trả mảng rỗng, không bịa dữ liệu.

    Test này khoá lại việc đã xoá khối candidate_objects: trước đây nó tiêm
    forklift/container/person với confidence 0.95 mỗi khi không phát hiện được gì.
    """
    set_detections(monkeypatch, [])

    res = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}")

    assert res.status_code == 200
    assert res.json() == []


def test_no_detection_writes_nothing_to_database(client, db_session, monkeypatch):
    set_detections(monkeypatch, [])

    before = db_session.query(Event).filter(Event.camera_id == TEST_CAMERA_ID).count()
    client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}")
    after = db_session.query(Event).filter(Event.camera_id == TEST_CAMERA_ID).count()

    assert before == after == 0


def test_response_bbox_stays_within_percentage_range(client, monkeypatch):
    """Frontend đổ thẳng bbox vào CSS `left/top/width/height` theo %."""
    set_detections(monkeypatch, [
        person_violation_detection(),
        {
            "object_class": "truck",
            "vietnamese_name": "Xe tải",
            "confidence": 0.38,
            "bbox": [0.0, 0.0, 100.0, 100.0],
            "severity": 1,
            "zone_violation": False,
            "zone_name": None,
        },
    ])

    payload = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}").json()

    assert len(payload) == 2
    for det in payload:
        left, top, width, height = det["bbox"]
        assert 0.0 <= left <= 100.0
        assert 0.0 <= top <= 100.0
        assert 0.0 < width <= 100.0
        assert 0.0 < height <= 100.0
        assert left + width <= 100.5   # dung sai làm tròn 0.1 của pipeline
        assert top + height <= 100.5


def test_response_preserves_real_confidence(client, monkeypatch):
    """Confidence thật (~0.4) không được thay bằng hằng số 0.95 nào."""
    set_detections(monkeypatch, [person_violation_detection()])

    payload = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}").json()

    assert payload[0]["confidence"] == pytest.approx(0.41)


def test_real_violation_is_persisted(client, db_session, monkeypatch):
    set_detections(monkeypatch, [person_violation_detection()])

    payload = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}").json()

    assert payload[0]["zone_violation"] is True
    assert payload[0]["severity"] == 3
    assert "VI PHẠM" in payload[0]["label"]

    stored = db_session.query(Event).filter(Event.camera_id == TEST_CAMERA_ID).all()
    assert len(stored) == 1
    assert stored[0].event_type == "ZONE_VIOLATION"
    assert stored[0].severity_level == 3
    assert stored[0].zone_id == "zone-live-test"
    assert stored[0].confidence == pytest.approx(0.41)


def test_allowed_detection_is_not_persisted(client, db_session, monkeypatch):
    """Đối tượng được phép chỉ hiển thị, không sinh sự kiện vi phạm."""
    set_detections(monkeypatch, [{
        "object_class": "truck",
        "vietnamese_name": "Xe tải",
        "confidence": 0.38,
        "bbox": [10.0, 10.0, 20.0, 20.0],
        "severity": 1,
        "zone_violation": False,
        "zone_name": "Vùng cấm người",
    }])

    payload = client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}").json()

    assert payload[0]["zone_violation"] is False
    assert "ĐƯỢC PHÉP" in payload[0]["label"]
    assert db_session.query(Event).filter(Event.camera_id == TEST_CAMERA_ID).count() == 0


def test_repeated_violation_is_deduplicated_within_10s(client, db_session, monkeypatch):
    """Polling 3 giây/lần không được nhân bản cùng một vi phạm thành nhiều sự kiện."""
    set_detections(monkeypatch, [person_violation_detection()])

    for _ in range(3):
        client.get(f"/api/v1/events/live-detections?camera_id={TEST_CAMERA_ID}")

    repo = EventRepository(db_session)
    stored = repo.get_recent_events(camera_id=TEST_CAMERA_ID, severity_level=3, limit=10)
    assert len(stored) == 1

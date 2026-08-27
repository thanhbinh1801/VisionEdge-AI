from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import events
from backend.app.services import frame_extractor
from backend.app.services.video_stream import get_camera_pipeline
from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.main import app
from backend.tests.conftest import SCHEMA_SQL_PATH


def _write_fixture_video(path: Path, *, fps: int = 10, seconds: int = 2) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 48))
    assert writer.isOpened()
    try:
        for index in range(fps * seconds):
            writer.write(np.full((48, 64, 3), index % 255, dtype=np.uint8))
    finally:
        writer.release()


class DummyCapture:
    def __init__(self, path: str):
        self.path = path
        self.opened = True
        self.pos = 0
        self.read_count = 0
        self.seek_calls = []

    def isOpened(self):
        return self.opened

    def get(self, prop):
        if prop == 5:  # CAP_PROP_FPS
            return 30
        if prop == 7:  # CAP_PROP_FRAME_COUNT
            return 120
        return 0

    def set(self, prop, value):
        self.pos = value
        self.seek_calls.append((prop, value))

    def read(self):
        frame = f"frame-{self.read_count}"
        self.read_count += 1
        return True, frame

    def release(self):
        self.opened = False


def test_extract_jpeg_frame_bytes_reads_target_frame(monkeypatch):
    dummy_cv2 = SimpleNamespace(
        VideoCapture=lambda path: DummyCapture(path),
        CAP_PROP_FPS=5,
        CAP_PROP_FRAME_COUNT=7,
        CAP_PROP_POS_FRAMES=1,
        IMWRITE_JPEG_QUALITY=1,
        imencode=lambda ext, frame, params: (True, SimpleNamespace(tobytes=lambda: b"jpeg-bytes")),
    )
    monkeypatch.setitem(__import__("sys").modules, "cv2", dummy_cv2)

    payload = frame_extractor.extract_jpeg_frame_bytes("/tmp/test.mp4", seek_seconds=1.0)

    assert payload == b"jpeg-bytes"


def test_extract_frame_decodes_forward_and_returns_actual_metadata(monkeypatch):
    capture = DummyCapture("/tmp/hevc.mp4")
    dummy_cv2 = SimpleNamespace(
        VideoCapture=lambda path: capture,
        CAP_PROP_FPS=5,
        CAP_PROP_FRAME_COUNT=7,
        CAP_PROP_POS_FRAMES=1,
        IMWRITE_JPEG_QUALITY=1,
        imencode=lambda ext, frame, params: (
            True,
            SimpleNamespace(tobytes=lambda: frame.encode()),
        ),
    )
    monkeypatch.setitem(__import__("sys").modules, "cv2", dummy_cv2)

    result = frame_extractor.extract_jpeg_frame(
        "/tmp/hevc.mp4", timestamp_seconds=2.0
    )

    assert result.jpeg_bytes == b"frame-60"
    assert result.source_name == "hevc.mp4"
    assert result.requested_frame_index == 60
    assert result.actual_frame_index == 60
    assert result.actual_timestamp_seconds == 2.0
    assert capture.read_count == 61
    assert capture.seek_calls == []


def test_extract_frame_rejects_timestamp_and_frame_index_together():
    try:
        frame_extractor.extract_jpeg_frame(
            "/tmp/hevc.mp4", timestamp_seconds=1.0, frame_index=30
        )
        assert False, "Expected mutually exclusive selectors to fail"
    except ValueError as exc:
        assert "timestamp_seconds or frame_index" in str(exc)


@pytest.fixture
def isolated_video_env(monkeypatch, tmp_path):
    """Cô lập resolve_video_path khỏi .env và khỏi data/video thật của repo."""
    monkeypatch.delenv("VIDEO_PATH", raising=False)
    monkeypatch.delenv("VIDEOS_DIR", raising=False)
    monkeypatch.delenv("VIDEO_BAI_KIEM_PATH", raising=False)
    monkeypatch.setattr(frame_extractor.settings, "VIDEO_PATH", "")
    monkeypatch.setattr(frame_extractor.settings, "VIDEO_BAI_KIEM_PATH", "")
    monkeypatch.setattr(frame_extractor.settings, "VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setattr(frame_extractor, "_video_search_dirs", lambda: [tmp_path / "videos"])
    return tmp_path / "videos"


def test_resolve_video_path_uses_env_video_path(monkeypatch, tmp_path):
    fake_video = tmp_path / "KiemHoa-Hik (1).mp4"
    fake_video.write_bytes(b"fake-video")
    monkeypatch.setattr(frame_extractor.settings, "VIDEO_PATH", str(fake_video))

    resolved = frame_extractor.resolve_video_path("BAI-KIEM")

    assert Path(resolved) == fake_video


def test_resolve_video_path_prefers_per_camera_override(monkeypatch, tmp_path):
    shared = tmp_path / "shared.mp4"
    per_camera = tmp_path / "bai-kiem-override.mp4"
    shared.write_bytes(b"shared")
    per_camera.write_bytes(b"per-camera")
    monkeypatch.setattr(frame_extractor.settings, "VIDEO_PATH", str(shared))
    monkeypatch.setenv("VIDEO_BAI_KIEM_PATH", str(per_camera))

    assert Path(frame_extractor.resolve_video_path("BAI-KIEM")) == per_camera
    assert Path(frame_extractor.resolve_video_path("GATE-01")) == shared


def test_resolve_video_path_falls_back_to_camera_named_sample(isolated_video_env):
    videos_dir = isolated_video_env
    videos_dir.mkdir(parents=True)
    (videos_dir / "GATE-01.mp4").write_bytes(b"gate")
    (videos_dir / "BAI-KIEM.mp4").write_bytes(b"bai-kiem")

    resolved = frame_extractor.resolve_video_path("BAI-KIEM")

    assert Path(resolved).name == "BAI-KIEM.mp4"


def test_resolve_video_path_falls_back_to_any_sample_when_camera_file_absent(isolated_video_env):
    videos_dir = isolated_video_env
    videos_dir.mkdir(parents=True)
    (videos_dir / "GATE-01.mp4").write_bytes(b"gate")

    resolved = frame_extractor.resolve_video_path("BAI-KIEM")

    assert Path(resolved).name == "GATE-01.mp4"


def test_resolve_video_path_ignores_missing_env_and_uses_repo_sample(isolated_video_env, monkeypatch):
    videos_dir = isolated_video_env
    videos_dir.mkdir(parents=True)
    (videos_dir / "BAI-KIEM.mp4").write_bytes(b"bai-kiem")
    monkeypatch.setattr(
        frame_extractor.settings, "VIDEO_PATH", str(videos_dir / "khong-ton-tai.mp4")
    )

    resolved = frame_extractor.resolve_video_path("BAI-KIEM")

    assert Path(resolved).name == "BAI-KIEM.mp4"


def test_resolve_video_path_fails_when_no_source_available(isolated_video_env, monkeypatch):
    missing = isolated_video_env / "missing.mp4"
    monkeypatch.setattr(frame_extractor.settings, "VIDEO_PATH", str(missing))

    with pytest.raises(frame_extractor.VideoSourceUnavailableError) as excinfo:
        frame_extractor.resolve_video_path("BAI-KIEM")

    assert "VIDEO_PATH does not point to an existing file" in str(excinfo.value)
    assert str(missing) in str(excinfo.value)


def test_video_source_unavailable_error_stays_a_runtime_error():
    """Caller cũ bắt RuntimeError vẫn hoạt động sau khi thêm lớp lỗi riêng."""
    assert issubclass(frame_extractor.VideoSourceUnavailableError, RuntimeError)


def _client_with_db(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[events.get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "video-feed.db"
    engine = get_sqlite_engine(f"sqlite:///{db_path}")
    assert SCHEMA_SQL_PATH.is_file(), f"Không tìm thấy schema DDL tại {SCHEMA_SQL_PATH}"
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


def test_video_feed_returns_503_when_video_source_missing(db_session, monkeypatch):
    def unavailable(camera_id=None):
        raise events.VideoSourceUnavailableError(camera_id, ["/tmp/khong-co.mp4"])

    monkeypatch.setattr(events, "resolve_video_path", unavailable)

    client = _client_with_db(db_session)
    try:
        # Endpoint này trả StreamingResponse MJPEG vô hạn ở nhánh thành công, nên
        # luôn gọi bằng client.stream(): body chỉ được đọc khi ta chủ động yêu cầu.
        with client.stream(
            "GET", "/api/v1/events/video-feed", params={"camera_id": "BAI-KIEM"}
        ) as response:
            assert response.status_code == 503
            response.read()
            detail = response.json()["detail"]
    finally:
        app.dependency_overrides.pop(events.get_db, None)

    assert "BAI-KIEM" in detail


def test_video_feed_streams_first_mjpeg_chunk_with_real_video(db_session, monkeypatch, tmp_path):
    source_video = tmp_path / "feed-source.mp4"
    _write_fixture_video(source_video)
    monkeypatch.setattr(events, "resolve_video_path", lambda camera_id=None: str(source_video))
    monkeypatch.setattr(events.vision_pipeline, "process_frame", lambda *a, **kw: [])
    # TestClient gom hết body rồi mới trả response, nên phải chặn stream ở chunk đầu
    # tiên; nếu không generator MJPEG sẽ chạy vô hạn và test treo.
    monkeypatch.setattr(events, "_MAX_STREAM_FRAMES", 1)

    client = _client_with_db(db_session)
    try:
        with client.stream(
            "GET", "/api/v1/events/video-feed", params={"camera_id": "FEED-CAM"}
        ) as response:
            assert response.status_code == 200
            assert "multipart/x-mixed-replace" in response.headers["content-type"]
            first_bytes = next(response.iter_bytes())
    finally:
        app.dependency_overrides.pop(events.get_db, None)
        get_camera_pipeline("FEED-CAM", events.vision_pipeline, str(source_video)).stop()

    assert first_bytes.startswith(b"--frame")
    assert b"Content-Type: image/jpeg" in first_bytes


def test_video_feed_returns_503_when_pipeline_cannot_decode(db_session, monkeypatch, tmp_path):
    broken_video = tmp_path / "broken.mp4"
    broken_video.write_bytes(b"not-a-real-video")
    monkeypatch.setattr(events, "resolve_video_path", lambda camera_id=None: str(broken_video))

    client = _client_with_db(db_session)
    try:
        with client.stream(
            "GET", "/api/v1/events/video-feed", params={"camera_id": "BROKEN-CAM"}
        ) as response:
            assert response.status_code == 503
            response.read()
            detail = response.json()["detail"]
    finally:
        app.dependency_overrides.pop(events.get_db, None)
        get_camera_pipeline("BROKEN-CAM", events.vision_pipeline, str(broken_video)).stop()

    assert "BROKEN-CAM" in detail

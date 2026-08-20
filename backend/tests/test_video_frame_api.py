from pathlib import Path
from types import SimpleNamespace

from backend.app.services import frame_extractor


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


def test_resolve_video_path_uses_env_video_path(monkeypatch, tmp_path):
    fake_video = tmp_path / "KiemHoa-Hik (1).mp4"
    fake_video.write_bytes(b"fake-video")
    monkeypatch.setattr(frame_extractor.settings, "VIDEO_PATH", str(fake_video))

    resolved = frame_extractor.resolve_video_path("BAI-KIEM")

    assert Path(resolved) == fake_video


def test_resolve_video_path_fails_when_env_missing_file(monkeypatch, tmp_path):
    missing = tmp_path / "missing.mp4"
    monkeypatch.setattr(frame_extractor.settings, "VIDEO_PATH", str(missing))

    try:
        frame_extractor.resolve_video_path("BAI-KIEM")
        assert False, "Expected resolve_video_path to fail when env file is missing"
    except RuntimeError as exc:
        assert "VIDEO_PATH does not point to an existing file" in str(exc)

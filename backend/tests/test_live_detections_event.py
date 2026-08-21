from datetime import datetime
from types import SimpleNamespace

from backend.app.services.video_stream import (
    CameraFramePipeline,
    LatestFrameProvider,
    VideoStreamService,
    get_latest_frame_provider,
)
from backend.database.models import Event as EventModel


def test_event_model_instantiation_with_zone_id_succeeds():
    """
    Verifies EventModel instantiation with zone_id succeeds and valid schema fields work cleanly.
    """
    evt = EventModel(
        id="evt-live-test-01",
        timestamp=datetime.utcnow(),
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

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.api.v1 import events


class DummyFrame:
    shape = (100, 200, 3)

    def copy(self):
        return self


class StubPipeline:
    def __init__(self, snapshots):
        self._snapshots = list(snapshots)
        self.update_calls = []
        self.wait_calls = []

    def update_zones(self, zones, zone_version):
        self.update_calls.append((zones, zone_version))

    def wait_for_snapshot(self, after_frame_id, timeout=2.0):
        self.wait_calls.append((after_frame_id, timeout))
        if self._snapshots:
            return self._snapshots.pop(0)
        return None


def _zone_state():
    return SimpleNamespace(zones=[], zone_version=7)


def _snapshot(frame_id=11, captured_at="2026-08-21T09:00:00+00:00"):
    return SimpleNamespace(
        frame_id=frame_id,
        captured_at=captured_at,
        frame=DummyFrame(),
        detections=(),
    )


def _install_cv2(monkeypatch, *, encode_ok=True):
    rectangle_calls = []
    dummy_cv2 = SimpleNamespace(
        IMWRITE_JPEG_QUALITY=1,
        FONT_HERSHEY_SIMPLEX=0,
        imencode=lambda ext, frame, params: (
            encode_ok,
            SimpleNamespace(tobytes=lambda: b"jpeg-first-frame"),
        ),
        rectangle=lambda *args, **kwargs: rectangle_calls.append(args),
        getTextSize=lambda *args, **kwargs: ((32, 10), 0),
        putText=lambda *args, **kwargs: None,
        polylines=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(events, "cv2", dummy_cv2)
    return rectangle_calls


def test_video_feed_emits_first_mjpeg_chunk_without_waiting_forever(monkeypatch):
    pipeline = StubPipeline([_snapshot()])
    monkeypatch.setattr(events, "get_camera_pipeline", lambda *args, **kwargs: pipeline)
    monkeypatch.setattr(events.zone_cache_service, "get_or_load", lambda db, camera_id: _zone_state())
    _install_cv2(monkeypatch)

    response = events.video_feed(db=object())
    iterator = response.body_iterator
    first_chunk = asyncio.run(iterator.__anext__())

    assert response.media_type == "multipart/x-mixed-replace; boundary=frame"
    assert first_chunk.startswith(b"--frame\r\nContent-Type: image/jpeg\r\n")
    assert b"X-Frame-Id: 11\r\n" in first_chunk
    assert b"jpeg-first-frame" in first_chunk
    assert pipeline.wait_calls == [(None, pytest.approx(2.0))]


def test_video_feed_returns_explicit_error_when_first_snapshot_never_arrives(monkeypatch):
    pipeline = StubPipeline([None, None, None, None])
    monkeypatch.setattr(events, "get_camera_pipeline", lambda *args, **kwargs: pipeline)
    monkeypatch.setattr(events.zone_cache_service, "get_or_load", lambda db, camera_id: _zone_state())
    _install_cv2(monkeypatch)

    monotonic_values = iter([0.0, 0.0, 2.0, 2.0, 4.0, 4.0, 5.0, 5.0])
    monkeypatch.setattr(events.time, "monotonic", lambda: next(monotonic_values))

    with pytest.raises(HTTPException) as excinfo:
        events.video_feed(db=object())

    assert excinfo.value.status_code == 503
    assert "frame đầu tiên" in excinfo.value.detail
    assert len(pipeline.wait_calls) == 3


def test_video_feed_returns_explicit_error_when_first_snapshot_cannot_encode(monkeypatch):
    pipeline = StubPipeline([_snapshot()])
    monkeypatch.setattr(events, "get_camera_pipeline", lambda *args, **kwargs: pipeline)
    monkeypatch.setattr(events.zone_cache_service, "get_or_load", lambda db, camera_id: _zone_state())
    _install_cv2(monkeypatch, encode_ok=False)

    with pytest.raises(HTTPException) as excinfo:
        events.video_feed(db=object())

    assert excinfo.value.status_code == 503
    assert "mã hóa được frame đầu tiên" in excinfo.value.detail


def test_video_feed_hides_static_container_boxes_until_debug_enabled(monkeypatch):
    snapshot = _snapshot()
    snapshot.detections = (
        {
            "object_class": "container",
            "vietnamese_name": "Container",
            "confidence": 0.9,
            "bbox": [10, 10, 20, 20],
            "zone_violation": False,
        },
    )
    monkeypatch.setattr(events.zone_cache_service, "get_or_load", lambda db, camera_id: _zone_state())

    hidden_pipeline = StubPipeline([snapshot])
    monkeypatch.setattr(events, "get_camera_pipeline", lambda *args, **kwargs: hidden_pipeline)
    hidden_rectangles = _install_cv2(monkeypatch)
    response = events.video_feed(db=object())
    asyncio.run(response.body_iterator.__anext__())
    assert hidden_rectangles == []

    shown_pipeline = StubPipeline([snapshot])
    monkeypatch.setattr(events, "get_camera_pipeline", lambda *args, **kwargs: shown_pipeline)
    shown_rectangles = _install_cv2(monkeypatch)
    response = events.video_feed(db=object(), show_static_containers=True)
    asyncio.run(response.body_iterator.__anext__())
    assert len(shown_rectangles) >= 2

"""CR-006: vòng decode phải publish frame mà không chờ inference.

Trước CR-006, `CameraFramePipeline` gọi `process_frame()` đồng bộ ngay trong vòng
decode, nên toàn bộ video lane bị khóa ở nhịp suy luận (đo được 3.07 FPS trên
`BAI-KIEM` trong khi nguồn là 25 FPS). Các test dưới đây cố định lại ranh giới đó.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from backend.app.services.video_stream import CameraFramePipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_VIDEO = PROJECT_ROOT / "data" / "video" / "BAI-KIEM.mp4"

# Đủ chậm để bỏ xa nhịp decode 25 FPS, đủ nhanh để test không kéo dài.
SLOW_INFERENCE_SECONDS = 0.25


class SlowVisionPipelineStub:
    """Đứng thay YOLO: chậm có chủ đích và đếm số lần thực sự được gọi."""

    def __init__(self, delay_seconds: float = SLOW_INFERENCE_SECONDS):
        self.delay_seconds = delay_seconds
        self.call_count = 0
        self._lock = threading.Lock()

    def process_frame(self, frame_matrix, zones=None, conf_threshold=None):
        time.sleep(self.delay_seconds)
        with self._lock:
            self.call_count += 1
            current = self.call_count
        return [
            {
                "id": f"stub-{current}",
                "object_class": "person",
                "vietnamese_name": "Người",
                "confidence": 0.9,
                "bbox": [10.0, 10.0, 20.0, 20.0],
                "severity": 1,
                "zone_violation": False,
                "zone_name": None,
                "zone_id": None,
            }
        ]


@pytest.fixture(name="pipeline")
def pipeline_fixture():
    if not SAMPLE_VIDEO.is_file():
        pytest.skip(f"Thiếu video mẫu: {SAMPLE_VIDEO}")
    stub = SlowVisionPipelineStub()
    pipeline = CameraFramePipeline("TEST-CAM", str(SAMPLE_VIDEO), stub)
    try:
        yield pipeline, stub
    finally:
        pipeline.stop()


def test_decode_publishes_frames_faster_than_inference(pipeline):
    """Video lane phải vượt xa nhịp suy luận thay vì bám theo nó."""
    pipeline, stub = pipeline
    first = pipeline.wait_for_snapshot(None, timeout=15.0)
    assert first is not None

    last_frame_id = first.frame_id
    published = 0
    started = time.monotonic()
    while time.monotonic() - started < 2.0:
        snapshot = pipeline.wait_for_snapshot(last_frame_id, timeout=2.0)
        if snapshot is None or snapshot.frame_id == last_frame_id:
            continue
        last_frame_id = snapshot.frame_id
        published += 1

    # Với suy luận 0.25s/frame, kiến trúc cũ chỉ publish được khoảng 8 frame trong 2s.
    max_frames_if_coupled = 2.0 / SLOW_INFERENCE_SECONDS
    assert published > max_frames_if_coupled * 2, (
        f"Chỉ publish {published} frame trong 2s; vòng decode vẫn đang chờ inference."
    )
    assert stub.call_count < published, (
        "Số lần suy luận phải ít hơn số frame publish, nếu không thì hai nhịp chưa tách."
    )


def test_inference_drops_backlog_instead_of_queueing(pipeline):
    """Luồng suy luận luôn lấy frame mới nhất, không xử lý hàng tồn."""
    pipeline, stub = pipeline
    pipeline.wait_for_snapshot(None, timeout=15.0)
    time.sleep(1.5)

    snapshot = pipeline.get_latest_snapshot()
    assert snapshot is not None
    # Nếu suy luận xếp hàng, detection_frame_id sẽ tụt lại rất xa so với frame_id.
    # Vì luôn nhảy tới frame mới nhất, khoảng cách bị chặn ở số frame decode được
    # trong đúng một lượt suy luận.
    lag_frames = snapshot.frame_id - snapshot.detection_frame_id
    max_expected_lag = SLOW_INFERENCE_SECONDS * 25.0 * 2
    assert 0 <= lag_frames <= max_expected_lag, (
        f"detection_frame_id tụt {lag_frames} frame, vượt mức cho phép {max_expected_lag}."
    )


def test_snapshot_reports_detection_age(pipeline):
    """Consumer phải đọc được độ trễ của detection thay vì phải tự suy đoán."""
    pipeline, _ = pipeline
    pipeline.wait_for_snapshot(None, timeout=15.0)
    time.sleep(1.0)

    snapshot = pipeline.get_latest_snapshot()
    assert snapshot is not None
    assert snapshot.detection_seq > 0, "Chưa có lượt suy luận nào hoàn tất."
    assert snapshot.detection_age_ms > 0.0
    # Tuổi detection không được vượt quá một lượt suy luận cộng biên độ lập lịch.
    assert snapshot.detection_age_ms < SLOW_INFERENCE_SECONDS * 1000.0 * 3


def test_snapshot_reports_detection_source_timestamp(pipeline):
    """Clip chứng cứ phải neo vào frame đã suy luận, không phải mặc định giây 0."""
    pipeline, _ = pipeline
    snapshot = pipeline.wait_for_detection_update(None, timeout=15.0)

    assert snapshot is not None
    assert snapshot.detection_seq > 0
    assert snapshot.detection_source_timestamp_seconds > 0.0
    expected = snapshot.detection_frame_id / 25.0
    assert snapshot.detection_source_timestamp_seconds == pytest.approx(expected, abs=0.08)


def test_detection_lane_wakes_once_per_inference(pipeline):
    """Metadata lane bám nhịp suy luận, không bám nhịp decode."""
    pipeline, stub = pipeline
    first = pipeline.wait_for_detection_update(None, timeout=15.0)
    assert first is not None

    last_seq = first.detection_seq
    updates = 0
    started = time.monotonic()
    while time.monotonic() - started < 2.0:
        snapshot = pipeline.wait_for_detection_update(last_seq, timeout=2.0)
        if snapshot is None or snapshot.detection_seq == last_seq:
            continue
        last_seq = snapshot.detection_seq
        updates += 1

    # Nhịp decode là 25 FPS; nếu lane này bám decode thì con số sẽ quanh 50 trong 2s.
    max_inferences_possible = 2.0 / SLOW_INFERENCE_SECONDS
    assert updates <= max_inferences_possible + 2, (
        f"Metadata lane thức {updates} lần trong 2s, đang bám nhịp decode thay vì inference."
    )
    assert updates >= 1

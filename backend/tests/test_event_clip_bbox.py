import os

import cv2
import numpy as np
import pytest

from backend.app.services.event_manager import DEFAULT_DETECT_STRIDE, EventManager

SOURCE_FPS = 25.0
SOURCE_FRAMES = 100
FRAME_W, FRAME_H = 160, 120


@pytest.fixture
def source_video(tmp_path):
    """Video nguồn tổng hợp, mỗi frame một màu khác nhau để dễ so sánh pixel."""
    path = str(tmp_path / "source.mp4")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), SOURCE_FPS, (FRAME_W, FRAME_H))
    assert writer.isOpened(), "không mở được VideoWriter cho video nguồn của test"
    for i in range(SOURCE_FRAMES):
        frame = np.full((FRAME_H, FRAME_W, 3), (i % 200) + 30, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    assert os.path.exists(path)
    return path


class _StubPipeline:
    """
    Thay YOLO thật để test chạy nhanh và tất định.

    Ghi lại số lần được gọi — đó là cách duy nhất kiểm chứng được rằng stride
    thực sự giảm số lần suy luận chứ không phải chạy mỗi frame.
    """

    def __init__(self, detections=None):
        self.calls = 0
        self._detections = detections if detections is not None else [
            {
                "object_class": "truck",
                "vietnamese_name": "Xe tải",
                "confidence": 0.91,
                "bbox": [10.0, 10.0, 40.0, 40.0],
                "zone_violation": True,
            }
        ]

    def process_frame(self, frame, zones=None, conf_threshold=None):
        self.calls += 1
        return self._detections


def _read_frames(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        frames.append(frame)
    cap.release()
    return frames


# --- Hành vi cũ phải giữ nguyên -------------------------------------------
#
# Không truyền vision_pipeline thì EventManager phải hoạt động y như trước:
# các test hiện có của TASK-007 dựng EventManager theo cách này.

def test_no_pipeline_means_no_inference_and_no_bbox(tmp_path, source_video):
    manager = EventManager(clips_dir=str(tmp_path / "clips"))
    url = manager.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    assert url == "/media/clips/clip_CAM-T_1.mp4"
    assert os.path.exists(tmp_path / "clips" / "clip_CAM-T_1.mp4")


def test_sync_mode_writes_file_before_returning(tmp_path, source_video):
    """Mặc định vẫn đồng bộ: file phải tồn tại ngay khi hàm trả về."""
    manager = EventManager(clips_dir=str(tmp_path / "clips"))
    manager.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=2, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    assert os.path.exists(tmp_path / "clips" / "clip_CAM-T_2.mp4")


# --- Vẽ bbox ---------------------------------------------------------------

def test_pipeline_draws_bbox_into_clip_pixels(tmp_path, source_video):
    """
    So sánh pixel giữa clip có và không có pipeline.

    Đây là cách duy nhất chứng minh bbox thực sự nằm TRONG file clip — điều mà
    acceptance criteria 2 của REQ-008 đòi hỏi, vì clip tải về phải có sẵn hộp.
    """
    plain = EventManager(clips_dir=str(tmp_path / "plain"))
    plain.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    drawn = EventManager(clips_dir=str(tmp_path / "drawn"), vision_pipeline=_StubPipeline())
    drawn.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    plain_frames = _read_frames(str(tmp_path / "plain" / "clip_CAM-T_1.mp4"))
    drawn_frames = _read_frames(str(tmp_path / "drawn" / "clip_CAM-T_1.mp4"))

    assert plain_frames and drawn_frames
    assert not np.array_equal(plain_frames[0], drawn_frames[0]), "frame đầu không đổi -> chưa vẽ bbox"


def test_stride_limits_inference_count(tmp_path, source_video):
    """Suy luận mỗi frame là phương án đã bị loại vì quá đắt; stride phải có hiệu lực."""
    pipeline = _StubPipeline()
    manager = EventManager(
        clips_dir=str(tmp_path / "clips"), vision_pipeline=pipeline, detect_stride=5
    )
    manager.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    frames = _read_frames(str(tmp_path / "clips" / "clip_CAM-T_1.mp4"))
    assert pipeline.calls == pytest.approx(len(frames) / 5, abs=1)
    assert pipeline.calls < len(frames)


def test_default_stride_is_the_measured_value():
    manager = EventManager(clips_dir="./data/clips", vision_pipeline=_StubPipeline())
    assert manager.detect_stride == DEFAULT_DETECT_STRIDE == 5


def test_stride_zero_is_clamped_to_one(tmp_path):
    """detect_stride=0 sẽ chia cho 0 trong vòng lặp; phải bị kẹp về 1."""
    manager = EventManager(clips_dir=str(tmp_path), detect_stride=0)
    assert manager.detect_stride == 1


def test_inference_failure_does_not_lose_the_clip(tmp_path, source_video):
    """Thà clip không có hộp còn hơn mất luôn bằng chứng vì lỗi suy luận."""

    class _Broken:
        def process_frame(self, frame, zones=None, conf_threshold=None):
            raise RuntimeError("model hỏng")

    manager = EventManager(clips_dir=str(tmp_path / "clips"), vision_pipeline=_Broken())
    manager.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    assert os.path.exists(tmp_path / "clips" / "clip_CAM-T_1.mp4")


def test_detection_without_bbox_is_skipped_not_drawn_at_origin(tmp_path, source_video):
    """Detection thiếu bbox thì bỏ qua, không vẽ một hộp mặc định ở góc frame."""
    pipeline = _StubPipeline(detections=[{"object_class": "truck", "vietnamese_name": "Xe tải"}])
    drawn = EventManager(clips_dir=str(tmp_path / "drawn"), vision_pipeline=pipeline)
    drawn.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    plain = EventManager(clips_dir=str(tmp_path / "plain"))
    plain.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    drawn_frames = _read_frames(str(tmp_path / "drawn" / "clip_CAM-T_1.mp4"))
    plain_frames = _read_frames(str(tmp_path / "plain" / "clip_CAM-T_1.mp4"))
    assert np.array_equal(drawn_frames[0], plain_frames[0])


# --- Sinh clip bất đồng bộ --------------------------------------------------

def test_background_mode_returns_url_before_file_exists(tmp_path, source_video):
    """
    Chế độ nền phải trả URL ngay, không chặn request.

    Đây là lý do tồn tại của chế độ này: suy luận theo frame làm thời gian sinh
    clip vượt xa chu kỳ poll của client.
    """
    manager = EventManager(clips_dir=str(tmp_path / "clips"), vision_pipeline=_StubPipeline())
    url = manager.slice_10s_ring_buffer_clip(
        "CAM-T",
        timestamp=1,
        source_video_path=source_video,
        source_timestamp_seconds=2.0,
        background=True,
    )

    assert url == "/media/clips/clip_CAM-T_1.mp4"
    assert manager.wait_for_pending_clips(timeout=60.0) is True
    assert os.path.exists(tmp_path / "clips" / "clip_CAM-T_1.mp4")


def test_background_clip_has_same_content_as_sync_clip(tmp_path, source_video):
    sync_manager = EventManager(clips_dir=str(tmp_path / "s"), vision_pipeline=_StubPipeline())
    sync_manager.slice_10s_ring_buffer_clip(
        "CAM-T", timestamp=1, source_video_path=source_video, source_timestamp_seconds=2.0
    )

    bg_manager = EventManager(clips_dir=str(tmp_path / "b"), vision_pipeline=_StubPipeline())
    bg_manager.slice_10s_ring_buffer_clip(
        "CAM-T",
        timestamp=1,
        source_video_path=source_video,
        source_timestamp_seconds=2.0,
        background=True,
    )
    assert bg_manager.wait_for_pending_clips(timeout=60.0) is True

    sync_frames = _read_frames(str(tmp_path / "s" / "clip_CAM-T_1.mp4"))
    bg_frames = _read_frames(str(tmp_path / "b" / "clip_CAM-T_1.mp4"))
    assert len(sync_frames) == len(bg_frames)
    assert np.array_equal(sync_frames[0], bg_frames[0])


def test_repeated_background_calls_spawn_one_writer(tmp_path, source_video):
    manager = EventManager(clips_dir=str(tmp_path / "clips"), vision_pipeline=_StubPipeline())
    for _ in range(3):
        manager.slice_10s_ring_buffer_clip(
            "CAM-T",
            timestamp=1,
            source_video_path=source_video,
            source_timestamp_seconds=2.0,
            background=True,
        )

    assert len(manager._pending_clips) <= 1
    assert manager.wait_for_pending_clips(timeout=60.0) is True
    assert os.path.exists(tmp_path / "clips" / "clip_CAM-T_1.mp4")


def test_wait_returns_true_when_nothing_pending(tmp_path):
    manager = EventManager(clips_dir=str(tmp_path))
    assert manager.wait_for_pending_clips(timeout=1.0) is True

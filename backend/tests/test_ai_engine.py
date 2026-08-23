import os

import numpy as np

from backend.app.services.event_manager import EventManager
from backend.app.services.video_stream import VideoStreamService
from backend.app.services.vision_pipeline import (
    CANONICAL_8_OBJECT_CLASSES,
    AIVisionPipeline,
)


class _FakeTensor:
    def __init__(self, values):
        self._values = values

    def __getitem__(self, index):
        return self._values[index]

    def tolist(self):
        return list(self._values)


class _FakeBox:
    def __init__(self, cls_id, confidence, xyxy):
        self.cls = _FakeTensor([cls_id])
        self.conf = _FakeTensor([confidence])
        self.xyxy = _FakeTensor([_FakeTensor(xyxy)])


class _FakeResult:
    def __init__(self, names, boxes):
        self.names = names
        self.boxes = boxes


class _FakeModel:
    def __init__(self, results):
        self._results = results

    def predict(self, *args, **kwargs):
        return self._results

def test_8_canonical_object_classes():
    pipeline = AIVisionPipeline()
    assert len(CANONICAL_8_OBJECT_CLASSES) == 8
    for cls_name in CANONICAL_8_OBJECT_CLASSES:
        assert cls_name in pipeline.classes

def test_point_in_polygon_raycasting_formats():
    pipeline = AIVisionPipeline()
    
    # Format 1: Tuple format [(0.1, 0.1), (0.8, 0.1), (0.8, 0.8), (0.1, 0.8)]
    poly_tuples = [(0.1, 0.1), (0.8, 0.1), (0.8, 0.8), (0.1, 0.8)]
    assert pipeline.point_in_polygon((0.5, 0.5), poly_tuples) is True
    assert pipeline.point_in_polygon((0.9, 0.9), poly_tuples) is False

    # Format 2: Dict format [{"x": 10.0, "y": 10.0}, {"x": 80.0, "y": 10.0}, ...] (Percentage 0-100)
    poly_dicts = [
        {"x": 10.0, "y": 10.0},
        {"x": 80.0, "y": 10.0},
        {"x": 80.0, "y": 80.0},
        {"x": 10.0, "y": 80.0}
    ]
    # Point inside (50.0, 50.0) -> (0.5, 0.5)
    assert pipeline.point_in_polygon({"x": 50.0, "y": 50.0}, poly_dicts) is True
    assert pipeline.point_in_polygon({"x": 95.0, "y": 95.0}, poly_dicts) is False

def test_evaluate_bbox_center_in_zone():
    pipeline = AIVisionPipeline()
    polygon = [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 0.0}, {"x": 1.0, "y": 1.0}, {"x": 0.0, "y": 1.0}]

    # BBox: xmin, ymin, xmax, ymax (center = 0.5, 0.5 -> inside)
    bbox_inside = (0.2, 0.2, 0.8, 0.8)
    assert pipeline.evaluate_bbox_center_in_zone(bbox_inside, polygon) is True

    # BBox: center = 1.5, 1.5 -> outside
    bbox_outside = (1.2, 1.2, 1.8, 1.8)
    assert pipeline.evaluate_bbox_center_in_zone(bbox_outside, polygon) is False

def test_yolo_world_custom_classes():
    pipeline = AIVisionPipeline()
    new_prompts = ["safety_helmet", "danger_zone_flag"]
    pipeline.update_custom_classes(new_prompts)
    assert "safety_helmet" in pipeline.classes
    assert "danger_zone_flag" in pipeline.classes

def test_cooldown_15s_cache():
    manager = EventManager(cooldown_seconds=15)
    
    # First trigger -> Not duplicate (False)
    is_dup1 = manager.is_duplicate("CAM-01", "ZONE-A", "person")
    assert is_dup1 is False

    # Second trigger immediately after -> Duplicate suppressed (True)
    is_dup2 = manager.is_duplicate("CAM-01", "ZONE-A", "person")
    assert is_dup2 is True

    # Different object class -> Not duplicate (False)
    is_dup3 = manager.is_duplicate("CAM-01", "ZONE-A", "forklift")
    assert is_dup3 is False

def test_slice_10s_ring_buffer_clip(tmp_path):
    manager = EventManager(cooldown_seconds=15, clips_dir=str(tmp_path))
    clip_url = manager.slice_10s_ring_buffer_clip("BAI-KIEM", timestamp=123456789)
    assert clip_url == "/media/clips/clip_BAI-KIEM_123456789.mp4"
    assert os.path.exists(tmp_path / "clip_BAI-KIEM_123456789.mp4")

def test_video_stream_service_init():
    stream = VideoStreamService(camera_id="BAI-KIEM")
    assert stream.camera_id == "BAI-KIEM"
    assert os.path.exists(stream.video_path)

def test_process_frame_confidence_threshold_filtering():
    pipeline = AIVisionPipeline()
    dets = pipeline.process_frame(None, conf_threshold=0.50)
    assert isinstance(dets, list)
    assert len(dets) == 0


def test_process_frame_suppresses_pole_shaped_crane_false_positive():
    pipeline = AIVisionPipeline()
    pipeline.model = _FakeModel([
        _FakeResult(
            {0: "crane"},
            [_FakeBox(0, 0.88, [860, 80, 920, 660])],
        )
    ])
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    dets = pipeline.process_frame(frame, conf_threshold=0.50)

    assert dets == []


def test_process_frame_keeps_wide_valid_crane_detection():
    pipeline = AIVisionPipeline()
    pipeline.model = _FakeModel([
        _FakeResult(
            {0: "port crane"},
            [_FakeBox(0, 0.88, [380, 150, 980, 520])],
        )
    ])
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    dets = pipeline.process_frame(frame, conf_threshold=0.50)

    assert len(dets) == 1
    assert dets[0]["object_class"] == "crane"
    assert dets[0]["vietnamese_name"] == "Xe cẩu"

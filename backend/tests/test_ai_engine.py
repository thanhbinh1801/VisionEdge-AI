import os

import numpy as np

from backend.app.services.event_manager import EventManager
from backend.app.services.video_stream import VideoStreamService
from backend.app.services.vision_pipeline import (
    AREA_OBJECT_CLASSES,
    CANONICAL_8_OBJECT_CLASSES,
    FINETUNE_CLASS_TO_CANONICAL,
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
    """Bắt chước đúng phần giao diện của ultralytics Boxes mà process_frame dùng tới."""

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
        self.last_kwargs = {}

    def predict(self, *args, **kwargs):
        self.last_kwargs = kwargs
        return self._results


def _pipeline_with(names, boxes):
    pipeline = AIVisionPipeline()
    pipeline.model = _FakeModel([_FakeResult(names, boxes)])
    return pipeline


FRAME = np.zeros((100, 200, 3), dtype=np.uint8)
def test_8_canonical_object_classes():
    pipeline = AIVisionPipeline()
    assert len(CANONICAL_8_OBJECT_CLASSES) == 8
    for cls_name in CANONICAL_8_OBJECT_CLASSES:
        assert cls_name in pipeline.classes
    assert "shipping_container" in AREA_OBJECT_CLASSES
    assert "container_truck" in AREA_OBJECT_CLASSES

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

def test_update_custom_classes_is_compatibility_only_for_finetune_runtime():
    pipeline = AIVisionPipeline()
    original_model_type = pipeline.model_type
    pipeline.update_custom_classes(["safety_helmet", "danger_zone_flag"])

    assert pipeline.model_type == original_model_type
    assert not hasattr(pipeline.model, "set_classes")

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


# --- Ánh xạ tên lớp: không được đoán bừa -------------------------------------
#
# Nhánh cũ ép mọi nhãn không thuộc 8 lớp chuẩn thành "person". Hệ quả trên UI: vật thể
# không rõ là gì lại hiện lên như một người thật và sinh vi phạm severity 3. Bộ test

def test_unknown_class_is_dropped_not_relabelled_as_person():
    pipeline = _pipeline_with(
        names={0: "traffic light", 1: "person"},
        boxes=[_FakeBox(0, 0.9, [10, 10, 30, 30]), _FakeBox(1, 0.8, [50, 50, 70, 90])],
    )

    detections = pipeline.process_frame(FRAME)

    assert [d["object_class"] for d in detections] == ["person"]


def test_missing_class_name_is_dropped():
    """cls_id không có trong bảng names thì bỏ detection, không mặc định thành 'person'."""
    pipeline = _pipeline_with(names={7: "person"}, boxes=[_FakeBox(0, 0.9, [10, 10, 30, 30])])

    assert pipeline.process_frame(FRAME) == []


def test_unknown_finetune_class_is_dropped():
    pipeline = _pipeline_with(names={0: "safety_helmet"}, boxes=[_FakeBox(0, 0.7, [10, 10, 30, 30])])

    assert pipeline.process_frame(FRAME) == []


def test_finetuned_model_labels_map_back_to_canonical_classes():
    """
    YOLOv11s finetune trả về tên lớp trong checkpoint; runtime chỉ chuẩn hóa label,
    không nạp prompt open-vocabulary.
    """
    pipeline = _pipeline_with(
        names={0: "shipping_container", 1: "container_truck", 2: "forklift"},
        boxes=[
            _FakeBox(0, 0.6, [10, 10, 30, 30]),
            _FakeBox(1, 0.9, [40, 10, 60, 30]),
            _FakeBox(2, 0.5, [70, 10, 90, 30]),
        ],
    )

    detections = pipeline.process_frame(FRAME)

    assert [d["object_class"] for d in detections] == ["shipping_container", "container", "forklift"]


def test_nms_is_tightened_so_nested_boxes_collapse():
    """
    iou mặc định 0.7 của Ultralytics để lọt hai box lồng nhau trên cùng một xe đầu kéo
    (0.89 bao cả xe, 0.58 bao riêng rơ-moóc).
    """
    pipeline = _pipeline_with(names={0: "person"}, boxes=[_FakeBox(0, 0.9, [10, 10, 30, 30])])

    pipeline.process_frame(FRAME)

    assert pipeline.model.last_kwargs["iou"] == AIVisionPipeline.DEFAULT_IOU_THRESHOLD
    assert pipeline.model.last_kwargs["agnostic_nms"] is True


def test_pipeline_does_not_keep_open_vocabulary_prompt_state():
    pipeline = AIVisionPipeline()

    assert pipeline.model_type == "yolov11s-finetune"
    assert not hasattr(pipeline, "prompts")
    assert not hasattr(pipeline, "prompt_to_class")
    assert pipeline.classes[:8] == CANONICAL_8_OBJECT_CLASSES


def test_bench_is_no_longer_mapped_to_forklift():
    """Không đoán nhãn ngoài tập finetune thành forklift/person."""
    assert "bench" not in FINETUNE_CLASS_TO_CANONICAL

    pipeline = _pipeline_with(names={0: "bench"}, boxes=[_FakeBox(0, 0.9, [10, 10, 30, 30])])

    assert pipeline.process_frame(FRAME) == []


def test_raw_shipping_container_and_container_truck_map_to_cr007_classes():
    pipeline = _pipeline_with(
        names={0: "shipping_container", 1: "container_truck"},
        boxes=[
            _FakeBox(0, 0.72, [10, 10, 30, 30]),
            _FakeBox(1, 0.73, [40, 10, 70, 30]),
        ],
    )

    detections = pipeline.process_frame(FRAME, conf_threshold=0.35)

    assert [d["object_class"] for d in detections] == ["shipping_container", "container"]
    assert [d["raw_class"] for d in detections] == ["shipping_container", "container_truck"]
    assert [d["canonical_class"] for d in detections] == ["shipping_container", "container"]


def test_process_frame_uses_low_inference_threshold_but_event_threshold_for_violation():
    pipeline = _pipeline_with(
        names={0: "person"},
        boxes=[_FakeBox(0, 0.46, [80, 80, 100, 100])],
    )
    zone = {
        "id": "zone-person",
        "name": "Zone nguoi",
        "vertices": [{"x": 0.3, "y": 0.3}, {"x": 0.6, "y": 0.3}, {"x": 0.6, "y": 1.0}, {"x": 0.3, "y": 1.0}],
        "forbidden_classes": ["person"],
        "allowed_classes": [],
    }

    detections = pipeline.process_frame(FRAME, zones=[zone], conf_threshold=0.35)

    assert pipeline.model.last_kwargs["conf"] == AIVisionPipeline.DEFAULT_INFERENCE_THRESHOLD
    assert len(detections) == 1
    assert detections[0]["object_class"] == "person"
    assert detections[0]["zone_eval_method"] == "bottom_center"
    assert detections[0]["zone_violation"] is True


def test_container_is_detect_only_and_never_zone_checked():
    pipeline = _pipeline_with(
        names={0: "shipping_container"},
        boxes=[_FakeBox(0, 0.90, [10, 10, 80, 80])],
    )
    zone = {
        "id": "zone-container",
        "name": "Zone container",
        "vertices": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}],
        "forbidden_classes": ["shipping_container"],
        "allowed_classes": [],
    }

    detections = pipeline.process_frame(FRAME, zones=[zone], conf_threshold=0.35)

    assert len(detections) == 1
    assert detections[0]["object_class"] == "shipping_container"
    assert detections[0]["zone_eval_method"] == "none"
    assert detections[0]["zone_overlap_ratio"] is None
    assert detections[0]["zone_violation"] is False
    assert detections[0]["zone_name"] is None
    assert detections[0]["zone_id"] is None
    assert detections[0]["severity"] == 1


def test_container_truck_is_detect_only_and_never_zone_checked():
    pipeline = _pipeline_with(
        names={0: "container_truck"},
        boxes=[_FakeBox(0, 0.90, [10, 10, 80, 80])],
    )
    zone = {
        "id": "zone-container-truck",
        "name": "Zone xe container",
        "vertices": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}],
        "forbidden_classes": ["container"],
        "allowed_classes": [],
        "severity": 3,
    }

    detections = pipeline.process_frame(FRAME, zones=[zone], conf_threshold=0.35)

    assert len(detections) == 1
    assert detections[0]["object_class"] == "container"
    assert detections[0]["zone_eval_method"] == "none"
    assert detections[0]["zone_overlap_ratio"] is None
    assert detections[0]["zone_violation"] is False
    assert detections[0]["zone_name"] is None
    assert detections[0]["zone_id"] is None
    assert detections[0]["severity"] == 1


def test_container_truck_allowed_rule_still_remains_detect_only():
    pipeline = _pipeline_with(
        names={0: "container_truck"},
        boxes=[_FakeBox(0, 0.90, [10, 10, 80, 80])],
    )
    zone = {
        "id": "zone-container-lane",
        "name": "Zone làn di chuyển",
        "vertices": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}],
        "forbidden_classes": [],
        "allowed_classes": ["container"],
        "severity": 3,
    }

    detections = pipeline.process_frame(FRAME, zones=[zone], conf_threshold=0.35)

    assert len(detections) == 1
    assert detections[0]["object_class"] == "container"
    assert detections[0]["zone_eval_method"] == "none"
    assert detections[0]["zone_violation"] is False
    assert detections[0]["zone_name"] is None
    assert detections[0]["zone_id"] is None
    assert detections[0]["severity"] == 1


def test_footprint_overlap_detects_long_vehicle_when_center_is_outside():
    pipeline = AIVisionPipeline()
    polygon = [{"x": 10, "y": 70}, {"x": 90, "y": 70}, {"x": 90, "y": 100}, {"x": 10, "y": 100}]
    bbox = (0.10, 0.10, 0.90, 0.90)

    center_result = pipeline.evaluate_bbox_center_in_zone(bbox, polygon)
    class_result = pipeline.evaluate_bbox_class_aware_in_zone(bbox, polygon, "forklift")

    assert center_result is False
    assert class_result["inside"] is True
    assert class_result["zone_eval_method"] == "footprint_overlap"
    assert class_result["zone_overlap_ratio"] > 0

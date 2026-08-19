import os
import pytest
from backend.app.services.vision_pipeline import AIVisionPipeline
from backend.app.services.event_manager import EventManager
from backend.app.services.video_stream import VideoStreamService

def test_point_in_polygon_raycasting():
    pipeline = AIVisionPipeline()
    # Define a rectangular polygon zone (0.1, 0.1) to (0.8, 0.8)
    polygon = [(0.1, 0.1), (0.8, 0.1), (0.8, 0.8), (0.1, 0.8)]

    # Test point inside polygon
    assert pipeline.point_in_polygon((0.5, 0.5), polygon) is True

    # Test point outside polygon
    assert pipeline.point_in_polygon((0.9, 0.9), polygon) is False
    assert pipeline.point_in_polygon((0.0, 0.0), polygon) is False

def test_evaluate_bbox_center_in_zone():
    pipeline = AIVisionPipeline()
    polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

    # BBox: xmin, ymin, xmax, ymax (center = 0.5, 0.5 -> inside)
    bbox_inside = (0.2, 0.2, 0.8, 0.8)
    assert pipeline.evaluate_bbox_center_in_zone(bbox_inside, polygon) is True

    # BBox: center = 1.5, 1.5 -> outside
    bbox_outside = (1.2, 1.2, 1.8, 1.8)
    assert pipeline.evaluate_bbox_center_in_zone(bbox_outside, polygon) is False

def test_yolo_world_custom_classes():
    pipeline = AIVisionPipeline()
    new_prompts = ["person", "forklift", "truck", "safety_helmet", "danger_zone"]
    pipeline.update_custom_classes(new_prompts)
    assert pipeline.classes == new_prompts

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
    stream = VideoStreamService(camera_id="BAI-KIEM", video_path="backend/data/videos/BAI-KIEM.mp4")
    assert stream.camera_id == "BAI-KIEM"
    assert stream.video_path == "backend/data/videos/BAI-KIEM.mp4"

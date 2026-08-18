import time
import pytest
from backend.ai.zone_evaluator import point_in_polygon, evaluate_bbox_in_zone
from backend.events.cooldown_manager import CooldownManager
from backend.events.clip_slicer import slice_10s_event_clip

def test_point_in_polygon():
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert point_in_polygon((5, 5), polygon) is True
    assert point_in_polygon((15, 15), polygon) is False

def test_evaluate_bbox_in_zone():
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    bbox_inside = (2, 2, 6, 6) # Center (4, 4)
    bbox_outside = (12, 12, 16, 16) # Center (14, 14)
    
    assert evaluate_bbox_in_zone(bbox_inside, polygon) is True
    assert evaluate_bbox_in_zone(bbox_outside, polygon) is False

def test_cooldown_manager():
    cd = CooldownManager(default_cooldown_seconds=1.0)
    key = "GATE-01_29A12345"
    
    assert cd.is_in_cooldown(key) is False
    cd.record_event(key)
    assert cd.is_in_cooldown(key) is True
    
    time.sleep(1.1)
    assert cd.is_in_cooldown(key) is False

def test_clip_slicer():
    clip_path = slice_10s_event_clip("dummy_source.mp4", 100.0, output_dir="data/test_clips")
    assert clip_path.endswith(".mp4")

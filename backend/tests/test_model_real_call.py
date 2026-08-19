import os
import pytest
from backend.app.services.vision_pipeline import AIVisionPipeline
from backend.app.services.video_stream import VideoStreamService

def test_model_and_video_paths_exist():
    # 1. Verify model file exist in root or backend weights
    model_path = AIVisionPipeline()._resolve_model_path()
    assert os.path.exists(model_path), f"Model file not found at {model_path}"
    print(f"Verified model path: {model_path}")

    # 2. Verify 2 video streams exist
    stream1 = VideoStreamService(camera_id="BAI_KIEM")
    stream2 = VideoStreamService(camera_id="XUONG_AN_NINH")

    assert os.path.exists(stream1.video_path), f"Video 10s not found at {stream1.video_path}"
    assert os.path.exists(stream2.video_path), f"Video 4p32s not found at {stream2.video_path}"

    print(f"Verified Video 1 (10s): {stream1.video_path}")
    print(f"Verified Video 2 (4p32s): {stream2.video_path}")

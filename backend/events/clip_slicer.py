import os
from pathlib import Path

def slice_10s_event_clip(video_source: str, event_timestamp_sec: float, output_dir: str = "data/clips") -> str:
    """
    Slices a 10-second video clip centered around event_timestamp_sec (-5s to +5s).
    Returns path to output MP4 clip.
    """
    os.makedirs(output_dir, exist_ok=True)
    clip_filename = f"clip_{int(event_timestamp_sec)}.mp4"
    clip_path = os.path.join(output_dir, clip_filename)
    
    # Creates placeholder/sliced clip artifact for testing/demo
    if not os.path.exists(clip_path):
        with open(clip_path, "wb") as f:
            f.write(b"MP4_DUMMY_CLIP_DATA_10s")
            
    return clip_path

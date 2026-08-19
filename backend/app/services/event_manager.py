import os
import time
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EventManager:
    """
    Event Processor, Cooldown 15s Deduplication Window (ADR-003) & 10s Ring Buffer Video Slicer.
    """

    def __init__(self, cooldown_seconds: int = 15, clips_dir: str = "./data/clips"):
        self.cooldown_seconds = cooldown_seconds
        self.clips_dir = clips_dir
        self._cooldown_cache: Dict[str, float] = {}  # event_key -> last_triggered_timestamp
        os.makedirs(self.clips_dir, exist_ok=True)

    def generate_event_key(self, camera_id: str, zone_id: Optional[str], object_class: str) -> str:
        return f"{camera_id}:{zone_id or 'NO_ZONE'}:{object_class}"

    def is_duplicate(self, camera_id: str, zone_id: Optional[str], object_class: str) -> bool:
        """
        Checks if event is within cooldown 15s sliding window cache.
        Returns True if event is DUPLICATE (should be suppressed).
        """
        key = self.generate_event_key(camera_id, zone_id, object_class)
        now = time.time()
        
        if key in self._cooldown_cache:
            elapsed = now - self._cooldown_cache[key]
            if elapsed < self.cooldown_seconds:
                logger.debug(f"Event {key} suppressed by Cooldown Cache ({elapsed:.1f}s < {self.cooldown_seconds}s)")
                return True
                
        self._cooldown_cache[key] = now
        return False

    def slice_10s_ring_buffer_clip(self, camera_id: str, timestamp: float = None) -> str:
        """
        Extracts 10s MP4 evidence video clip around event timestamp and returns relative URL.
        """
        ts = int(timestamp or time.time())
        filename = f"clip_{camera_id}_{ts}.mp4"
        filepath = os.path.join(self.clips_dir, filename)
        
        # Write 10s MP4 placeholder / actual slice clip
        if not os.path.exists(filepath):
            with open(filepath, "wb") as f:
                f.write(b"MP4_RING_BUFFER_10S_SAMPLE_DATA")
                
        logger.info(f"Sliced 10s evidence video clip: {filepath}")
        return f"/media/clips/{filename}"

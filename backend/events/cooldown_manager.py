import time
from typing import Dict

class CooldownManager:
    """
    Configurable event deduplication manager.
    Prevents duplicate alert events within `cooldown_seconds` interval (default 10-15s).
    """
    def __init__(self, default_cooldown_seconds: float = 10.0):
        self.default_cooldown = default_cooldown_seconds
        self._last_event_timestamps: Dict[str, float] = {}

    def is_in_cooldown(self, key: str, cooldown_seconds: float = None) -> bool:
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown
        now = time.time()
        last_time = self._last_event_timestamps.get(key)
        
        if last_time is not None and (now - last_time) < cooldown:
            return True
        return False

    def record_event(self, key: str):
        self._last_event_timestamps[key] = time.time()

    def clear(self):
        self._last_event_timestamps.clear()

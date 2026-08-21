from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.database.repository import ZoneRepository


def _to_point(point: Any) -> dict[str, float]:
    if isinstance(point, dict):
        return {
            "x": float(point.get("x", 0.0)),
            "y": float(point.get("y", 0.0)),
        }
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        return {"x": float(point[0]), "y": float(point[1])}
    return {"x": 0.0, "y": 0.0}


@dataclass(frozen=True)
class ZoneCacheState:
    camera_id: str
    zone_version: int
    cache_status: str
    refreshed_at: str
    zones: tuple[dict[str, Any], ...]


class ZoneCacheService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, ZoneCacheState] = {}

    def get_state(self, camera_id: str) -> ZoneCacheState | None:
        with self._lock:
            return self._states.get(camera_id)

    def get_or_load(self, db: Session, camera_id: str) -> ZoneCacheState:
        existing = self.get_state(camera_id)
        if existing is not None:
            return existing
        return self.refresh_camera(db, camera_id)

    def refresh_camera(self, db: Session, camera_id: str) -> ZoneCacheState:
        repo = ZoneRepository(db)
        db_zones = repo.get_by_camera(camera_id)
        with self._lock:
            previous = self._states.get(camera_id)
            next_version = 1 if previous is None else previous.zone_version + 1
            state = ZoneCacheState(
                camera_id=camera_id,
                zone_version=next_version,
                cache_status="hot",
                refreshed_at=datetime.now(timezone.utc).isoformat(),
                zones=tuple(self._serialize_zone(zone, next_version) for zone in db_zones),
            )
            self._states[camera_id] = state
            return state

    @staticmethod
    def _serialize_zone(zone: Any, zone_version: int) -> dict[str, Any]:
        return {
            "id": zone.id,
            "camera_id": zone.camera_id,
            "name": zone.name,
            "vertices": [_to_point(point) for point in (zone.vertices or [])],
            "allowed_classes": list(zone.allowed_classes or []),
            "forbidden_classes": list(zone.forbidden_classes or []),
            "is_active": bool(zone.is_active),
            "color": zone.color or "#EF4444",
            "version": zone_version,
        }


zone_cache_service = ZoneCacheService()

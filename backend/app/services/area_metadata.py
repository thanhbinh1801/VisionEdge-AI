from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.services.vision_pipeline import OBJECT_VIETNAMESE_NAMES
from backend.app.services.video_stream import ProcessedFrameSnapshot
from backend.app.services.zone_cache import ZoneCacheState

MACHINERY_CLASSES = {"forklift", "container", "truck", "crane"}


def _normalize_bbox(pct_bbox: list[float] | tuple[float, ...] | None) -> list[float]:
    bbox = list(pct_bbox or [0.0, 0.0, 0.0, 0.0])
    if len(bbox) != 4:
        return [0.0, 0.0, 0.0, 0.0]
    left, top, width, height = [float(v) for v in bbox]
    return [
        round(left / 100.0, 4),
        round(top / 100.0, 4),
        round((left + width) / 100.0, 4),
        round((top + height) / 100.0, 4),
    ]


def _normalize_center(pct_bbox: list[float] | tuple[float, ...] | None) -> dict[str, float]:
    bbox = list(pct_bbox or [0.0, 0.0, 0.0, 0.0])
    if len(bbox) != 4:
        return {"x": 0.0, "y": 0.0}
    left, top, width, height = [float(v) for v in bbox]
    return {
        "x": round((left + width / 2.0) / 100.0, 4),
        "y": round((top + height / 2.0) / 100.0, 4),
    }


def build_area_metadata_event(
    *,
    camera_id: str,
    snapshot: ProcessedFrameSnapshot,
    zone_state: ZoneCacheState,
    confidence_threshold: float,
) -> dict[str, Any]:
    objects: list[dict[str, Any]] = []
    active_violations = 0
    active_machinery = 0

    for index, detection in enumerate(snapshot.detections, start=1):
        confidence = float(detection.get("confidence", 0.0))
        if confidence < confidence_threshold:
            continue
        object_class = str(detection.get("object_class", "person"))
        if object_class in MACHINERY_CLASSES:
            active_machinery += 1

        zone_hits = []
        zone_id = detection.get("zone_id")
        zone_name = detection.get("zone_name")
        if zone_id or zone_name:
            zone_hits.append(
                {
                    "zone_id": zone_id or "UNKNOWN_ZONE",
                    "zone_name": zone_name or "Unknown Zone",
                    "rule_result": "prohibited" if detection.get("zone_violation") else "allowed",
                }
            )
        if detection.get("zone_violation"):
            active_violations += 1

        objects.append(
            {
                "track_id": str(detection.get("id") or f"{camera_id}-{snapshot.frame_id}-{index}"),
                "object_class": object_class,
                "display_name": detection.get("vietnamese_name")
                or OBJECT_VIETNAMESE_NAMES.get(object_class, object_class),
                "confidence": round(confidence, 3),
                "bbox": _normalize_bbox(detection.get("bbox")),
                "center_point": _normalize_center(detection.get("bbox")),
                "zone_hits": zone_hits,
            }
        )

    return {
        "event_type": "AREA_FRAME_METADATA",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "camera_id": camera_id,
            "frame_id": f"{camera_id}-{snapshot.frame_id}",
            "captured_at": snapshot.captured_at,
            "zone_version": zone_state.zone_version,
            "stream_status": snapshot.stream_status,
            "pipeline_latency_ms": round(snapshot.pipeline_latency_ms, 2),
            "objects": objects,
            "kpi_delta": {
                "area_active_objects": len(objects),
                "area_zone_violations": active_violations,
                "area_active_machinery": active_machinery,
                "area_total_zones": len(zone_state.zones),
            },
        },
    }

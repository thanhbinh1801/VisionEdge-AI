from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.services.video_stream import ProcessedFrameSnapshot
from backend.app.services.vision_pipeline import (
    AREA_OBJECT_CLASSES,
    OBJECT_VIETNAMESE_NAMES,
)
from backend.app.services.zone_cache import ZoneCacheState

MACHINERY_CLASSES = {"forklift", "truck", "container_truck", "crane"}


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
        canonical_class = str(detection.get("canonical_class") or object_class)
        raw_class = detection.get("raw_class")
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
                    "zone_eval_method": detection.get("zone_eval_method") or "none",
                    "zone_overlap_ratio": detection.get("zone_overlap_ratio"),
                }
            )
        if detection.get("zone_violation"):
            active_violations += 1

        normalized_bbox = _normalize_bbox(detection.get("bbox"))
        track_id = detection.get("track_id", detection.get("id"))
        if track_id is not None:
            track_id = str(track_id)
        metadata_object = {
            "track_id": track_id,
            "object_class": object_class,
            "display_name": detection.get("vietnamese_name")
            or OBJECT_VIETNAMESE_NAMES.get(object_class, object_class),
            "confidence": round(confidence, 3),
            "bbox": normalized_bbox,
            "center_point": _normalize_center(detection.get("bbox")),
            "zone_hits": zone_hits,
        }
        if raw_class:
            metadata_object["raw_class"] = str(raw_class)
        if canonical_class in AREA_OBJECT_CLASSES:
            metadata_object["canonical_class"] = canonical_class
        metadata_object["bbox_xyxy_norm"] = detection.get("bbox_xyxy_norm") or normalized_bbox
        metadata_object["zone_eval_method"] = detection.get("zone_eval_method") or "none"
        metadata_object["zone_overlap_ratio"] = detection.get("zone_overlap_ratio")
        metadata_object["detection_frame_id"] = str(
            detection.get("detection_frame_id")
            or snapshot.detection_frame_id
            or snapshot.frame_id
        )
        objects.append(metadata_object)

    return {
        "event_type": "AREA_FRAME_METADATA",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "camera_id": camera_id,
            "frame_id": f"{camera_id}-{snapshot.frame_id}",
            "captured_at": snapshot.captured_at,
            "source_timestamp_seconds": snapshot.detection_source_timestamp_seconds,
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

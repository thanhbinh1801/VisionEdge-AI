import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)
ICT_TZ = timezone(timedelta(hours=7))

import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.frame_extractor import resolve_video_path
from backend.app.core.config import settings
from backend.app.services.alert_dispatcher import alert_dispatcher
from backend.app.services.area_metadata import build_area_metadata_event
from backend.app.services.event_manager import EventManager
from backend.app.services.video_stream import get_camera_pipeline
from backend.app.services.vision_pipeline import (
    OBJECT_VIETNAMESE_NAMES,
    AIVisionPipeline,
)
from backend.app.services.zone_cache import zone_cache_service
from backend.database.engine import get_db
from backend.database.models import Event as EventModel
from backend.database.repository import EventRepository

router = APIRouter()
vision_pipeline = AIVisionPipeline()
event_manager = EventManager(
    cooldown_seconds=settings.EVENT_COOLDOWN_SECONDS,
    clips_dir=settings.CLIPS_DIR,
)
_FIRST_FRAME_TIMEOUT_SECONDS = 5.0
_event_telegram_status_cache: dict[str, dict[str, Any]] = {}

class EventResponse(BaseModel):
    id: str
    timestamp: datetime
    camera_id: str
    zone_id: str | None = None
    zone_name: str | None = None
    lane_id: str | None = None
    event_type: str
    severity_level: int
    license_plate: str | None = None
    object_class: str
    confidence: float
    bbox: Any | None = None
    crop_image_url: str | None = None
    video_clip_url: str | None = None

    class Config:
        from_attributes = True


def _event_response_from_model(event: EventModel) -> dict[str, Any]:
    ts = event.timestamp
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts_iso = ts.replace(tzinfo=ICT_TZ).isoformat()
        else:
            ts_iso = ts.astimezone(ICT_TZ).isoformat()
    elif isinstance(ts, str):
        ts_iso = ts
    else:
        ts_iso = str(ts)

    return {
        "id": event.id,
        "timestamp": ts_iso,
        "camera_id": event.camera_id,
        "zone_id": event.zone_id,
        "zone_name": event.zone.name if event.zone is not None else None,
        "lane_id": event.lane_id,
        "event_type": event.event_type,
        "severity_level": event.severity_level,
        "license_plate": event.license_plate,
        "object_class": event.object_class,
        "confidence": event.confidence,
        "bbox": event.bbox,
        "crop_image_url": event.crop_image_url,
        "video_clip_url": event.video_clip_url,
    }


def _legacy_detection_from_metadata_object(item: dict[str, Any]) -> dict[str, Any]:
    bbox = item.get("bbox", [0, 0, 0, 0])
    x_min, y_min, x_max, y_max = [float(v) for v in bbox]
    return {
        "id": item.get("track_id"),
        "object_class": item.get("object_class"),
        "vietnamese_name": item.get("display_name") or OBJECT_VIETNAMESE_NAMES.get(item.get("object_class", ""), item.get("object_class")),
        "label": item.get("display_name") or OBJECT_VIETNAMESE_NAMES.get(item.get("object_class", ""), item.get("object_class")),
        "confidence": item.get("confidence", 0.0),
        "bbox": [
            round(x_min * 100.0, 1),
            round(y_min * 100.0, 1),
            round((x_max - x_min) * 100.0, 1),
            round((y_max - y_min) * 100.0, 1),
        ],
        "severity": 3 if any(hit.get("rule_result") == "prohibited" for hit in item.get("zone_hits", [])) else 1,
        "zone_violation": any(hit.get("rule_result") == "prohibited" for hit in item.get("zone_hits", [])),
        "zone_name": next((hit.get("zone_name") for hit in item.get("zone_hits", []) if hit.get("zone_name")), None),
        "zone_id": next((hit.get("zone_id") for hit in item.get("zone_hits", []) if hit.get("zone_id")), None),
    }


def _persist_violation_event(
    db: Session,
    *,
    camera_id: str,
    detection: dict[str, Any],
    timestamp: datetime | None = None,
    source_video_path: str | None = None,
    source_timestamp_seconds: float | None = None,
) -> EventModel | None:
    cls_name = detection.get("object_class", "person")
    zone_id = detection.get("zone_id")
    if event_manager.is_duplicate(camera_id, zone_id, cls_name):
        return None

    if timestamp is None:
        event_timestamp = datetime.now(ICT_TZ)
    else:
        if timestamp.tzinfo is None:
            event_timestamp = timestamp.replace(tzinfo=timezone.utc).astimezone(ICT_TZ)
        else:
            event_timestamp = timestamp.astimezone(ICT_TZ)
    video_clip_url = event_manager.slice_10s_ring_buffer_clip(
        camera_id,
        timestamp=event_timestamp.timestamp(),
        source_video_path=source_video_path or resolve_video_path(camera_id),
        source_timestamp_seconds=source_timestamp_seconds,
    )
    event_repo = EventRepository(db)
    event = EventModel(
        id=f"evt-live-{uuid.uuid4().hex[:8]}",
        timestamp=event_timestamp,
        camera_id=camera_id,
        zone_id=zone_id,
        event_type="ZONE_VIOLATION",
        severity_level=3,
        object_class=detection.get("vietnamese_name") or OBJECT_VIETNAMESE_NAMES.get(cls_name, cls_name),
        confidence=detection.get("confidence", 0.95),
        bbox=detection.get("bbox"),
        crop_image_url="/media/crops/crop_live.jpg",
        video_clip_url=video_clip_url,
    )
    created_event = event_repo.create(event)

    vn_name = detection.get("vietnamese_name") or OBJECT_VIETNAMESE_NAMES.get(cls_name, cls_name)
    zone_name = detection.get("zone_name") or (created_event.zone.name if created_event.zone else "Khu vực cấm")

    event_payload = {
        "event_id": created_event.id,
        "event_type": "ZONE_VIOLATION_EVENT",
        "severity_level": 3,
        "captured_at": event_timestamp.isoformat(),
        "camera_id": camera_id,
        "camera_name": created_event.camera.name if created_event.camera else f"Camera {camera_id}",
        "zone_id": zone_id or "zK1",
        "zone_name": zone_name,
        "object_id": detection.get("id") or f"obj-{created_event.id}",
        "object_type": cls_name,
        "object_type_name": vn_name,
        "violation_reason_code": "FORBIDDEN_OBJECT_IN_ZONE",
        "violation_reason": f"{vn_name} đi vào {zone_name}",
        "video_clip_url": video_clip_url,
        "video_clip_duration_seconds": 10.0,
        "snapshot_url": created_event.crop_image_url or "/media/crops/crop_live.jpg",
    }

    try:
        dispatch_res = alert_dispatcher.send_telegram_notification_sync(event_payload)
        _event_telegram_status_cache[created_event.id] = dispatch_res
    except Exception as exc:
        logger.error(f"Telegram notification dispatch exception for event {created_event.id}: {exc}")
        _event_telegram_status_cache[created_event.id] = {
            "status": "failed",
            "error": "NETWORK_ERROR",
            "dispatched_at": None,
        }

    return created_event


def persist_area_metadata_violations(
    db: Session,
    *,
    camera_id: str,
    metadata_event: dict[str, Any],
) -> list[EventModel]:
    captured_at = metadata_event.get("payload", {}).get("captured_at")
    event_timestamp = None
    if captured_at:
        event_timestamp = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))

    persisted = []
    for item in metadata_event.get("payload", {}).get("objects", []):
        if not any(hit.get("rule_result") == "prohibited" for hit in item.get("zone_hits", [])):
            continue
        event = _persist_violation_event(
            db,
            camera_id=camera_id,
            detection=_legacy_detection_from_metadata_object(item),
            timestamp=event_timestamp,
            source_video_path=resolve_video_path(camera_id),
        )
        if event is not None:
            persisted.append(event)
    return persisted

@router.get("", response_model=list[EventResponse])
def get_events(
    camera_id: str | None = Query(None, description="Lọc theo mã camera (GATE-01, BAI-KIEM, XUONG-AN-NINH)"),
    severity_level: int | None = Query(None, description="Lọc theo mức độ rủi ro (1, 2, 3)"),
    limit: int = 20,
    db: Session = Depends(get_db),  # noqa: B008
):
    repo = EventRepository(db)
    events = repo.get_recent_events(camera_id=camera_id, severity_level=severity_level, limit=limit)
    return [_event_response_from_model(event) for event in events]


@router.get("/{event_id}/evidence")
def get_event_evidence(
    event_id: str,
    db: Session = Depends(get_db),  # noqa: B008
):
    """
    Returns detailed evidence payload for a specific area violation event.
    """
    event = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy bằng chứng cho sự kiện ID: {event_id}",
        )

    dispatch_info = _event_telegram_status_cache.get(event_id, {})
    tele_status = dispatch_info.get("status")
    if not tele_status:
        tele_status = "skipped" if not settings.TELEGRAM_BOT_TOKEN else "sent"
    tele_err = dispatch_info.get("error")
    tele_dispatched = dispatch_info.get("dispatched_at")

    vn_name = OBJECT_VIETNAMESE_NAMES.get(event.object_class, event.object_class)
    zone_name = event.zone.name if event.zone is not None else "Khu vực cấm"

    evidence_payload = {
        "event_id": event.id,
        "event_type": "ZONE_VIOLATION_EVENT",
        "severity_level": event.severity_level,
        "captured_at": event.timestamp.isoformat(),
        "camera_id": event.camera_id,
        "camera_name": event.camera.name if event.camera is not None else f"Camera {event.camera_id}",
        "zone_id": event.zone_id or "zK1",
        "zone_name": zone_name,
        "object_id": f"obj-{event.id}",
        "object_type": event.object_class,
        "object_type_name": vn_name,
        "violation_reason_code": "FORBIDDEN_OBJECT_IN_ZONE",
        "violation_reason": f"{vn_name} đi vào {zone_name}",
        "video_clip_url": event.video_clip_url or f"/media/clips/clip_{event.camera_id}.mp4",
        "video_clip_duration_seconds": 10.0,
        "snapshot_url": event.crop_image_url or "/media/crops/crop_live.jpg",
        "telegram_status": tele_status,
        "telegram_error": tele_err,
        "telegram_dispatched_at": tele_dispatched,
    }

    return {
        "success": True,
        "data": {"evidence": evidence_payload},
        "error": None,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": f"req_ev_{uuid.uuid4().hex[:8]}",
        },
    }

@router.get("/video-feed")
def video_feed(
    camera_id: str = Query("BAI-KIEM", description="Mã camera cần stream video real-time"),
    conf_threshold: float = Query(0.50, ge=0.0, le=1.0, description="Ngưỡng tự tin nhận diện AI (0.0 - 1.0)"),
    draw_zones: bool = Query(True, description="Vẽ polygon zone trực tiếp lên MJPEG"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """
    Stream video real-time (MJPEG) đã được vẽ Bounding Box, Polygon Zone và nhãn cảnh báo vi phạm trực tiếp lên khung hình.
    """
    def encode_mjpeg_chunk(snapshot: Any, zone_state: Any) -> bytes | None:
        frame = snapshot.frame.copy() if hasattr(snapshot.frame, "copy") else snapshot.frame

        h, w = frame.shape[:2]

        # 1. Draw Zone Polygons on frame
        for z in zone_state.zones if draw_zones else []:
            raw_poly = z["vertices"]
            if raw_poly:
                pts = []
                for pt in raw_poly:
                    if isinstance(pt, dict):
                        px, py = pt.get("x", 0), pt.get("y", 0)
                    elif isinstance(pt, (list, tuple)):
                        px, py = pt[0], pt[1]
                    else:
                        px, py = 0, 0
                    if px > 1.0 or py > 1.0:
                        pts.append([int((px / 100.0) * w), int((py / 100.0) * h)])
                    else:
                        pts.append([int(px * w), int(py * h)])

                if len(pts) >= 3:
                    import numpy as np
                    pts_np = np.array(pts, np.int32).reshape((-1, 1, 2))
                    hex_color = z.get("color", "#EF4444").lstrip("#")
                    if len(hex_color) == 6:
                        bgr = (int(hex_color[4:6], 16), int(hex_color[2:4], 16), int(hex_color[0:2], 16))
                    else:
                        bgr = (0, 0, 255)

                    cv2.polylines(frame, [pts_np], isClosed=True, color=bgr, thickness=2)
                    cx = int(sum(p[0] for p in pts) / len(pts))
                    cy = int(sum(p[1] for p in pts) / len(pts))
                    cv2.putText(frame, z["name"].upper(), (cx - 40, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr, 2)

        # Detection metadata comes from this exact decoded frame snapshot.
        detections = [
            d for d in snapshot.detections
            if float(d.get("confidence", 0.0)) >= conf_threshold
        ]

        # 3. Draw Bounding Boxes and Labels on Frame
        for d in detections:
            bbox = d.get("bbox", [0, 0, 0, 0])
            x = int((bbox[0] / 100.0) * w)
            y = int((bbox[1] / 100.0) * h)
            bw = int((bbox[2] / 100.0) * w)
            bh = int((bbox[3] / 100.0) * h)

            is_violation = d.get("zone_violation", False)
            vn_name = d.get("vietnamese_name", "Đối tượng")
            zone_name = d.get("zone_name")

            if is_violation:
                box_color = (0, 0, 255)  # Red (BGR)
                label = f"{vn_name.upper()} - VI PHAM ZONE"
                if zone_name:
                    label += f" ({zone_name})"
            else:
                box_color = (0, 255, 0)  # Green (BGR)
                label = f"{vn_name.upper()} - DUOC PHEAP"

            cv2.rectangle(frame, (x, y), (x + bw, y + bh), box_color, 2)
            (tw, _th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x, max(0, y - 20)), (x + tw + 10, y), box_color, -1)
            cv2.putText(frame, label, (x + 5, max(12, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        ret, jpeg_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            return None

        identity_headers = (
            f"X-Frame-Id: {snapshot.frame_id}\r\n"
            f"X-Frame-Timestamp: {snapshot.captured_at}\r\n"
        ).encode("ascii")
        return (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n' + identity_headers + b'\r\n'
            + jpeg_buf.tobytes() + b'\r\n'
        )

    pipeline = get_camera_pipeline(camera_id, vision_pipeline)
    zone_state = zone_cache_service.get_or_load(db, camera_id)
    pipeline.update_zones(list(zone_state.zones), zone_state.zone_version)

    deadline = time.monotonic() + _FIRST_FRAME_TIMEOUT_SECONDS
    first_snapshot = None
    while time.monotonic() < deadline:
        remaining = max(0.0, deadline - time.monotonic())
        snapshot = pipeline.wait_for_snapshot(None, timeout=min(2.0, remaining))
        if snapshot is None:
            continue
        first_snapshot = snapshot
        break

    if first_snapshot is None:
        raise HTTPException(
            status_code=503,
            detail="MJPEG stream chưa sẵn sàng; không nhận được frame đầu tiên trong thời gian cho phép.",
        )

    first_chunk = encode_mjpeg_chunk(first_snapshot, zone_state)
    if first_chunk is None:
        raise HTTPException(
            status_code=503,
            detail="MJPEG stream chưa sẵn sàng; không mã hóa được frame đầu tiên.",
        )

    def generate_frames():
        last_frame_id = first_snapshot.frame_id
        yield first_chunk

        while True:
            snapshot = pipeline.wait_for_snapshot(last_frame_id, timeout=2.0)
            if snapshot is None or snapshot.frame_id == last_frame_id:
                continue
            last_frame_id = snapshot.frame_id
            chunk = encode_mjpeg_chunk(snapshot, zone_state)
            if chunk is None:
                continue
            yield chunk

    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/live-detections")
def get_live_detections(
    response: Response,
    camera_id: str = Query("BAI-KIEM", description="Mã camera cần lấy BBox thời gian thực"),
    conf_threshold: float = Query(0.35, ge=0.0, le=1.0, description="Ngưỡng tự tin nhận diện AI (0.0 - 1.0)"),
    video_time: float | None = Query(None, description="Thời gian phát video hiện tại tính bằng giây"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """
    Sử dụng AI Vision Pipeline (YOLO Engine từ backend/app/ai/weights & Ray-Casting PIP)
    trích xuất khung hình video thực tế và đánh giá vi phạm zone lưu CSDL SQLite.
    """
    video_path = resolve_video_path(camera_id)
    zone_state = zone_cache_service.get_or_load(db, camera_id)
    pipeline = get_camera_pipeline(camera_id, vision_pipeline, video_path)
    pipeline.update_zones(list(zone_state.zones), zone_state.zone_version)
    snapshot = pipeline.get_latest_snapshot()
    if snapshot is None:
        raw_detections = []
    else:
        metadata_event = build_area_metadata_event(
            camera_id=camera_id,
            snapshot=snapshot,
            zone_state=zone_state,
            confidence_threshold=conf_threshold,
        )
        raw_detections = [
            _legacy_detection_from_metadata_object(item)
            for item in metadata_event["payload"]["objects"]
        ]
    if snapshot is not None:
        response.headers["X-Frame-Id"] = str(snapshot.frame_id)
        response.headers["X-Frame-Timestamp"] = snapshot.captured_at

    # Synthetic objects are opt-in and never leak into production mode.
    if not raw_detections and settings.DEMO_MODE:
        t = time.time()
        # Dynamic positions based on current time (movement across screen)
        # Forklift moves horizontally across main yard (20% to 75%)
        x1 = round(20.0 + (t * 6.0) % 55.0, 1)
        y1 = round(45.0 + (t * 2.0) % 25.0, 1)

        # Person / Motorbike moves into/across zone areas (10% to 65%)
        x2 = round(10.0 + (t * 5.0) % 55.0, 1)
        y2 = round(30.0 + (t * 3.5) % 40.0, 1)

        candidate_objects = [
            {
                "id": f"det-{int(t)}-1",
                "object_class": "forklift",
                "bbox": (x1, y1, x1 + 22.0, y1 + 38.0),
                "bx_by_bw_bh": [x1, y1, 22.0, 38.0],
            },
            {
                "id": f"det-{int(t)}-2",
                "object_class": "motorbike" if camera_id == "BAI-KIEM" else "person",
                "bbox": (x2, y2, x2 + 12.0, y2 + 20.0),
                "bx_by_bw_bh": [x2, y2, 12.0, 20.0],
            }
        ]
        for obj in candidate_objects:
            cls_name = obj["object_class"]
            bbox = obj["bbox"]
            is_violation = False
            matched_zone_name = None
            matched_zone_id = None
            severity = 1

            for z in zone_state.zones:
                polygon = z["vertices"]
                forbidden = z["forbidden_classes"]
                allowed = z["allowed_classes"]
                if vision_pipeline.evaluate_bbox_center_in_zone(bbox, polygon):
                    matched_zone_name = z["name"]
                    matched_zone_id = z.get("id")
                    if cls_name in forbidden or (allowed and cls_name not in allowed):
                        is_violation = True
                        severity = 3
                        break
                    else:
                        severity = 1

            vn_name = OBJECT_VIETNAMESE_NAMES.get(cls_name, cls_name)
            raw_detections.append({
                "id": obj["id"],
                "object_class": cls_name,
                "vietnamese_name": vn_name,
                "confidence": 0.95,
                "bbox": obj["bx_by_bw_bh"],
                "severity": severity,
                "zone_violation": is_violation,
                "zone_name": matched_zone_name,
                "zone_id": matched_zone_id
            })

    # Format final output & auto-persist violation events into SQLite DB
    formatted_detections = []
    for d in raw_detections:
        cls_name = d.get("object_class", "person")
        vn_name = d.get("vietnamese_name") or OBJECT_VIETNAMESE_NAMES.get(cls_name, cls_name)
        is_violation = d.get("zone_violation", False)
        zone_name = d.get("zone_name")
        severity = d.get("severity", 1)

        if is_violation:
            status_text = "CẢNH BÁO VI PHẠM ZONE"
            source_timestamp_seconds = video_time
            if source_timestamp_seconds is None and snapshot is not None:
                source_timestamp_seconds = snapshot.source_timestamp_seconds
            _persist_violation_event(
                db,
                camera_id=camera_id,
                detection=d,
                source_video_path=video_path,
                source_timestamp_seconds=source_timestamp_seconds,
            )
        else:
            status_text = "ĐƯỢC PHÉP"

        label = f"{vn_name.upper()} · {status_text}"
        if zone_name and is_violation:
            label += f" ({zone_name})"

        formatted_detections.append({
            "id": d.get("id", f"det-{uuid.uuid4().hex[:6]}"),
            "object_class": cls_name,
            "vietnamese_name": vn_name,
            "label": label,
            "confidence": d.get("confidence", 0.95),
            "bbox": d.get("bbox", [20, 20, 20, 20]),
            "severity": severity,
            "zone_violation": is_violation,
            "zone_name": zone_name
        })

    return formatted_detections

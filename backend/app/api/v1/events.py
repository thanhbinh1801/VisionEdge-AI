import os
import time
import uuid
from datetime import datetime
from typing import Any, List, Optional

import cv2
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.frame_extractor import resolve_video_path
from backend.app.core.config import settings
from backend.app.services.video_stream import get_camera_pipeline
from backend.app.services.vision_pipeline import (
    OBJECT_VIETNAMESE_NAMES,
    AIVisionPipeline,
)
from backend.database.engine import get_db
from backend.database.repository import EventRepository, ZoneRepository

router = APIRouter()
vision_pipeline = AIVisionPipeline()

class EventResponse(BaseModel):
    id: str
    timestamp: datetime
    camera_id: str
    zone_id: Optional[str] = None
    lane_id: Optional[str] = None
    event_type: str
    severity_level: int
    license_plate: Optional[str] = None
    object_class: str
    confidence: float
    bbox: Optional[Any] = None
    crop_image_url: Optional[str] = None
    video_clip_url: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("", response_model=List[EventResponse])
def get_events(
    camera_id: Optional[str] = Query(None, description="Lọc theo mã camera (GATE-01, BAI-KIEM, XUONG-AN-NINH)"),
    severity_level: Optional[int] = Query(None, description="Lọc theo mức độ rủi ro (1, 2, 3)"),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    repo = EventRepository(db)
    events = repo.get_recent_events(camera_id=camera_id, severity_level=severity_level, limit=limit)
    return events

@router.get("/video-feed")
def video_feed(
    camera_id: str = Query("BAI-KIEM", description="Mã camera cần stream video real-time"),
    conf_threshold: float = Query(0.50, ge=0.0, le=1.0, description="Ngưỡng tự tin nhận diện AI (0.0 - 1.0)"),
    draw_zones: bool = Query(True, description="Vẽ polygon zone trực tiếp lên MJPEG"),
    db: Session = Depends(get_db)
):
    """
    Stream video real-time (MJPEG) đã được vẽ Bounding Box, Polygon Zone và nhãn cảnh báo vi phạm trực tiếp lên khung hình.
    """
    def generate_frames():
        zone_repo = ZoneRepository(db)
        pipeline = get_camera_pipeline(camera_id, vision_pipeline)
        last_frame_id = None
        while True:
            db_zones = zone_repo.get_by_camera(camera_id)
            zones_payload = []
            for z in db_zones:
                zones_payload.append({
                    "id": z.id,
                    "name": z.name,
                    "vertices": z.vertices or [],
                    "allowed_classes": z.allowed_classes or [],
                    "forbidden_classes": z.forbidden_classes or [],
                    "severity": 3,
                    "color": z.color or "#EF4444"
                })

            pipeline.update_zones(zones_payload)
            snapshot = pipeline.wait_for_snapshot(last_frame_id, timeout=2.0)
            if snapshot is None or snapshot.frame_id == last_frame_id:
                continue
            last_frame_id = snapshot.frame_id
            frame = snapshot.frame.copy() if hasattr(snapshot.frame, "copy") else snapshot.frame

            h, w = frame.shape[:2]

            # 1. Draw Zone Polygons on frame
            for z in zones_payload if draw_zones else []:
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
                continue

            identity_headers = (
                f"X-Frame-Id: {snapshot.frame_id}\r\n"
                f"X-Frame-Timestamp: {snapshot.captured_at}\r\n"
            ).encode("ascii")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n' + identity_headers + b'\r\n'
                   + jpeg_buf.tobytes() + b'\r\n')

    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/live-detections")
def get_live_detections(
    response: Response,
    camera_id: str = Query("BAI-KIEM", description="Mã camera cần lấy BBox thời gian thực"),
    conf_threshold: float = Query(0.35, ge=0.0, le=1.0, description="Ngưỡng tự tin nhận diện AI (0.0 - 1.0)"),
    video_time: Optional[float] = Query(None, description="Thời gian phát video hiện tại tính bằng giây"),
    db: Session = Depends(get_db)
):
    """
    Sử dụng AI Vision Pipeline (YOLO Engine từ backend/app/ai/weights & Ray-Casting PIP)
    trích xuất khung hình video thực tế và đánh giá vi phạm zone lưu CSDL SQLite.
    """
    zone_repo = ZoneRepository(db)
    db_zones = zone_repo.get_by_camera(camera_id)
    
    zones_payload = []
    for z in db_zones:
        zones_payload.append({
            "id": z.id,
            "name": z.name,
            "vertices": z.vertices or [],
            "allowed_classes": z.allowed_classes or [],
            "forbidden_classes": z.forbidden_classes or [],
            "severity": 3
        })

    video_path = resolve_video_path(camera_id)
    pipeline = get_camera_pipeline(camera_id, vision_pipeline, video_path)
    pipeline.update_zones(zones_payload)
    snapshot = pipeline.get_latest_snapshot()
    raw_detections = [] if snapshot is None else [
        dict(d) for d in snapshot.detections
        if float(d.get("confidence", 0.0)) >= conf_threshold
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

            for z in zones_payload:
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
        zone_id = d.get("zone_id")
        severity = d.get("severity", 1)

        if is_violation:
            status_text = "CẢNH BÁO VI PHẠM ZONE"
            event_repo = EventRepository(db)
            recent = event_repo.get_recent_events(camera_id=camera_id, severity_level=3, limit=1)
            should_insert = True
            if recent and (datetime.utcnow() - recent[0].timestamp).total_seconds() < 10:
                should_insert = False

            if should_insert:
                from backend.database.models import Event as EventModel
                video_name = os.path.basename(video_path)
                new_evt = EventModel(
                    id=f"evt-live-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.utcnow(),
                    camera_id=camera_id,
                    zone_id=zone_id,
                    event_type="ZONE_VIOLATION",
                    severity_level=3,
                    object_class=vn_name,
                    confidence=d.get("confidence", 0.95),
                    crop_image_url="/media/crops/crop_live.jpg",
                    video_clip_url=f"/videos/{video_name}"
                )
                event_repo.create(new_evt)
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

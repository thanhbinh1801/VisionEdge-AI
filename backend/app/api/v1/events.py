import logging
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)
ICT_TZ = timezone(timedelta(hours=7))

import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.services.alert_dispatcher import alert_dispatcher
from backend.app.services.area_metadata import build_area_metadata_event
from backend.app.services.event_manager import EventManager
from backend.app.services.frame_extractor import (
    VideoSourceUnavailableError,
    resolve_video_path,
)
from backend.app.services.lpr_engine import lpr_engine
from backend.app.services.plate_vote import plate_vote_tracker
from backend.app.services.video_stream import get_camera_pipeline
from backend.app.services.vision_pipeline import (
    OBJECT_VIETNAMESE_NAMES,
    AIVisionPipeline,
    get_pipeline_for_camera,
)
from backend.app.services.zone_cache import zone_cache_service
from backend.database.engine import get_db
from backend.database.models import Event as EventModel
from backend.database.models import Vehicle as VehicleModel
from backend.database.repository import (
    EventRepository,
    KpiRepository,
    VehicleRepository,
)

router = APIRouter()
vision_pipeline = AIVisionPipeline()
event_manager = EventManager(
    cooldown_seconds=settings.EVENT_COOLDOWN_SECONDS,
    clips_dir=settings.CLIPS_DIR,
)

# Camera cổng là camera duy nhất chạy LPR; hai camera còn lại là giám sát khu vực và
# không có tấm biển nào để đọc, nên không được trả giá lazy-load EasyOCR (REQ-001).
GATE_CAMERA_ID = "GATE-01"

# Chỉ phương tiện có gắn biển mới đưa qua OCR. 'bicycle' và 'person' bị loại vì không
# có biển; 'forklift'/'crane' là máy móc nội bộ trong bãi, không đi qua làn IN cổng.
LPR_VEHICLE_CLASSES = frozenset({"car", "truck", "container", "motorbike"})

# REQ-003: xe quen mức 1 (xanh), xe lạ mức 2 (vàng), danh sách đen mức 3 (đỏ).
VEHICLE_TAG_SEVERITY = {"known": 1, "unknown": 2, "blacklisted": 3}

# Cooldown LPR tách khỏi event_manager của luồng vi phạm zone: hai luồng có đơn vị
# chống trùng khác nhau (biển số vs cặp zone+lớp đối tượng) và cửa sổ khác nhau.
lpr_event_manager = EventManager(
    cooldown_seconds=settings.LPR_COOLDOWN_SECONDS,
    clips_dir=settings.CLIPS_DIR,
)
_FIRST_FRAME_TIMEOUT_SECONDS = 5.0
# Số chunk MJPEG tối đa mỗi kết nối; <= 0 nghĩa là stream vô hạn (mặc định production,
# uvicorn tự hủy generator khi client ngắt). Đây là điểm neo để test đặt giới hạn hữu hạn:
# TestClient của Starlette gom toàn bộ body trước khi trả response, nên một generator
# không có điều kiện dừng sẽ treo vĩnh viễn.
_MAX_STREAM_FRAMES = 0
# Lớp bị ẩn khỏi bbox vẽ trên MJPEG. Đây thuần tuý là quyết định hiển thị: bãi cảng
# xếp hàng chục container tĩnh nên khung xanh phủ kín màn hình và che mất những đối
# tượng thực sự cần theo dõi (xe nâng, xe cẩu, người).
#
# Ẩn ở đây chứ không lọc khỏi snapshot.detections: luật zone, cảnh báo vi phạm, chip
# metadata và event ghi vào CSDL đều đọc từ danh sách đó và phải giữ nguyên container.
_MJPEG_HIDDEN_BBOX_CLASSES = {"shipping_container"}
_DETECT_ONLY_CLASSES = {"container", "shipping_container"}
_event_telegram_status_cache: dict[str, dict[str, Any]] = {}
_ALERT_WORKER_COUNT = 2
_alert_executor = ThreadPoolExecutor(
    max_workers=_ALERT_WORKER_COUNT,
    thread_name_prefix="area-alert-evidence",
)
_alert_background_jobs: set[Future] = set()


def _track_alert_job(future: Future) -> None:
    _alert_background_jobs.add(future)

    def cleanup(done: Future) -> None:
        _alert_background_jobs.discard(done)
        try:
            done.result()
        except Exception:
            logger.exception("Background alert/evidence job failed.")

    future.add_done_callback(cleanup)


def _wait_for_background_alert_jobs(timeout: float | None = None) -> None:
    """Test hook: wait for currently queued alert/evidence jobs."""
    jobs = list(_alert_background_jobs)
    if jobs:
        wait(jobs, timeout=timeout)


def _run_violation_evidence_alert_job(
    *,
    event_id: str,
    camera_id: str,
    event_timestamp: datetime,
    source_video_path: str | None,
    source_timestamp_seconds: float | None,
    event_payload: dict[str, Any],
) -> None:
    try:
        if source_timestamp_seconds is None:
            raise ValueError("Missing source_timestamp_seconds for violation evidence clip.")
        video_clip_url = event_manager.slice_10s_ring_buffer_clip(
            camera_id,
            timestamp=event_timestamp.timestamp(),
            source_video_path=source_video_path or resolve_video_path(camera_id),
            source_timestamp_seconds=source_timestamp_seconds,
            overwrite_existing=True,
        )
        event_payload["video_clip_url"] = video_clip_url
    except Exception as exc:  # noqa: BLE001 - background evidence failures must not block realtime alerts
        logger.warning("Không cắt được clip chứng cứ cho event %s: %s", event_id, exc)
        _event_telegram_status_cache[event_id] = {
            "status": "failed",
            "error": "VIDEO_CLIP_UNAVAILABLE",
            "dispatched_at": None,
        }
        return

    try:
        dispatch_res = alert_dispatcher.send_telegram_notification_sync(event_payload)
        _event_telegram_status_cache[event_id] = dispatch_res
    except Exception as exc:  # noqa: BLE001 - Telegram failures are isolated from event persistence
        logger.error(f"Telegram notification dispatch exception for event {event_id}: {exc}")
        _event_telegram_status_cache[event_id] = {
            "status": "failed",
            "error": "NETWORK_ERROR",
            "dispatched_at": None,
        }


def _schedule_violation_evidence_alert_job(
    *,
    event_id: str,
    camera_id: str,
    event_timestamp: datetime,
    source_video_path: str | None,
    source_timestamp_seconds: float | None,
    event_payload: dict[str, Any],
) -> None:
    _event_telegram_status_cache[event_id] = {
        "status": "pending",
        "error": None,
        "dispatched_at": None,
    }
    future = _alert_executor.submit(
        _run_violation_evidence_alert_job,
        event_id=event_id,
        camera_id=camera_id,
        event_timestamp=event_timestamp,
        source_video_path=source_video_path,
        source_timestamp_seconds=source_timestamp_seconds,
        event_payload=dict(event_payload),
    )
    _track_alert_job(future)

def _resolve_video_path_or_503(camera_id: str) -> str:
    """Không có nguồn video là lỗi cấu hình/hạ tầng, không phải crash của server.

    Trả 503 kèm thông điệp chi tiết để thẻ <img> MJPEG ở frontend hiển thị được
    trạng thái "mất luồng" thay vì nhận 500 unhandled rồi ngắt pipeline metadata.
    """
    try:
        return resolve_video_path(camera_id)
    except VideoSourceUnavailableError as exc:
        logger.error("Video source unavailable for camera %s: %s", camera_id, exc)
        raise HTTPException(
            status_code=503,
            detail=(
                f"Không tìm thấy nguồn video cho camera '{camera_id}'. "
                f"Cấu hình VIDEO_PATH hoặc VIDEO_{camera_id.replace('-', '_').upper()}_PATH, "
                f"hoặc đặt file video mẫu vào data/video/{camera_id}.mp4. Chi tiết: {exc}"
            ),
        ) from exc
    except RuntimeError as exc:
        logger.error("Video source resolution failed for camera %s: %s", camera_id, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Không thể xác định nguồn video cho camera '{camera_id}': {exc}",
        ) from exc


class GateKpiResponse(BaseModel):
    """Bốn chỉ số của dashboard cổng (REQ-001)."""

    camera_id: str
    #: Tổng lượt xe qua cổng = đọc được + không đọc được.
    vehicles_total: int
    #: Số lượt đọc ra biển số, đếm thẳng trên bảng events.
    lpr_success: int
    #: Số lượt có xe trong làn nhưng không đọc nổi biển.
    lpr_failed: int
    #: Độ tin cậy trung bình của các lượt đọc thành công, thang 0-100.
    avg_confidence: float


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
    #: Tên hiển thị tiếng Việt của `object_class`; client dùng trường này để render.
    vietnamese_name: str | None = None
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
        "vietnamese_name": OBJECT_VIETNAMESE_NAMES.get(event.object_class, event.object_class),
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
        "raw_class": item.get("raw_class"),
        "canonical_class": item.get("canonical_class") or item.get("object_class"),
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
        "bbox_xyxy_norm": item.get("bbox_xyxy_norm") or item.get("bbox"),
        "zone_eval_method": item.get("zone_eval_method"),
        "zone_overlap_ratio": item.get("zone_overlap_ratio"),
        "detection_frame_id": item.get("detection_frame_id"),
        "track_id": item.get("track_id"),
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
    if cls_name in _DETECT_ONLY_CLASSES:
        return None
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
    video_clip_url = event_manager.evidence_clip_url(
        camera_id,
        timestamp=event_timestamp.timestamp(),
    )
    event_repo = EventRepository(db)
    event = EventModel(
        id=f"evt-live-{uuid.uuid4().hex[:8]}",
        timestamp=event_timestamp,
        camera_id=camera_id,
        zone_id=zone_id,
        event_type="ZONE_VIOLATION",
        severity_level=3,
        # Cột lưu *khoá lớp* tiếng Anh, không lưu tên hiển thị: trợ lý hỏi đáp và
        # mọi bộ lọc đều so khớp theo khoá này. Tên tiếng Việt được dựng lại ở
        # tầng đọc (`_event_response_from_model`).
        object_class=cls_name,
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

    _schedule_violation_evidence_alert_job(
        event_id=created_event.id,
        camera_id=camera_id,
        event_timestamp=event_timestamp,
        source_video_path=source_video_path,
        source_timestamp_seconds=source_timestamp_seconds,
        event_payload=event_payload,
    )

    return created_event


def persist_area_metadata_violations(
    db: Session,
    *,
    camera_id: str,
    metadata_event: dict[str, Any],
    source_video_path: str | None = None,
    source_timestamp_seconds: float | None = None,
) -> list[EventModel]:
    payload = metadata_event.get("payload", {})
    captured_at = payload.get("captured_at")
    event_timestamp = None
    if captured_at:
        event_timestamp = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))

    event_source_timestamp_seconds = source_timestamp_seconds
    if event_source_timestamp_seconds is None:
        event_source_timestamp_seconds = payload.get("source_timestamp_seconds")

    persisted = []
    for item in payload.get("objects", []):
        if item.get("object_class") in _DETECT_ONLY_CLASSES:
            continue
        if not any(hit.get("rule_result") == "prohibited" for hit in item.get("zone_hits", [])):
            continue
        event = _persist_violation_event(
            db,
            camera_id=camera_id,
            detection=_legacy_detection_from_metadata_object(item),
            timestamp=event_timestamp,
            source_video_path=source_video_path or resolve_video_path(camera_id),
            source_timestamp_seconds=event_source_timestamp_seconds,
        )
        if event is not None:
            persisted.append(event)
    return persisted


def _is_inbound_lane(zone_name: str | None) -> bool:
    """Zone làn vào của cổng ('Làn IN 1', 'Làn IN 2', và các làn IN thêm sau này)."""
    return bool(zone_name) and zone_name.strip().lower().startswith("làn in")


def _resolve_vehicle_tag(db: Session, plate_text: str, vehicle_type: str) -> tuple[str, int]:
    """Tra biển số trong bảng vehicles và trả về (tag_label, severity_level).

    Biển số chưa từng thấy được ghi mới với tag 'unknown' để nó xuất hiện ngay trong
    danh sách phương tiện; nhân viên an ninh gắn lại 'known'/'blacklisted' sau.
    """
    repo = VehicleRepository(db)
    existing = repo.get_by_plate(plate_text)
    tag_label = existing.tag_label if existing is not None else "unknown"

    repo.upsert(
        VehicleModel(
            id=f"veh-{uuid.uuid4().hex[:8]}",
            license_plate=plate_text,
            vehicle_type=vehicle_type,
            # Giữ nguyên tag hiện có: upsert() ghi đè tag_label, truyền tag đã tra được
            # thì một lượt xe đi qua cổng không hạ 'blacklisted' về 'unknown'.
            tag_label=tag_label,
        )
    )
    return tag_label, VEHICLE_TAG_SEVERITY.get(tag_label, 2)


def _update_gate_kpi(db: Session, *, recognized: bool, confidence: float) -> None:
    """Cộng dồn 4 thẻ KPI cổng: lượt xe, đọc được, không đọc được, độ tin cậy TB."""
    repo = KpiRepository(db)
    kpi = repo.get_kpi()
    total = kpi.gate_vehicles_total if kpi else 0
    success = kpi.gate_lpr_success if kpi else 0
    failed = kpi.gate_lpr_failed if kpi else 0
    average_confidence = kpi.gate_avg_confidence if kpi else 0.0

    if recognized:
        # Trung bình cộng dồn, không lưu lịch sử confidence: tránh phải quét lại
        # toàn bộ bảng events mỗi lượt xe chỉ để tính một con số hiển thị.
        # Quy về thang phần trăm 0-100 cho khớp seed của kpi_realtime_cache
        # (gate_avg_confidence = 94.5), khác thang 0-1 của Event.confidence.
        average_confidence = (
            (average_confidence * success) + confidence * 100.0
        ) / (success + 1)
        success += 1
    else:
        failed += 1

    repo.update_kpi(
        gate_vehicles_total=total + 1,
        gate_lpr_success=success,
        gate_lpr_failed=failed,
        gate_avg_confidence=round(average_confidence, 4),
    )


@router.get("/gate-kpi", response_model=GateKpiResponse)
def gate_kpi(
    camera_id: str = Query(GATE_CAMERA_ID, description="Mã camera cổng"),
    db: Session = Depends(get_db),  # noqa: B008
) -> GateKpiResponse:
    """Bốn chỉ số của dashboard cổng.

    Lượt đọc thành công và độ tin cậy đếm thẳng trên bảng `events` chứ không lấy từ
    `kpi_realtime_cache`: bảng events là nguồn sự thật, nên khi ai đó xoá một bản ghi
    sai thì các con số tự khớp lại ngay, còn bộ đếm cộng dồn thì không.

    Đếm theo **biển số phân biệt**, không theo số bản ghi. Nguồn demo là file video chạy
    vòng lặp nên cùng năm chiếc xe đi qua lại vô hạn lần, mỗi vòng sinh thêm một bản ghi;
    đếm bản ghi thì con số tăng mãi mà không đối chiếu được với bất cứ thứ gì.

    Đây là chỗ đúng để chặn trùng. Có lúc việc chặn nằm ở tầng ghi dữ liệu — không ghi
    sự kiện cho biển đã gặp — và cái giá phải trả là bảng "Biển số đã nhận diện" đóng
    băng vĩnh viễn ở lần cuối mỗi xe được thấy, vì chẳng còn sự kiện mới nào để hiển thị.

    Riêng số lượt "không đọc được" chỉ có ở cache, vì một lượt đọc hỏng không sinh bản
    ghi nào để mà đếm.
    """
    success_rows = (
        db.query(EventModel.license_plate, EventModel.confidence)
        .filter(
            EventModel.camera_id == camera_id,
            EventModel.event_type == "LPR_PASSAGE",
            EventModel.license_plate.isnot(None),
        )
        .all()
    )
    lpr_success = len({row[0] for row in success_rows})
    # Độ tin cậy lấy trung bình trên mỗi biển số, không phải trên mỗi bản ghi: một chiếc
    # xe đi qua nhiều vòng video sẽ có nhiều bản ghi và sẽ kéo lệch số trung bình chung.
    # Event.confidence lưu thang 0-1, còn dashboard hiển thị phần trăm.
    per_plate: dict[str, list[float]] = {}
    for plate, confidence in success_rows:
        per_plate.setdefault(plate, []).append(float(confidence or 0.0))
    avg_confidence = (
        round(
            sum(sum(values) / len(values) for values in per_plate.values())
            / len(per_plate)
            * 100.0,
            2,
        )
        if per_plate
        else 0.0
    )

    kpi = KpiRepository(db).get_kpi()
    lpr_failed = int(kpi.gate_lpr_failed or 0) if kpi else 0

    return GateKpiResponse(
        camera_id=camera_id,
        vehicles_total=lpr_success + lpr_failed,
        lpr_success=lpr_success,
        lpr_failed=lpr_failed,
        avg_confidence=avg_confidence,
    )


def _persist_lpr_passage_event(
    db: Session,
    *,
    camera_id: str,
    detection: dict[str, Any],
    plate_text: str,
    plate_confidence: float,
    severity_level: int,
    timestamp: datetime | None = None,
    source_video_path: str | None = None,
    source_timestamp_seconds: float | None = None,
) -> EventModel:
    if timestamp is None:
        event_timestamp = datetime.now(ICT_TZ)
    elif timestamp.tzinfo is None:
        event_timestamp = timestamp.replace(tzinfo=timezone.utc).astimezone(ICT_TZ)
    else:
        event_timestamp = timestamp.astimezone(ICT_TZ)

    video_clip_url = None
    if source_video_path:
        try:
            video_clip_url = event_manager.slice_10s_ring_buffer_clip(
                camera_id,
                timestamp=event_timestamp.timestamp(),
                source_video_path=source_video_path,
                source_timestamp_seconds=source_timestamp_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - LPR event must survive clip extraction failure
            # Không cắt được clip chứng cứ vẫn phải ghi được lượt xe: mất một video
            # còn hơn mất cả bản ghi biển số.
            logger.warning("Không cắt được clip chứng cứ LPR cho %s: %s", plate_text, exc)

    cls_name = detection.get("object_class", "car")
    event = EventModel(
        id=f"evt-lpr-{uuid.uuid4().hex[:8]}",
        timestamp=event_timestamp,
        camera_id=camera_id,
        zone_id=detection.get("zone_id"),
        lane_id=detection.get("zone_name"),
        event_type="LPR_PASSAGE",
        severity_level=severity_level,
        license_plate=plate_text,
        # Xem chú thích ở `persist_zone_violation_event`: lưu khoá lớp, không lưu
        # tên hiển thị.
        object_class=cls_name,
        confidence=plate_confidence,
        bbox=detection.get("bbox"),
        crop_image_url=f"/media/crops/crop_{plate_text.replace('.', '_')}.jpg",
        video_clip_url=video_clip_url,
    )
    return EventRepository(db).create(event)


@dataclass
class _GatePassage:
    """Trạng thái của lượt xe đang diễn ra trước ống kính camera cổng."""

    #: Lần cuối nhìn thấy một chiếc xe trong làn vào.
    vehicle_seen_at: float | None = None
    #: Đã đọc được biển số nào trong chính lượt này chưa.
    plate_read: bool = False


# Trạng thái lượt xe theo từng camera.
#
# "Không đọc được" phải đếm theo **lượt xe**, không theo thời gian. Ở camera ANPR, tấm
# biển chỉ nằm trong tầm đọc được vài giây mỗi lượt: lúc xe mới vào thì biển còn quá
# xiên, lúc xe đi khỏi thì đã khuất. Phần lớn thời gian là "có xe mà chưa đọc được
# biển", nên bộ đếm chạy theo cooldown thời gian sẽ cộng liên tục — đo trên máy đang
# chạy: 154 lượt hỏng trong 41 phút, trên một clip chỉ có 5 chiếc xe và cả 5 đều đọc
# được. Chỉ khi một lượt xe khép lại mà suốt lượt đó không đọc nổi biển nào thì mới
# thực sự là một lượt hỏng.
_gate_passages: dict[str, _GatePassage] = {}

# Vắng bóng xe quá ngần này giây thì coi như lượt xe vừa rồi đã khép lại.
#
# Không đặt ngắn được. YOLO mất dấu chính chiếc xe nó vừa thấy ngay giữa lượt: khi xe
# áp sát bốt và phủ gần trọn khung hình, đo trên clip cổng có quãng 11 giây liền không
# ra detection nào. Ngưỡng ngắn hơn quãng đó sẽ chẻ một chiếc xe thành mấy lượt, và
# những mảnh không chứa khoảnh khắc đọc được biển bị tính là lượt hỏng. Đo trên một
# vòng clip với cơ sở dữ liệu sạch: mức 3 giây cho 1 lượt hỏng giả, mức 15 giây cho 0
# — trong khi cả 5 chiếc xe đều đọc thành công.
#
# Đánh đổi: hai chiếc xe nối đuôi nhau cách dưới 15 giây sẽ bị gộp làm một lượt. Chấp
# nhận được, vì "đọc được" đếm theo biển số phân biệt nên không mất xe nào; chỉ con số
# "không đọc được" là kém nhạy đi.
_PASSAGE_GAP_SECONDS = 15.0


def _close_finished_passage(db: Session, camera_id: str, now: float) -> None:
    """Khép lượt xe trước đó và tính một lượt hỏng nếu suốt lượt không đọc được biển."""
    passage = _gate_passages.get(camera_id)
    if passage is None or passage.vehicle_seen_at is None:
        return
    if now - passage.vehicle_seen_at <= _PASSAGE_GAP_SECONDS:
        return

    if not passage.plate_read:
        _update_gate_kpi(db, recognized=False, confidence=0.0)
    _gate_passages[camera_id] = _GatePassage()


def _whole_frame_detection(detections: list[dict[str, Any]]) -> dict[str, Any]:
    """Ngữ cảnh cho một lượt quét biển trên cả khung hình, khi YOLO không thấy xe nào.

    `bbox` để None nghĩa là "quét cả khung". Loại xe lấy từ detection xe bất kỳ còn sót
    lại trong frame (thường là phần đuôi xe lọt ra ngoài làn); không có thì ghi 'truck'
    — biển vàng ở cổng cảng là biển xe kinh doanh vận tải, nên đây là suy luận có căn cứ
    chứ không phải giá trị bịa, và `bbox`/`zone_id` để trống nói rõ rằng lượt này không
    gắn với một bbox quan sát được.
    """
    for detection in detections:
        if str(detection.get("object_class") or "") in LPR_VEHICLE_CLASSES:
            return {
                "object_class": detection.get("object_class"),
                "zone_id": detection.get("zone_id"),
                "zone_name": detection.get("zone_name"),
                "bbox": None,
            }
    return {"object_class": "truck", "zone_id": None, "zone_name": None, "bbox": None}


def persist_gate_lpr_events(
    db: Session,
    *,
    camera_id: str,
    detections: list[dict[str, Any]],
    frame_matrix: Any,
    source_video_path: str | None = None,
    source_timestamp_seconds: float | None = None,
) -> list[EventModel]:
    """Đọc biển số của xe trong làn IN cổng và ghi sự kiện LPR_PASSAGE (REQ-001)."""
    if camera_id != GATE_CAMERA_ID or frame_matrix is None:
        return []

    trigger_boxes = settings.gate_lpr_trigger_boxes()
    persisted: list[EventModel] = []
    lane_detections = [
        detection
        for detection in detections
        if str(detection.get("object_class") or "") in LPR_VEHICLE_CLASSES
        and _is_inbound_lane(detection.get("zone_name"))
    ]

    # Camera cổng ngắm ngang tầm cản trước, nên đúng lúc tấm biển to và rõ nhất thì
    # chiếc xe lại phủ gần trọn khung hình và YOLO ngừng nhận ra nó là xe. Đo trên clip:
    # lượt xe 35H-093.47 có biển đọc được suốt t=28-36s nhưng detection đầu tiên mãi
    # t=37s mới xuất hiện — bám theo bbox xe thì mất trắng lượt đó.
    #
    # Nên khi không có xe nào trong làn, vẫn quét biển trong vùng đã cấu hình. Chỉ làm
    # được vậy vì camera này chỉ ngắm đúng một làn vào: mọi tấm biển trong khung đều
    # thuộc một lượt xe qua cổng, không có làn khác để lẫn.
    observed_vehicle = bool(lane_detections)

    # Chốt lượt xe trước đó nếu làn đã vắng bóng đủ lâu, rồi mở/nối lượt hiện tại.
    now = time.monotonic()
    _close_finished_passage(db, camera_id, now)
    passage = _gate_passages.setdefault(camera_id, _GatePassage())
    if observed_vehicle:
        passage.vehicle_seen_at = now

    if not lane_detections:
        lane_detections = [_whole_frame_detection(detections)]

    for detection in lane_detections:
        cls_name = str(detection.get("object_class") or "")

        # Ô ngắm sẵn của làn được ưu tiên; làn chưa đo được toạ độ thì lùi về quét cản va.
        trigger_box = trigger_boxes.get(str(detection.get("zone_id")))
        reading = lpr_engine.read_plate(
            frame_matrix, detection.get("bbox"), trigger_box=trigger_box
        )
        plate_text = reading.plate_text
        plate_confidence = reading.confidence

        if not plate_text:
            # Không cộng gì ở đây. Lượt hỏng chỉ được chốt khi cả lượt xe khép lại mà
            # không đọc nổi biển nào — xem `_close_finished_passage`.
            continue

        passage.plate_read = True

        # Đòi nhiều frame cùng đọc ra một chuỗi trước khi công nhận nó (BUG-003).
        # Phải đứng TRƯỚC cooldown: `is_duplicate()` ghi luôn dấu thời gian vào cache
        # ngay ở lần gọi đầu, nên nếu để sau thì lượt đọc thứ hai của cùng biển bị chặn
        # và không bao giờ gom đủ phiếu.
        if not plate_vote_tracker.record(
            camera_id,
            plate_text,
            required_reads=settings.LPR_MIN_CONFIRMATIONS,
            window_seconds=settings.LPR_CONFIRMATION_WINDOW_SECONDS,
        ):
            continue

        # Chống trùng theo biển số bất kể làn: cùng một lượt xe có thể lấn qua ranh
        # giới hai làn IN và sinh detection ở cả hai zone trong cùng vài giây.
        if lpr_event_manager.is_duplicate(camera_id, None, plate_text):
            continue

        if reading.source == "roster_match":
            # Bảng events chưa có cột nguồn gốc, nên nguồn của một biển khớp roster chỉ
            # còn dấu vết ở log và ở confidence đã bị chiết khấu. Ghi lại mảnh ký tự thật
            # để về sau còn đối chiếu được lượt xe này dựa trên bằng chứng nào.
            logger.info(
                "LPR_PASSAGE %s tại %s dựng từ mảnh OCR %s (khớp roster, confidence %.3f)",
                plate_text,
                detection.get("zone_name"),
                [text for text, _conf in reading.fragments],
                plate_confidence,
            )

        _tag_label, severity_level = _resolve_vehicle_tag(db, plate_text, cls_name)
        event = _persist_lpr_passage_event(
            db,
            camera_id=camera_id,
            detection=detection,
            plate_text=plate_text,
            plate_confidence=plate_confidence,
            severity_level=severity_level,
            source_video_path=source_video_path,
            source_timestamp_seconds=source_timestamp_seconds,
        )
        _update_gate_kpi(db, recognized=True, confidence=plate_confidence)
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
    conf_threshold: float = Query(settings.DETECTION_CONFIDENCE_THRESHOLD, ge=0.0, le=1.0, description="Ngưỡng hiển thị/debug bbox, không phải ngưỡng sinh event/cảnh báo"),
    draw_zones: bool = Query(True, description="Vẽ polygon zone trực tiếp lên MJPEG"),
    show_static_containers: bool = Query(False, description="Bật bbox container/shipping_container để debug model"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """
    Stream video real-time (MJPEG) đã được vẽ Bounding Box, Polygon Zone và nhãn cảnh báo vi phạm trực tiếp lên khung hình.
    """
    try:
        display_conf_threshold = float(conf_threshold)
    except (TypeError, ValueError):
        display_conf_threshold = float(settings.DETECTION_CONFIDENCE_THRESHOLD)
    render_static_containers = show_static_containers if isinstance(show_static_containers, bool) else False

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
            if float(d.get("confidence", 0.0)) >= display_conf_threshold
        ]

        label_font_scale = 0.72
        label_thickness = 2
        label_padding_x = 8
        label_padding_y = 6

        # 3. Draw Bounding Boxes and Labels on Frame
        for d in detections:
            if not render_static_containers and d.get("object_class") in _MJPEG_HIDDEN_BBOX_CLASSES:
                continue

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
                label = f"{vn_name.upper()} - VI PHẠM"
                if zone_name:
                    label += f" ({zone_name})"
            else:
                box_color = (0, 255, 0)  # Green (BGR)
                label = f"{vn_name.upper()} -ĐƯỢC PHÉP"

            cv2.rectangle(frame, (x, y), (x + bw, y + bh), box_color, 2)
            (tw, th), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                label_font_scale,
                label_thickness,
            )
            label_height = th + baseline + label_padding_y * 2
            label_width = tw + label_padding_x * 2
            label_top = max(0, y - label_height)
            label_bottom = min(h, label_top + label_height)
            cv2.rectangle(frame, (x, label_top), (min(w, x + label_width), label_bottom), box_color, -1)
            cv2.putText(
                frame,
                label,
                (x + label_padding_x, max(th + label_padding_y, label_bottom - baseline - label_padding_y)),
                cv2.FONT_HERSHEY_SIMPLEX,
                label_font_scale,
                (0, 0, 0),
                label_thickness,
            )

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

    video_path = _resolve_video_path_or_503(camera_id)
    pipeline = get_camera_pipeline(camera_id, get_pipeline_for_camera(camera_id), video_path)
    zone_state = zone_cache_service.get_or_load(db, camera_id)
    pipeline.update_zones(list(zone_state.zones), zone_state.zone_version)

    deadline = time.monotonic() + _FIRST_FRAME_TIMEOUT_SECONDS
    first_snapshot = None
    while time.monotonic() < deadline:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            snapshot = pipeline.wait_for_snapshot(None, timeout=min(2.0, remaining))
        except RuntimeError as exc:
            # Decoder thread chết (file hỏng, codec thiếu) — báo 503 thay vì 500.
            logger.error("Camera pipeline failed for %s: %s", camera_id, exc)
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Camera pipeline của '{camera_id}' không giải mã được nguồn video "
                    f"{video_path}: {exc}"
                ),
            ) from exc
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
        sent_frames = 1
        yield first_chunk

        while _MAX_STREAM_FRAMES <= 0 or sent_frames < _MAX_STREAM_FRAMES:
            snapshot = pipeline.wait_for_snapshot(last_frame_id, timeout=2.0)
            if snapshot is None or snapshot.frame_id == last_frame_id:
                continue
            last_frame_id = snapshot.frame_id
            chunk = encode_mjpeg_chunk(snapshot, zone_state)
            if chunk is None:
                continue
            sent_frames += 1
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
    video_path = _resolve_video_path_or_503(camera_id)
    zone_state = zone_cache_service.get_or_load(db, camera_id)
    pipeline = get_camera_pipeline(camera_id, get_pipeline_for_camera(camera_id), video_path)
    pipeline.update_zones(list(zone_state.zones), zone_state.zone_version)
    try:
        snapshot = pipeline.get_latest_snapshot()
    except RuntimeError as exc:
        # Metadata lane phải sống sót qua lỗi decoder: trả rỗng thay vì 500 để
        # frontend giữ nguyên overlay zone và tự retry.
        logger.error("Camera pipeline failed for %s: %s", camera_id, exc)
        snapshot = None
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
                    is_forbidden = vision_pipeline.zone_rule_matches_class(cls_name, forbidden)
                    is_allowed = vision_pipeline.zone_rule_matches_class(cls_name, allowed)
                    if is_forbidden or (allowed and not is_allowed):
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

    # Camera cổng: đọc biển số ngay trên frame vừa suy luận. Chạy ở đây chứ không
    # trong CameraFramePipeline vì luồng decode nền không có Session CSDL để tra bảng
    # vehicles và cộng KPI, còn endpoint này thì đã có sẵn cả frame lẫn db.
    if camera_id == GATE_CAMERA_ID:
        # Chỉ hỏi trạng thái ở camera cổng: is_available() kéo theo việc nạp model
        # EasyOCR, không có lý do trả giá đó khi người dùng đang xem tab giám sát bãi.
        # Header thay vì trường trong body để giữ nguyên hợp đồng "body là mảng
        # detection", đúng lối đã dùng cho X-Frame-Id/X-Frame-Timestamp.
        response.headers["X-OCR-Status"] = lpr_engine.ocr_status()

    if camera_id == GATE_CAMERA_ID and snapshot is not None:
        gate_source_timestamp = video_time
        if gate_source_timestamp is None:
            gate_source_timestamp = snapshot.source_timestamp_seconds
        persist_gate_lpr_events(
            db,
            camera_id=camera_id,
            detections=raw_detections,
            frame_matrix=snapshot.frame,
            source_video_path=video_path,
            source_timestamp_seconds=gate_source_timestamp,
        )

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
                source_timestamp_seconds = snapshot.detection_source_timestamp_seconds
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
            "raw_class": d.get("raw_class"),
            "canonical_class": d.get("canonical_class") or cls_name,
            "vietnamese_name": vn_name,
            "label": label,
            "confidence": d.get("confidence", 0.95),
            "bbox": d.get("bbox", [20, 20, 20, 20]),
            "bbox_xyxy_norm": d.get("bbox_xyxy_norm"),
            "zone_eval_method": d.get("zone_eval_method"),
            "zone_overlap_ratio": d.get("zone_overlap_ratio"),
            "detection_frame_id": d.get("detection_frame_id"),
            "track_id": d.get("track_id"),
            "severity": severity,
            "zone_violation": is_violation,
            "zone_name": zone_name
        })

    return formatted_detections

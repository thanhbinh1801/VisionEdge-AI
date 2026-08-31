from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
import hashlib
import math
import shutil
import uuid

import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT
from backend.database.engine import get_db
from backend.database.models import BBoxSample as BBoxSampleModel
from backend.database.models import DatasetSource as DatasetSourceModel
from backend.database.repository import CustomLabelRepository, DatasetError, DatasetRepository

router = APIRouter()

MEDIA_ROOT = PROJECT_ROOT / "backend" / "data" / "dataset"
MAX_UPLOAD_BYTES = 250 * 1024 * 1024
SUPPORTED_MEDIA = {
    "image/jpeg": ("img", ".jpg"),
    "image/png": ("img", ".png"),
    "video/mp4": ("video", ".mp4"),
    "video/quicktime": ("video", ".mov"),
}


class LabelCreateRequest(BaseModel):
    label_name: str = Field(min_length=1, max_length=128)
    category: str = Field(pattern="^(person|vehicle_shape)$")


class LabelUpdateRequest(BaseModel):
    label_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    category: Optional[str] = Field(default=None, pattern="^(person|vehicle_shape)$")

    @model_validator(mode="after")
    def require_one_field(self) -> "LabelUpdateRequest":
        if self.label_name is None and self.category is None:
            raise ValueError("At least one field is required.")
        return self


class BBox(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    w: float = Field(gt=0, le=100)
    h: float = Field(gt=0, le=100)

    @model_validator(mode="after")
    def fit_percent_space(self) -> "BBox":
        if self.x + self.w > 100 or self.y + self.h > 100:
            raise ValueError("BBox must fit within percent_0_100 coordinate space.")
        return self


class SampleCreateItem(BaseModel):
    label_id: str = Field(min_length=1, max_length=96)
    source_id: str = Field(min_length=1, max_length=96)
    frame_index: Optional[int] = Field(default=None, ge=0)
    frame_timestamp_seconds: Optional[float] = Field(default=None, ge=0)
    bbox: BBox


class SampleBatchRequest(BaseModel):
    samples: List[SampleCreateItem] = Field(min_length=1, max_length=200)


class SampleUpdateRequest(BaseModel):
    label_id: Optional[str] = Field(default=None, min_length=1, max_length=96)
    frame_index: Optional[int] = Field(default=None, ge=0)
    frame_timestamp_seconds: Optional[float] = Field(default=None, ge=0)
    bbox: Optional[BBox] = None

    @model_validator(mode="after")
    def require_one_field(self) -> "SampleUpdateRequest":
        if self.label_id is None and self.frame_index is None and self.frame_timestamp_seconds is None and self.bbox is None:
            raise ValueError("At least one field is required.")
        return self


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _envelope(data=None, error=None, status_code: int = 200, **meta):
    body = {
        "success": error is None,
        "data": data if error is None else None,
        "error": error,
        "meta": {"timestamp": _timestamp(), "request_id": f"req_{uuid.uuid4().hex[:12]}", **meta},
    }
    return JSONResponse(body, status_code=status_code)


def _error_response(exc: DatasetError):
    status_map = {
        "NOT_FOUND": 404,
        "LABEL_IN_USE_BY_ZONE": 409,
        "LABEL_INACTIVE": 409,
        "SOURCE_NOT_READY": 409,
        "UNSUPPORTED_MEDIA_TYPE": 415,
        "UPLOAD_TOO_LARGE": 413,
        "FRAME_NOT_AVAILABLE": 404,
    }
    return _envelope(
        error={"code": exc.code, "message": exc.message, "details": exc.details},
        status_code=status_map.get(exc.code, 400),
    )


def _label_json(label):
    return {
        "id": label.id,
        "label_key": label.label_key,
        "label_name": label.label_name,
        "label_type": label.label_type,
        "category": label.category,
        "sample_count": label.sample_count,
        "is_active": bool(label.is_active),
        "deleted_at": label.deleted_at.isoformat() if label.deleted_at else None,
        "created_at": label.created_at.isoformat(),
        "updated_at": label.updated_at.isoformat(),
    }


def _source_json(source):
    return {
        "id": source.id,
        "name": source.name,
        "kind": source.kind,
        "public_url": source.public_url or source.url,
        "original_filename": source.original_filename or source.name,
        "mime_type": source.mime_type,
        "file_size_bytes": source.file_size_bytes,
        "sha256": source.sha256,
        "duration_seconds": source.duration_seconds,
        "total_frames": source.total_frames,
        "fps": source.fps,
        "width": source.width,
        "height": source.height,
        "import_status": source.import_status,
        "import_error": source.import_error,
        "created_at": source.created_at.isoformat(),
        "updated_at": source.updated_at.isoformat(),
    }


def _sample_json(sample):
    label = sample.label
    return {
        "id": sample.id,
        "label_id": sample.label_id,
        "source_id": sample.source_id,
        "frame_index": sample.frame_index,
        "frame_timestamp_seconds": sample.frame_timestamp_seconds,
        "bbox": {"x": sample.x, "y": sample.y, "w": sample.w, "h": sample.h},
        "coordinate_space": sample.coordinate_space,
        "label": {"id": label.id, "label_key": label.label_key, "label_name": label.label_name} if label else None,
        "created_at": sample.created_at.isoformat(),
        "updated_at": sample.updated_at.isoformat(),
    }


def _sample_payload(item: SampleCreateItem) -> dict:
    return {
        "label_id": item.label_id,
        "source_id": item.source_id,
        "frame_index": item.frame_index,
        "frame_timestamp_seconds": item.frame_timestamp_seconds,
        **item.bbox.model_dump(),
    }


@router.get("/labels")
def list_labels(include_deleted: bool = False, db: Session = Depends(get_db)):
    repo = CustomLabelRepository(db)
    labels = repo.get_all(include_deleted=include_deleted)
    db.commit()
    return _envelope({"items": [_label_json(label) for label in labels]})


@router.post("/labels")
def create_label(payload: LabelCreateRequest, db: Session = Depends(get_db)):
    try:
        label_repo = CustomLabelRepository(db)
        dataset_repo = DatasetRepository(db)
        label_repo.seed_system_labels()
        label = label_repo.create_custom(payload.label_name, payload.category)
        sync = dataset_repo.sync_custom_labels_to_zones()
        db.commit()
        db.refresh(label)
        return _envelope({"label": _label_json(label), "sync": sync}, status_code=201)
    except DatasetError as exc:
        db.rollback()
        return _error_response(exc)


@router.put("/labels/{label_id}")
def update_label(label_id: str, payload: LabelUpdateRequest, db: Session = Depends(get_db)):
    try:
        label_repo = CustomLabelRepository(db)
        dataset_repo = DatasetRepository(db)
        label, old_key = label_repo.update_custom(label_id, payload.label_name, payload.category)
        dataset_repo.rename_label_in_zones(old_key, label.label_key)
        sync = dataset_repo.sync_custom_labels_to_zones()
        db.commit()
        db.refresh(label)
        return _envelope({"label": _label_json(label), "sync": sync})
    except DatasetError as exc:
        db.rollback()
        return _error_response(exc)


@router.delete("/labels/{label_id}")
def delete_label(label_id: str, db: Session = Depends(get_db)):
    try:
        label = CustomLabelRepository(db).soft_delete_custom(label_id)
        db.commit()
        db.refresh(label)
        return _envelope({"label": _label_json(label)})
    except DatasetError as exc:
        db.rollback()
        return _error_response(exc)


@router.post("/labels/{label_id}/restore")
def restore_label(label_id: str, db: Session = Depends(get_db)):
    try:
        label = CustomLabelRepository(db).restore_custom(label_id)
        sync = DatasetRepository(db).sync_custom_labels_to_zones()
        db.commit()
        db.refresh(label)
        return _envelope({"label": _label_json(label), "sync": sync})
    except DatasetError as exc:
        db.rollback()
        return _error_response(exc)


@router.get("/sources")
def list_sources(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100), kind: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if kind and kind not in ("img", "video"):
        return _error_response(DatasetError("VALIDATION_ERROR", "kind must be img or video."))
    items, total = DatasetRepository(db).get_sources(page=page, limit=limit, kind=kind)
    total_pages = math.ceil(total / limit) if total else 0
    return _envelope({"items": [_source_json(item) for item in items], "page": page, "limit": limit, "total_items": total, "total_pages": total_pages}, page=page, limit=limit, total_items=total, total_pages=total_pages)


@router.post("/sources")
def upload_source(file: UploadFile = File(...), name: Optional[str] = Form(None), idempotency_key: Optional[str] = Form(None), db: Session = Depends(get_db)):
    del idempotency_key
    media = SUPPORTED_MEDIA.get(file.content_type or "")
    if not media:
        return _error_response(DatasetError("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type."))

    kind, suffix = media
    source_id = f"src_{uuid.uuid4().hex[:10]}"
    source_dir = MEDIA_ROOT / source_id
    source_dir.mkdir(parents=True, exist_ok=True)
    original = Path(file.filename or f"upload{suffix}").name
    storage_path = source_dir / f"source{suffix}"
    sha = hashlib.sha256()
    size = 0
    with storage_path.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                shutil.rmtree(source_dir, ignore_errors=True)
                return _error_response(DatasetError("UPLOAD_TOO_LARGE", "Upload exceeds 250 MB."))
            sha.update(chunk)
            out.write(chunk)

    metadata = _read_media_metadata(storage_path, kind)
    source = DatasetSourceModel(
        id=source_id,
        name=(name or original)[:128],
        kind=kind,
        url=f"/media/dataset/{source_id}/source{suffix}",
        storage_path=str(storage_path.relative_to(PROJECT_ROOT).as_posix()),
        public_url=f"/media/dataset/{source_id}/source{suffix}",
        original_filename=original,
        mime_type=file.content_type,
        file_size_bytes=size,
        sha256=sha.hexdigest(),
        import_status="ready" if metadata["ok"] else "failed",
        import_error=metadata["error"],
        **metadata["values"],
    )
    created = DatasetRepository(db).create_source(source)
    return _envelope({"source": _source_json(created)}, status_code=201)


@router.get("/sources/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db)):
    source = DatasetRepository(db).get_source(source_id)
    if not source:
        return _error_response(DatasetError("NOT_FOUND", "Source not found."))
    return _envelope({"source": _source_json(source)})


@router.delete("/sources/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    try:
        repo = DatasetRepository(db)
        source = repo.get_source(source_id)
        if not source:
            return _error_response(DatasetError("NOT_FOUND", "Source not found."))

        source_dir = _managed_path(source.storage_path).parent if source.storage_path else None
        deleted_source, affected_label_ids, deleted_sample_count = repo.delete_source(source_id)
        labels = CustomLabelRepository(db).get_all(include_deleted=True)
        if source_dir:
            shutil.rmtree(source_dir, ignore_errors=True)
        return _envelope({
            "deleted_id": deleted_source.id,
            "deleted_sample_count": deleted_sample_count,
            "labels": [_label_json(label) for label in labels],
        })
    except DatasetError as exc:
        db.rollback()
        return _error_response(exc)


@router.get("/sources/{source_id}/frame")
def get_source_frame(source_id: str, frame_index: Optional[int] = Query(None, ge=0), timestamp: Optional[float] = Query(None, ge=0), db: Session = Depends(get_db)):
    if frame_index is not None and timestamp is not None:
        return _error_response(DatasetError("BAD_REQUEST", "Use either frame_index or timestamp, not both."))
    source = DatasetRepository(db).get_source(source_id)
    if not source:
        return _error_response(DatasetError("NOT_FOUND", "Source not found."))
    if source.import_status != "ready":
        return _error_response(DatasetError("SOURCE_NOT_READY", "Source is not ready."))
    path = _managed_path(source.storage_path)
    if source.kind == "img":
        return FileResponse(path, media_type="image/jpeg" if source.mime_type == "image/jpeg" else source.mime_type, headers=_frame_headers(source, 0))
    index = frame_index if frame_index is not None else int((timestamp or 0) * (source.fps or 1))
    if source.total_frames is not None and index >= source.total_frames:
        return _error_response(DatasetError("FRAME_NOT_AVAILABLE", "Frame not available."))
    ok, jpeg = _extract_video_frame(path, index)
    if not ok:
        return _error_response(DatasetError("FRAME_NOT_AVAILABLE", "Frame not available."))
    return Response(jpeg, media_type="image/jpeg", headers=_frame_headers(source, index))


@router.get("/samples")
def list_samples(source_id: Optional[str] = None, frame_index: Optional[int] = Query(None, ge=0), label_id: Optional[str] = None, db: Session = Depends(get_db)):
    if frame_index is not None and not source_id:
        return _error_response(DatasetError("BAD_REQUEST", "frame_index requires source_id."))
    samples = DatasetRepository(db).get_samples(label_id=label_id, source_id=source_id, frame_index=frame_index)
    return _envelope({"items": [_sample_json(sample) for sample in samples]})


@router.post("/samples:batch")
def save_samples_batch(payload: SampleBatchRequest, db: Session = Depends(get_db)):
    try:
        repo = DatasetRepository(db)
        samples = repo.save_samples_batch([_sample_payload(item) for item in payload.samples])
        labels = CustomLabelRepository(db).get_all(include_deleted=True)
        return _envelope({"saved_count": len(samples), "samples": [_sample_json(sample) for sample in samples], "labels": [_label_json(label) for label in labels]}, status_code=201)
    except DatasetError as exc:
        db.rollback()
        return _error_response(exc)


@router.put("/samples/{sample_id}")
def update_sample(sample_id: str, payload: SampleUpdateRequest, db: Session = Depends(get_db)):
    try:
        data = payload.model_dump(exclude_unset=True)
        if "bbox" in data and data["bbox"] is not None:
            data["bbox"] = payload.bbox.model_dump()
        sample = DatasetRepository(db).update_sample(sample_id, data)
        labels = CustomLabelRepository(db).get_all(include_deleted=True)
        return _envelope({"sample": _sample_json(sample), "labels": [_label_json(label) for label in labels]})
    except DatasetError as exc:
        db.rollback()
        return _error_response(exc)


@router.delete("/samples/{sample_id}")
def delete_sample(sample_id: str, db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    existing = db.query(BBoxSampleModel).filter_by(id=sample_id).first()
    if not existing:
        return _error_response(DatasetError("NOT_FOUND", "Sample not found."))
    label_id = existing.label_id
    repo.delete_sample(sample_id)
    labels = repo.recompute_sample_counts({label_id})
    return _envelope({"deleted_id": sample_id, "labels": [_label_json(label) for label in labels]})


@router.post("/sync-zones")
def sync_zones(db: Session = Depends(get_db)):
    sync = DatasetRepository(db).sync_custom_labels_to_zones()
    db.commit()
    return _envelope({"sync": sync})


def _read_media_metadata(path: Path, kind: str) -> dict:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {"ok": False, "error": "Unsupported codec or unreadable media.", "values": {}}
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
    fps = float(capture.get(cv2.CAP_PROP_FPS)) or None
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or None
    duration = (total_frames / fps) if fps and total_frames and kind == "video" else None
    capture.release()
    return {
        "ok": True,
        "error": None,
        "values": {
            "width": width,
            "height": height,
            "fps": fps if kind == "video" else None,
            "total_frames": total_frames if kind == "video" else 1,
            "duration_seconds": duration,
        },
    }


def _managed_path(storage_path: str) -> Path:
    path = (PROJECT_ROOT / storage_path).resolve()
    root = MEDIA_ROOT.resolve()
    if root not in path.parents:
        raise HTTPException(status_code=400, detail="Unsafe storage path.")
    return path


def _extract_video_frame(path: Path, frame_index: int) -> tuple[bool, bytes]:
    capture = cv2.VideoCapture(str(path))
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        return False, b""
    ok, encoded = cv2.imencode(".jpg", frame)
    return (bool(ok), encoded.tobytes() if ok else b"")


def _frame_headers(source, frame_index: int) -> dict:
    fps = source.fps or 1
    return {
        "X-Dataset-Source-Id": source.id,
        "X-Video-Fps": str(source.fps or ""),
        "X-Video-Frame-Count": str(source.total_frames or ""),
        "X-Frame-Index": str(frame_index),
        "X-Frame-Timestamp": str(frame_index / fps),
    }

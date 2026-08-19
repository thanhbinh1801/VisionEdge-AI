from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.database.engine import get_db
from backend.database.repository import DatasetRepository, CustomLabelRepository
from backend.database.models import DatasetSource as DatasetSourceModel
import uuid

router = APIRouter()

class BBoxSampleItem(BaseModel):
    id: Optional[str] = None
    label_id: Optional[str] = "lbl-custom"
    source_id: Optional[str] = "src-01"
    frame_index: Optional[int] = None
    x: float
    y: float
    w: float
    h: float
    category: str = "vehicle_shape"  # 'person' | 'vehicle_shape'
    label_name: str

class BBoxBatchSaveRequest(BaseModel):
    samples: List[BBoxSampleItem]

class DatasetSourceCreateRequest(BaseModel):
    name: str
    kind: str  # 'img' | 'video'
    url: str
    duration_seconds: Optional[float] = None
    total_frames: Optional[int] = None

@router.get("/labels")
def get_custom_labels(db: Session = Depends(get_db)):
    repo = CustomLabelRepository(db)
    labels = repo.get_all()
    if not labels:
        return {"custom_labels": ["person", "forklift", "truck", "container", "car", "crane", "motorbike", "bicycle"]}
    return {"custom_labels": [lbl.label_name for lbl in labels]}

@router.get("/sources")
def get_dataset_sources(db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    sources = repo.get_sources()
    return sources

@router.post("/sources")
def create_dataset_source(
    payload: DatasetSourceCreateRequest,
    db: Session = Depends(get_db)
):
    if payload.kind not in ("img", "video"):
        raise HTTPException(status_code=400, detail="kind phải là 'img' hoặc 'video'")
    
    src_id = f"src-{uuid.uuid4().hex[:8]}"
    source = DatasetSourceModel(
        id=src_id,
        name=payload.name,
        kind=payload.kind,
        url=payload.url,
        duration_seconds=payload.duration_seconds,
        total_frames=payload.total_frames,
        created_at=datetime.utcnow()
    )
    repo = DatasetRepository(db)
    created = repo.create_source(source)
    return created

@router.get("/samples")
def get_bbox_samples(
    label_id: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    repo = DatasetRepository(db)
    return repo.get_samples(label_id=label_id, source_id=source_id)

@router.post("/samples")
def save_bbox_samples_batch(
    payload: BBoxBatchSaveRequest,
    db: Session = Depends(get_db)
):
    repo = DatasetRepository(db)
    samples_data = [item.dict() for item in payload.samples]
    saved = repo.save_samples_batch(samples_data)
    return {"success": True, "saved_count": len(saved), "samples": saved}

@router.delete("/samples/{sample_id}")
def delete_bbox_sample(
    sample_id: str,
    db: Session = Depends(get_db)
):
    repo = DatasetRepository(db)
    success = repo.delete_sample(sample_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy BBox sample có id: {sample_id}")
    return {"success": True, "message": f"Đã xóa BBox sample {sample_id}"}

@router.post("/sync-zones")
def sync_custom_labels_to_zones(db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    result = repo.sync_custom_labels_to_zones()
    return result

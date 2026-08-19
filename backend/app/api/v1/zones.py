from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.database.engine import get_db
from backend.database.repository import ZoneRepository
from backend.database.models import Zone as ZoneModel
import uuid

router = APIRouter()

class Point2D(BaseModel):
    x: float
    y: float

class ZoneCreateRequest(BaseModel):
    camera_id: str = "BAI-KIEM"
    name: str
    vertices: List[Any]  # Array of Point2D objects or [x, y] coordinates
    allowed_classes: List[str] = Field(default_factory=list)
    forbidden_classes: List[str] = Field(default_factory=list)
    is_active: bool = True
    color: str = "#EF4444"

class ZoneUpdateRequest(BaseModel):
    name: Optional[str] = None
    vertices: Optional[List[Any]] = None
    allowed_classes: Optional[List[str]] = None
    forbidden_classes: Optional[List[str]] = None
    is_active: Optional[bool] = None
    color: Optional[str] = None

class ZoneResponse(BaseModel):
    id: str
    camera_id: str
    name: str
    vertices: Any
    allowed_classes: Any
    forbidden_classes: Any
    is_active: bool
    color: Optional[str] = "#EF4444"
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[ZoneResponse])
def get_zones(
    camera_id: Optional[str] = Query(None, description="Lọc theo mã camera (BAI-KIEM, GATE-01)"),
    db: Session = Depends(get_db)
):
    repo = ZoneRepository(db)
    if camera_id:
        zones = repo.get_by_camera(camera_id)
    else:
        zones = repo.get_all()
    return zones

@router.post("", response_model=ZoneResponse)
def create_zone(
    payload: ZoneCreateRequest,
    db: Session = Depends(get_db)
):
    if len(payload.vertices) < 3:
        raise HTTPException(status_code=422, detail="Polygon đa giác zone phải chứa ít nhất 3 đỉnh.")
    
    zone_id = f"zone-{uuid.uuid4().hex[:8]}"
    new_zone = ZoneModel(
        id=zone_id,
        camera_id=payload.camera_id,
        name=payload.name,
        vertices=payload.vertices,
        allowed_classes=payload.allowed_classes,
        forbidden_classes=payload.forbidden_classes,
        is_active=payload.is_active,
        color=payload.color,
    )
    repo = ZoneRepository(db)
    created = repo.create(new_zone)
    return created

@router.put("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: str,
    payload: ZoneUpdateRequest,
    db: Session = Depends(get_db)
):
    repo = ZoneRepository(db)
    if payload.vertices is not None and len(payload.vertices) < 3:
        raise HTTPException(status_code=422, detail="Polygon đa giác zone phải chứa ít nhất 3 đỉnh.")
        
    updated = repo.update_zone(
        zone_id=zone_id,
        name=payload.name,
        vertices=payload.vertices,
        allowed_classes=payload.allowed_classes,
        forbidden_classes=payload.forbidden_classes,
        is_active=payload.is_active,
        color=payload.color
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy zone có id: {zone_id}")
    return updated

@router.delete("/{zone_id}")
def delete_zone(
    zone_id: str,
    db: Session = Depends(get_db)
):
    repo = ZoneRepository(db)
    success = repo.delete(zone_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy zone có id: {zone_id}")
    return {"success": True, "message": f"Đã xóa zone {zone_id}"}

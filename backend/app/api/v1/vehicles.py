from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database.engine import get_db
from backend.database.repository import VehicleRepository

router = APIRouter()

class VehicleTagUpdateRequest(BaseModel):
    tag_label: str  # 'known' | 'unknown' | 'blacklisted'
    vehicle_type: Optional[str] = "car"
    notes: Optional[str] = None

class VehicleResponse(BaseModel):
    id: str
    license_plate: str
    vehicle_type: str
    tag_label: str
    crop_image_url: Optional[str] = None
    last_seen_at: datetime
    total_entries: int
    notes: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("", response_model=List[VehicleResponse])
def get_vehicles(
    tag_label: Optional[str] = Query(None, description="Lọc theo nhãn 'known', 'unknown', 'blacklisted'"),
    db: Session = Depends(get_db)
):
    repo = VehicleRepository(db)
    vehicles = repo.list_all(tag_label=tag_label)
    return vehicles

@router.get("/stats")
def get_vehicle_stats(db: Session = Depends(get_db)):
    repo = VehicleRepository(db)
    return repo.get_stats()

@router.put("/{plate_number}/tag", response_model=VehicleResponse)
def update_vehicle_tag(
    plate_number: str,
    payload: VehicleTagUpdateRequest,
    db: Session = Depends(get_db)
):
    if payload.tag_label not in ("known", "unknown", "blacklisted"):
        raise HTTPException(status_code=400, detail="tag_label phải là 'known', 'unknown', hoặc 'blacklisted'")
    
    repo = VehicleRepository(db)
    vehicle = repo.update_tag(
        license_plate=plate_number,
        tag_label=payload.tag_label,
        notes=payload.notes,
        vehicle_type=payload.vehicle_type
    )
    return vehicle

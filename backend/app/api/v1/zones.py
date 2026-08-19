from fastapi import APIRouter
from typing import List
from app.models.schemas.zone import ZoneResponse, ZoneCreate

router = APIRouter()

@router.get("", response_model=List[ZoneResponse])
def get_zones():
    return [
        ZoneResponse(
            id="zone-01",
            name="Vùng Nguy Hiểm Xe Nâng",
            camera_id="BAI-KIEM",
            polygon_points=[[0.1, 0.1], [0.9, 0.1], [0.8, 0.8], [0.2, 0.8]],
            severity=3,
            allowed_classes=["forklift"],
            active=True
        )
    ]

@router.post("", response_model=ZoneResponse)
def create_zone(zone: ZoneCreate):
    return ZoneResponse(id="zone-new", **zone.dict())

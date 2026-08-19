from fastapi import APIRouter
from typing import List
from datetime import datetime
from app.models.schemas.vehicle import VehicleTagResponse, VehicleTagCreate

router = APIRouter()

@router.get("", response_model=List[VehicleTagResponse])
def get_vehicles():
    return [
        VehicleTagResponse(
            id="v-01",
            plate_number="29A-123.45",
            owner_name="Công Ty Vận Tải A",
            vehicle_type="Truck",
            category="WHITELIST",
            notes="Đã đăng ký cố định",
            updated_at=datetime.utcnow()
        )
    ]

@router.post("", response_model=VehicleTagResponse)
def create_vehicle(tag: VehicleTagCreate):
    return VehicleTagResponse(id="v-new", updated_at=datetime.utcnow(), **tag.dict())

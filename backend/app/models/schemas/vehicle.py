from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VehicleTagBase(BaseModel):
    plate_number: str
    owner_name: str
    vehicle_type: str = "Car"
    category: str = "WHITELIST"  # WHITELIST, BLACKLIST, VISITOR
    notes: Optional[str] = None

class VehicleTagCreate(VehicleTagBase):
    pass

class VehicleTagResponse(VehicleTagBase):
    id: str
    updated_at: datetime

    class Config:
        from_attributes = True

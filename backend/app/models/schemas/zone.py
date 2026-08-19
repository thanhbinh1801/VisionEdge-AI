from pydantic import BaseModel
from typing import List, Tuple

class ZoneBase(BaseModel):
    name: str
    camera_id: str
    polygon_points: List[Tuple[float, float]]
    severity: int = 2
    allowed_classes: List[str] = []
    active: bool = True

class ZoneCreate(ZoneBase):
    pass

class ZoneResponse(ZoneBase):
    id: str

    class Config:
        from_attributes = True

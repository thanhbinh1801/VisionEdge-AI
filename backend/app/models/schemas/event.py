from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    camera_id: str
    camera_name: str
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    event_type: str
    severity: int = 1
    plate_number: Optional[str] = None
    object_class: str
    confidence: float
    crop_url: Optional[str] = None
    video_clip_url: Optional[str] = None
    status: str = "NEW"

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True

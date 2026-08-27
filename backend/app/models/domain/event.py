from sqlalchemy import Column, String, Integer, Float, DateTime
from datetime import datetime
from backend.app.core.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    camera_id = Column(String, index=True)
    camera_name = Column(String)
    zone_id = Column(String, nullable=True)
    zone_name = Column(String, nullable=True)
    event_type = Column(String)  # LPR, ZONE_INTRUSION, UNAUTHORIZED_VEHICLE, SAFETY_VIOLATION
    severity = Column(Integer, default=1)  # Level 1, 2, 3
    plate_number = Column(String, nullable=True, index=True)
    object_class = Column(String)
    confidence = Column(Float)
    crop_url = Column(String, nullable=True)
    video_clip_url = Column(String, nullable=True)
    status = Column(String, default="NEW")

from sqlalchemy import Column, String, Integer, Boolean, Text
from app.core.database import Base

class Zone(Base):
    __tablename__ = "zones"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    camera_id = Column(String, index=True)
    polygon_points_json = Column(Text)  # JSON string of [[x1, y1], [x2, y2], ...]
    severity = Column(Integer, default=2)
    allowed_classes_json = Column(Text)  # JSON string of ['person', 'truck']
    active = Column(Boolean, default=True)

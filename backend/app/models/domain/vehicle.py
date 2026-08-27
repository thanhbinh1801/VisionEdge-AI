from sqlalchemy import Column, String, DateTime
from datetime import datetime
from backend.app.core.database import Base

class VehicleTag(Base):
    __tablename__ = "vehicle_tags"

    id = Column(String, primary_key=True, index=True)
    plate_number = Column(String, unique=True, index=True)
    owner_name = Column(String)
    vehicle_type = Column(String)
    category = Column(String)  # WHITELIST, BLACKLIST, VISITOR, CONTRACTOR
    notes = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

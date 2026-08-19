from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from backend.database.models import (
    Camera,
    Zone,
    Vehicle,
    Event,
    CustomLabel,
    KpiRealtimeCache,
)

class CameraRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, camera_id: str) -> Optional[Camera]:
        return self.db.query(Camera).filter(Camera.id == camera_id).first()

    def get_all(self) -> List[Camera]:
        return self.db.query(Camera).all()

    def create(self, camera: Camera) -> Camera:
        self.db.add(camera)
        self.db.commit()
        self.db.refresh(camera)
        return camera

class ZoneRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, zone_id: str) -> Optional[Zone]:
        return self.db.query(Zone).filter(Zone.id == zone_id).first()

    def get_by_camera(self, camera_id: str) -> List[Zone]:
        return self.db.query(Zone).filter(Zone.camera_id == camera_id, Zone.is_active == True).all()

    def create(self, zone: Zone) -> Zone:
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return zone

    def delete(self, zone_id: str) -> bool:
        zone = self.get_by_id(zone_id)
        if zone:
            self.db.delete(zone)
            self.db.commit()
            return True
        return False

class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_plate(self, license_plate: str) -> Optional[Vehicle]:
        return self.db.query(Vehicle).filter(Vehicle.license_plate == license_plate).first()

    def list_all(self, tag_label: Optional[str] = None) -> List[Vehicle]:
        query = self.db.query(Vehicle)
        if tag_label:
            query = query.filter(Vehicle.tag_label == tag_label)
        return query.all()

    def upsert(self, vehicle: Vehicle) -> Vehicle:
        existing = self.get_by_plate(vehicle.license_plate)
        if existing:
            existing.last_seen_at = datetime.utcnow()
            existing.total_entries += 1
            if vehicle.tag_label:
                existing.tag_label = vehicle.tag_label
            if vehicle.crop_image_url:
                existing.crop_image_url = vehicle.crop_image_url
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            self.db.add(vehicle)
            self.db.commit()
            self.db.refresh(vehicle)
            return vehicle

class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event: Event) -> Event:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_recent_events(
        self,
        camera_id: Optional[str] = None,
        severity_level: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Event]:
        query = self.db.query(Event)
        if camera_id:
            query = query.filter(Event.camera_id == camera_id)
        if severity_level:
            query = query.filter(Event.severity_level == severity_level)
        return query.order_by(desc(Event.timestamp)).offset(offset).limit(limit).all()

    def count_by_severity(self, severity_level: int) -> int:
        return self.db.query(func.count(Event.id)).filter(Event.severity_level == severity_level).scalar() or 0

class CustomLabelRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[CustomLabel]:
        return self.db.query(CustomLabel).all()

    def create_or_increment(self, label_name: str, category: str = "custom") -> CustomLabel:
        existing = self.db.query(CustomLabel).filter(CustomLabel.label_name == label_name).first()
        if existing:
            existing.sample_count += 1
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_label = CustomLabel(
                id=f"lbl_{int(datetime.utcnow().timestamp())}",
                label_name=label_name,
                category=category,
                sample_count=1,
            )
            self.db.add(new_label)
            self.db.commit()
            self.db.refresh(new_label)
            return new_label

class KpiRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_kpi(self) -> Optional[KpiRealtimeCache]:
        return self.db.query(KpiRealtimeCache).filter(KpiRealtimeCache.id == "GLOBAL_KPI").first()

    def update_kpi(self, **kwargs) -> KpiRealtimeCache:
        kpi = self.get_kpi()
        if not kpi:
            kpi = KpiRealtimeCache(id="GLOBAL_KPI")
            self.db.add(kpi)
        
        for key, val in kwargs.items():
            if hasattr(kpi, key):
                setattr(kpi, key, val)
        kpi.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(kpi)
        return kpi

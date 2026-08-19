from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
import uuid
from backend.database.models import (
    Camera,
    Zone,
    Vehicle,
    Event,
    CustomLabel,
    DatasetSource,
    BBoxSample,
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

    def get_all(self) -> List[Zone]:
        return self.db.query(Zone).all()

    def create(self, zone: Zone) -> Zone:
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return zone

    def update_zone(
        self,
        zone_id: str,
        name: Optional[str] = None,
        vertices: Optional[list] = None,
        allowed_classes: Optional[list] = None,
        forbidden_classes: Optional[list] = None,
        is_active: Optional[bool] = None,
        color: Optional[str] = None,
    ) -> Optional[Zone]:
        zone = self.get_by_id(zone_id)
        if not zone:
            return None
        if name is not None:
            zone.name = name
        if vertices is not None:
            zone.vertices = vertices
        if allowed_classes is not None:
            zone.allowed_classes = allowed_classes
        if forbidden_classes is not None:
            zone.forbidden_classes = forbidden_classes
        if is_active is not None:
            zone.is_active = is_active
        if color is not None:
            zone.color = color
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
        return query.order_by(desc(Vehicle.last_seen_at)).all()

    def update_tag(self, license_plate: str, tag_label: str, notes: Optional[str] = None, vehicle_type: Optional[str] = None) -> Optional[Vehicle]:
        vehicle = self.get_by_plate(license_plate)
        if not vehicle:
            # Create a vehicle entry if not exists
            vehicle = Vehicle(
                id=f"veh-{uuid.uuid4().hex[:8]}",
                license_plate=license_plate,
                vehicle_type=vehicle_type or "car",
                tag_label=tag_label,
                notes=notes,
                last_seen_at=datetime.utcnow(),
                total_entries=1
            )
            self.db.add(vehicle)
        else:
            vehicle.tag_label = tag_label
            if notes is not None:
                vehicle.notes = notes
            if vehicle_type is not None:
                vehicle.vehicle_type = vehicle_type
            vehicle.last_seen_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def get_stats(self) -> Dict[str, int]:
        total_known = self.db.query(func.count(Vehicle.id)).filter(Vehicle.tag_label == "known").scalar() or 0
        total_unknown = self.db.query(func.count(Vehicle.id)).filter(Vehicle.tag_label == "unknown").scalar() or 0
        total_blacklisted = self.db.query(func.count(Vehicle.id)).filter(Vehicle.tag_label == "blacklisted").scalar() or 0
        return {
            "known": total_known,
            "unknown": total_unknown,
            "blacklisted": total_blacklisted,
            "total": total_known + total_unknown + total_blacklisted
        }

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

class DatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_sources(self) -> List[DatasetSource]:
        return self.db.query(DatasetSource).all()

    def create_source(self, source: DatasetSource) -> DatasetSource:
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_samples(self, label_id: Optional[str] = None, source_id: Optional[str] = None) -> List[BBoxSample]:
        query = self.db.query(BBoxSample)
        if label_id:
            query = query.filter(BBoxSample.label_id == label_id)
        if source_id:
            query = query.filter(BBoxSample.source_id == source_id)
        return query.order_by(desc(BBoxSample.created_at)).all()

    def save_samples_batch(self, samples_data: List[Dict[str, Any]]) -> List[BBoxSample]:
        created_samples = []
        custom_label_repo = CustomLabelRepository(self.db)
        
        for item in samples_data:
            sample_id = item.get("id") or f"bbox-{uuid.uuid4().hex[:10]}"
            label_name = item.get("label_name", "custom_object")
            category = item.get("category", "vehicle_shape")
            
            # Increment sample count in custom_labels
            custom_label_repo.create_or_increment(label_name=label_name, category=category)
            
            sample = BBoxSample(
                id=sample_id,
                label_id=item.get("label_id", f"lbl-{label_name}"),
                source_id=item.get("source_id", "src-default"),
                frame_index=item.get("frame_index"),
                x=float(item.get("x", 0)),
                y=float(item.get("y", 0)),
                w=float(item.get("w", 0)),
                h=float(item.get("h", 0)),
                category=category,
                label_name=label_name,
                created_at=datetime.utcnow()
            )
            self.db.add(sample)
            created_samples.append(sample)
            
        self.db.commit()
        for sample in created_samples:
            self.db.refresh(sample)
        return created_samples

    def delete_sample(self, sample_id: str) -> bool:
        sample = self.db.query(BBoxSample).filter(BBoxSample.id == sample_id).first()
        if sample:
            self.db.delete(sample)
            self.db.commit()
            return True
        return False

    def sync_custom_labels_to_zones(self) -> Dict[str, Any]:
        """Tự động đồng bộ các nhãn custom mới vào mảng forbidden_classes của tất cả các zone hiện có"""
        custom_labels = [cl.label_name for cl in self.db.query(CustomLabel).all()]
        zones = self.db.query(Zone).all()
        updated_zones_count = 0
        
        for zone in zones:
            forbidden = set(zone.forbidden_classes or [])
            original_len = len(forbidden)
            for lbl in custom_labels:
                # Add label if not in allowed_classes and not in forbidden_classes
                if lbl not in (zone.allowed_classes or []) and lbl not in forbidden:
                    forbidden.add(lbl)
            if len(forbidden) > original_len:
                zone.forbidden_classes = list(forbidden)
                updated_zones_count += 1
                
        if updated_zones_count > 0:
            self.db.commit()
            
        return {
            "synced_count": len(custom_labels),
            "synced_labels": custom_labels,
            "affected_zones": updated_zones_count
        }

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

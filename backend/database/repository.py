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
    SYSTEM_LABELS = (
        ("lbl_system_container", "container", "Container", "vehicle_shape"),
        ("lbl_system_truck", "truck", "Xe tải", "vehicle_shape"),
        ("lbl_system_forklift", "forklift", "Xe nâng", "vehicle_shape"),
        ("lbl_system_crane", "crane", "Xe cẩu", "vehicle_shape"),
        ("lbl_system_car", "car", "Xe con", "vehicle_shape"),
        ("lbl_system_motorbike", "motorbike", "Xe máy", "vehicle_shape"),
        ("lbl_system_bicycle", "bicycle", "Xe đạp", "vehicle_shape"),
        ("lbl_system_person", "person", "Người", "person"),
    )

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def label_key(label_name: str) -> str:
        return " ".join(label_name.strip().lower().split())

    def seed_system_labels(self) -> None:
        for label_id, key, name, category in self.SYSTEM_LABELS:
            existing = self.db.query(CustomLabel).filter(CustomLabel.id == label_id).first()
            if not existing:
                self.db.add(CustomLabel(
                    id=label_id,
                    label_key=key,
                    label_name=name,
                    label_type="system",
                    category=category,
                    sample_count=0,
                    is_active=True,
                ))
        self.db.flush()

    def get_all(self, include_deleted: bool = False) -> List[CustomLabel]:
        self.seed_system_labels()
        query = self.db.query(CustomLabel)
        if not include_deleted:
            query = query.filter(CustomLabel.is_active == True)
        return query.order_by(CustomLabel.label_type.desc(), CustomLabel.label_key.asc()).all()

    def get_by_id(self, label_id: str) -> Optional[CustomLabel]:
        return self.db.query(CustomLabel).filter(CustomLabel.id == label_id).first()

    def get_by_key(self, label_key: str) -> Optional[CustomLabel]:
        return self.db.query(CustomLabel).filter(CustomLabel.label_key == label_key).first()

    def create_custom(self, label_name: str, category: str) -> CustomLabel:
        key = self.label_key(label_name)
        existing = self.get_by_key(key)
        if existing:
            raise DatasetError("DUPLICATE_LABEL_NAME", "Label name already exists.")
        label = CustomLabel(
            id=f"lbl_custom_{uuid.uuid4().hex[:10]}",
            label_key=key,
            label_name=label_name.strip(),
            label_type="custom",
            category=category,
            sample_count=0,
            is_active=True,
        )
        self.db.add(label)
        self.db.flush()
        return label

    def update_custom(self, label_id: str, label_name: Optional[str] = None, category: Optional[str] = None) -> CustomLabel:
        label = self.get_by_id(label_id)
        if not label:
            raise DatasetError("NOT_FOUND", "Label not found.")
        if label.label_type == "system":
            raise DatasetError("SYSTEM_LABEL_LOCKED", "System labels cannot be renamed or edited.")
        old_key = label.label_key
        if label_name is not None:
            key = self.label_key(label_name)
            duplicate = self.get_by_key(key)
            if duplicate and duplicate.id != label.id:
                raise DatasetError("DUPLICATE_LABEL_NAME", "Label name already exists.")
            label.label_key = key
            label.label_name = label_name.strip()
        if category is not None:
            label.category = category
        label.updated_at = datetime.utcnow()
        return label, old_key

    def soft_delete_custom(self, label_id: str) -> CustomLabel:
        label = self.get_by_id(label_id)
        if not label:
            raise DatasetError("NOT_FOUND", "Label not found.")
        if label.label_type == "system":
            raise DatasetError("SYSTEM_LABEL_LOCKED", "System labels cannot be deleted.")
        zones = self.db.query(Zone).all()
        for zone in zones:
            if label.label_key in (zone.allowed_classes or []) or label.label_key in (zone.forbidden_classes or []):
                raise DatasetError("LABEL_IN_USE_BY_ZONE", "Label is still referenced by zone rules.")
        label.is_active = False
        label.deleted_at = datetime.utcnow()
        label.updated_at = datetime.utcnow()
        self.db.flush()
        return label

    def restore_custom(self, label_id: str) -> CustomLabel:
        label = self.get_by_id(label_id)
        if not label:
            raise DatasetError("NOT_FOUND", "Label not found.")
        if label.label_type == "system":
            raise DatasetError("SYSTEM_LABEL_LOCKED", "System labels cannot be restored.")
        label.is_active = True
        label.deleted_at = None
        label.updated_at = datetime.utcnow()
        self.db.flush()
        return label


class DatasetError(Exception):
    def __init__(self, code: str, message: str, details: Optional[List[Dict[str, str]]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

class DatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_sources(self, page: int = 1, limit: int = 50, kind: Optional[str] = None) -> tuple[List[DatasetSource], int]:
        query = self.db.query(DatasetSource)
        if kind:
            query = query.filter(DatasetSource.kind == kind)
        total = query.count()
        items = query.order_by(desc(DatasetSource.created_at)).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def get_source(self, source_id: str) -> Optional[DatasetSource]:
        return self.db.query(DatasetSource).filter(DatasetSource.id == source_id).first()

    def create_source(self, source: DatasetSource) -> DatasetSource:
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_samples(
        self,
        label_id: Optional[str] = None,
        source_id: Optional[str] = None,
        frame_index: Optional[int] = None,
    ) -> List[BBoxSample]:
        query = self.db.query(BBoxSample)
        if label_id:
            query = query.filter(BBoxSample.label_id == label_id)
        if source_id:
            query = query.filter(BBoxSample.source_id == source_id)
        if frame_index is not None:
            query = query.filter(BBoxSample.frame_index == frame_index)
        return query.order_by(desc(BBoxSample.created_at)).all()

    def save_samples_batch(self, samples_data: List[Dict[str, Any]]) -> List[BBoxSample]:
        if not samples_data:
            raise DatasetError("VALIDATION_ERROR", "At least one sample is required.")
        if len(samples_data) > 200:
            raise DatasetError("VALIDATION_ERROR", "A batch may contain at most 200 samples.")

        labels = {}
        sources = {}
        affected_label_ids = set()
        created_samples = []

        for item in samples_data:
            label = labels.get(item["label_id"]) or self.db.query(CustomLabel).filter(CustomLabel.id == item["label_id"]).first()
            if not label:
                raise DatasetError("NOT_FOUND", "Label not found.", [{"field": "label_id", "issue": item["label_id"]}])
            if not label.is_active:
                raise DatasetError("LABEL_INACTIVE", "Inactive labels cannot be used for samples.")
            labels[label.id] = label

            source = sources.get(item["source_id"]) or self.get_source(item["source_id"])
            if not source:
                raise DatasetError("NOT_FOUND", "Source not found.", [{"field": "source_id", "issue": item["source_id"]}])
            if source.import_status != "ready":
                raise DatasetError("SOURCE_NOT_READY", "Source is not ready for annotation.")
            sources[source.id] = source

            frame_index = item.get("frame_index")
            if source.kind == "video" and frame_index is None:
                raise DatasetError("VALIDATION_ERROR", "Video samples require frame_index.")
            if source.kind == "img" and frame_index is None:
                frame_index = 0

            self._validate_bbox(item)
            sample = BBoxSample(
                id=item.get("id") or f"bbox_{uuid.uuid4().hex[:10]}",
                label_id=label.id,
                source_id=source.id,
                frame_index=frame_index,
                frame_timestamp_seconds=item.get("frame_timestamp_seconds"),
                x=float(item["x"]),
                y=float(item["y"]),
                w=float(item["w"]),
                h=float(item["h"]),
                coordinate_space="percent_0_100",
                category=label.category,
                label_name=label.label_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(sample)
            created_samples.append(sample)
            affected_label_ids.add(label.id)
            
        self.db.flush()
        self.recompute_sample_counts(affected_label_ids)
        self.db.commit()
        for sample in created_samples:
            self.db.refresh(sample)
        return created_samples

    def update_sample(self, sample_id: str, data: Dict[str, Any]) -> BBoxSample:
        sample = self.db.query(BBoxSample).filter(BBoxSample.id == sample_id).first()
        if not sample:
            raise DatasetError("NOT_FOUND", "Sample not found.")
        affected_label_ids = {sample.label_id}
        label = sample.label
        if "label_id" in data:
            label = self.db.query(CustomLabel).filter(CustomLabel.id == data["label_id"]).first()
            if not label:
                raise DatasetError("NOT_FOUND", "Label not found.")
            if not label.is_active:
                raise DatasetError("LABEL_INACTIVE", "Inactive labels cannot be used for samples.")
            sample.label_id = label.id
            sample.category = label.category
            sample.label_name = label.label_name
            affected_label_ids.add(label.id)
        source = sample.source
        frame_index = data.get("frame_index", sample.frame_index)
        if source.kind == "video" and frame_index is None:
            raise DatasetError("VALIDATION_ERROR", "Video samples require frame_index.")
        if source.kind == "img" and frame_index is None:
            frame_index = 0
        sample.frame_index = frame_index
        if "frame_timestamp_seconds" in data:
            sample.frame_timestamp_seconds = data["frame_timestamp_seconds"]
        if "bbox" in data:
            bbox = data["bbox"]
            self._validate_bbox(bbox)
            sample.x = float(bbox["x"])
            sample.y = float(bbox["y"])
            sample.w = float(bbox["w"])
            sample.h = float(bbox["h"])
        sample.updated_at = datetime.utcnow()
        self.db.flush()
        self.recompute_sample_counts(affected_label_ids)
        self.db.commit()
        self.db.refresh(sample)
        return sample

    def delete_sample(self, sample_id: str) -> bool:
        sample = self.db.query(BBoxSample).filter(BBoxSample.id == sample_id).first()
        if sample:
            label_id = sample.label_id
            self.db.delete(sample)
            self.db.flush()
            self.recompute_sample_counts({label_id})
            self.db.commit()
            return True
        return False

    def recompute_sample_counts(self, label_ids) -> List[CustomLabel]:
        labels = []
        for label_id in label_ids:
            label = self.db.query(CustomLabel).filter(CustomLabel.id == label_id).first()
            if label:
                label.sample_count = self.db.query(func.count(BBoxSample.id)).filter(BBoxSample.label_id == label_id).scalar() or 0
                label.updated_at = datetime.utcnow()
                labels.append(label)
        self.db.flush()
        return labels

    @staticmethod
    def _validate_bbox(item: Dict[str, Any]) -> None:
        x, y, w, h = (float(item["x"]), float(item["y"]), float(item["w"]), float(item["h"]))
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x > 100 or y > 100 or w > 100 or h > 100 or x + w > 100 or y + h > 100:
            raise DatasetError("VALIDATION_ERROR", "BBox must fit within percent_0_100 coordinate space.")

    def sync_custom_labels_to_zones(self) -> Dict[str, Any]:
        """Sync active custom label keys into every zone as forbidden by default."""
        custom_labels = [
            cl.label_key for cl in self.db.query(CustomLabel)
            .filter(CustomLabel.label_type == "custom", CustomLabel.is_active == True)
            .order_by(CustomLabel.label_key.asc()).all()
        ]
        zones = self.db.query(Zone).all()
        affected_zones = []
        
        for zone in zones:
            forbidden = set(zone.forbidden_classes or [])
            allowed = set(zone.allowed_classes or [])
            for lbl in custom_labels:
                if lbl not in allowed and lbl not in forbidden:
                    forbidden.add(lbl)
            if set(zone.forbidden_classes or []) != forbidden:
                zone.forbidden_classes = sorted(forbidden)
                affected_zones.append(zone.id)
                
        self.db.flush()
            
        return {
            "synced_labels": custom_labels,
            "affected_zones": affected_zones,
            "default_rule": "forbidden",
            "cache": [
                {
                    "camera_id": zone.camera_id,
                    "zone_version": 1,
                    "cache_status": "hot",
                    "refreshed_at": datetime.utcnow().isoformat() + "Z",
                }
                for zone in zones
            ],
        }

    def rename_label_in_zones(self, old_key: str, new_key: str) -> None:
        if old_key == new_key:
            return
        for zone in self.db.query(Zone).all():
            allowed = [new_key if item == old_key else item for item in (zone.allowed_classes or [])]
            forbidden = [new_key if item == old_key else item for item in (zone.forbidden_classes or [])]
            zone.allowed_classes = list(dict.fromkeys(allowed))
            zone.forbidden_classes = list(dict.fromkeys(forbidden))
        self.db.flush()

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

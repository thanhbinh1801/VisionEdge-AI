from dataclasses import dataclass
from typing import Optional

@dataclass
class CameraModel:
    id: str
    name: str
    location: str
    stream_url: str
    created_at: Optional[str] = None

@dataclass
class ZoneModel:
    id: str
    camera_id: str
    name: str
    polygon_points: str  # JSON string
    rule_type: str  # 'allow', 'deny', 'lpr'
    created_at: Optional[str] = None

@dataclass
class VehicleModel:
    license_plate: str
    vehicle_type: Optional[str]
    list_type: str  # 'whitelist', 'blacklist', 'unknown'
    owner_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class EventModel:
    id: str
    camera_id: str
    event_type: str
    severity: int
    zone_id: Optional[str] = None
    license_plate: Optional[str] = None
    ocr_confidence: Optional[float] = None
    object_class: Optional[str] = None
    snapshot_path: Optional[str] = None
    clip_path: Optional[str] = None
    is_corrected: bool = False
    corrected_plate: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class CustomLabelModel:
    id: str
    label_name: str
    bbox_coordinates: str
    feature_embedding: Optional[bytes] = None
    created_at: Optional[str] = None

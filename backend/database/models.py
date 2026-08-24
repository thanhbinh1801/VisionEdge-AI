from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.engine import Base

class SchemaMigration(Base):
    __tablename__ = "schema_migrations"

    version = Column(String(32), primary_key=True)
    description = Column(String(255), nullable=False)
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(32), primary_key=True)
    name = Column(String(128), nullable=False)
    location = Column(String(255), nullable=False)
    stream_url = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False, default="online")
    fps = Column(Float, nullable=False, default=10.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="camera", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('online', 'offline', 'degraded')", name="check_camera_status"),
        CheckConstraint("fps > 0", name="check_camera_fps"),
    )

class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(64), primary_key=True)
    camera_id = Column(String(32), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    vertices = Column(JSON, nullable=False)
    allowed_classes = Column(JSON, nullable=False)
    forbidden_classes = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    color = Column(String(16), default="#EF4444")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    camera = relationship("Camera", back_populates="zones")
    events = relationship("Event", back_populates="zone")

    __table_args__ = (
        Index("idx_zones_camera_id", "camera_id"),
    )

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String(64), primary_key=True)
    license_plate = Column(String(32), nullable=False, unique=True)
    vehicle_type = Column(String(64), default="car")
    tag_label = Column(String(32), nullable=False, default="unknown")
    crop_image_url = Column(String(512), nullable=True)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_entries = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("tag_label IN ('known', 'unknown', 'blacklisted')", name="check_vehicle_tag_label"),
        CheckConstraint("total_entries >= 0", name="check_vehicle_total_entries"),
        Index("idx_vehicles_license_plate", "license_plate", unique=True),
    )

class Event(Base):
    __tablename__ = "events"

    id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    camera_id = Column(String(32), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(String(64), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    lane_id = Column(String(32), nullable=True)
    event_type = Column(String(64), nullable=False)
    severity_level = Column(Integer, nullable=False)
    license_plate = Column(String(32), nullable=True)
    object_class = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False)
    bbox = Column(JSON, nullable=True)
    crop_image_url = Column(String(512), nullable=True)
    video_clip_url = Column(String(512), nullable=True)

    camera = relationship("Camera", back_populates="events")
    zone = relationship("Zone", back_populates="events")

    __table_args__ = (
        CheckConstraint("event_type IN ('LPR_PASSAGE', 'ZONE_VIOLATION', 'RESTRICTED_ACCESS')", name="check_event_type"),
        CheckConstraint("severity_level IN (1, 2, 3)", name="check_event_severity"),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="check_event_confidence"),
        Index("idx_events_timestamp", timestamp.desc()),
        Index("idx_events_camera_severity", "camera_id", "severity_level"),
        Index("idx_events_license_plate", "license_plate"),
    )

class CustomLabel(Base):
    __tablename__ = "custom_labels"

    id = Column(String(64), primary_key=True)
    label_key = Column(String(128), nullable=True, unique=True)
    label_name = Column(String(128), nullable=False)
    label_type = Column(String(16), nullable=False, default="custom")
    category = Column(String(64), nullable=False, default="custom")
    sample_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    samples = relationship("BBoxSample", back_populates="label")

    __table_args__ = (
        CheckConstraint("sample_count >= 0", name="check_custom_label_sample_count"),
        CheckConstraint("label_type IN ('system', 'custom')", name="check_custom_label_type"),
        CheckConstraint("category IN ('person', 'vehicle_shape', 'custom')", name="check_custom_label_category"),
        Index("idx_object_labels_label_key", "label_key", unique=True),
        Index("idx_object_labels_active_type_key", "is_active", "label_type", "label_key"),
    )

class DatasetSource(Base):
    __tablename__ = "dataset_sources"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    kind = Column(String(16), nullable=False)  # 'img' | 'video'
    url = Column(String(512), nullable=True)
    storage_path = Column(String(512), nullable=True)
    public_url = Column(String(512), nullable=True)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(128), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    total_frames = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    import_status = Column(String(32), nullable=False, default="ready")
    import_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    samples = relationship("BBoxSample", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("kind IN ('img', 'video')", name="check_dataset_source_kind"),
        CheckConstraint("import_status IN ('processing', 'ready', 'failed')", name="check_dataset_source_import_status"),
        Index("idx_dataset_sources_created_at", created_at.desc()),
        Index("idx_dataset_sources_sha256", "sha256"),
    )

class BBoxSample(Base):
    __tablename__ = "bbox_samples"

    id = Column(String(64), primary_key=True)
    label_id = Column(String(64), ForeignKey("custom_labels.id"), nullable=False)
    source_id = Column(String(64), ForeignKey("dataset_sources.id", ondelete="CASCADE"), nullable=False)
    frame_index = Column(Integer, nullable=True)
    frame_timestamp_seconds = Column(Float, nullable=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    w = Column(Float, nullable=False)
    h = Column(Float, nullable=False)
    coordinate_space = Column(String(32), nullable=False, default="percent_0_100")
    category = Column(String(32), nullable=True)
    label_name = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    source = relationship("DatasetSource", back_populates="samples")
    label = relationship("CustomLabel", back_populates="samples")

    __table_args__ = (
        CheckConstraint("category IN ('person', 'vehicle_shape', 'custom')", name="check_bbox_sample_category"),
        CheckConstraint("coordinate_space = 'percent_0_100'", name="check_bbox_coordinate_space"),
        CheckConstraint("frame_index IS NULL OR frame_index >= 0", name="check_bbox_frame_index"),
        CheckConstraint("frame_timestamp_seconds IS NULL OR frame_timestamp_seconds >= 0", name="check_bbox_frame_timestamp"),
        CheckConstraint("x >= 0 AND x <= 100", name="check_bbox_x"),
        CheckConstraint("y >= 0 AND y <= 100", name="check_bbox_y"),
        CheckConstraint("w > 0 AND w <= 100", name="check_bbox_w"),
        CheckConstraint("h > 0 AND h <= 100", name="check_bbox_h"),
        CheckConstraint("x + w <= 100", name="check_bbox_x_extent"),
        CheckConstraint("y + h <= 100", name="check_bbox_y_extent"),
        Index("idx_bbox_samples_label", "label_id"),
        Index("idx_bbox_samples_source", "source_id"),
        Index("idx_bbox_samples_source_frame", "source_id", "frame_index", created_at.desc()),
    )

class KpiRealtimeCache(Base):
    __tablename__ = "kpi_realtime_cache"

    id = Column(String(32), primary_key=True, default="GLOBAL_KPI")
    gate_vehicles_total = Column(Integer, nullable=False, default=0)
    gate_lpr_success = Column(Integer, nullable=False, default=0)
    gate_lpr_failed = Column(Integer, nullable=False, default=0)
    gate_avg_confidence = Column(Float, nullable=False, default=0.0)
    area_active_objects = Column(Integer, nullable=False, default=0)
    area_zone_violations = Column(Integer, nullable=False, default=0)
    area_active_machinery = Column(Integer, nullable=False, default=0)
    area_total_zones = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

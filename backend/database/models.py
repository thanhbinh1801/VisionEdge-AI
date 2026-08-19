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
    label_name = Column(String(128), nullable=False, unique=True)
    category = Column(String(64), nullable=False, default="custom")
    sample_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("sample_count >= 0", name="check_custom_label_sample_count"),
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

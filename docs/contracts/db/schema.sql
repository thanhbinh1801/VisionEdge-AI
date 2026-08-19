-- ====================================================================
-- SentriAI Mini - Database Schema DDL (SQLite3)
-- Artifact: schema.sql (TASK-003)
-- Target: SQLite 3.35+ with Foreign Keys & WAL Mode
-- ====================================================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------
-- 0. Schema Migrations History
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(32) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 1. Cameras Table (REQ-001, REQ-002)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cameras (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    location VARCHAR(255) NOT NULL,
    stream_url VARCHAR(512) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'online' CHECK (status IN ('online', 'offline', 'degraded')),
    fps FLOAT NOT NULL DEFAULT 10.0 CHECK (fps > 0),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 2. Polygon Zones Table (REQ-002, REQ-005)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zones (
    id VARCHAR(64) PRIMARY KEY,
    camera_id VARCHAR(32) NOT NULL,
    name VARCHAR(128) NOT NULL,
    vertices JSON NOT NULL,
    allowed_classes JSON NOT NULL,
    forbidden_classes JSON NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    color VARCHAR(16) DEFAULT '#EF4444',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
);

-- --------------------------------------------------------------------
-- 3. Vehicle Whitelist & Blacklist Table (REQ-006)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicles (
    id VARCHAR(64) PRIMARY KEY,
    license_plate VARCHAR(32) NOT NULL UNIQUE,
    vehicle_type VARCHAR(64) DEFAULT 'car',
    tag_label VARCHAR(32) NOT NULL DEFAULT 'unknown' CHECK (tag_label IN ('known', 'unknown', 'blacklisted')),
    crop_image_url VARCHAR(512),
    last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_entries INTEGER NOT NULL DEFAULT 1 CHECK (total_entries >= 0),
    notes TEXT
);

-- --------------------------------------------------------------------
-- 4. Detection & Violation Events Table (REQ-001, REQ-002, REQ-003, REQ-004)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(64) PRIMARY KEY,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    camera_id VARCHAR(32) NOT NULL,
    zone_id VARCHAR(64),
    lane_id VARCHAR(32),
    event_type VARCHAR(64) NOT NULL CHECK (event_type IN ('LPR_PASSAGE', 'ZONE_VIOLATION', 'RESTRICTED_ACCESS')),
    severity_level INTEGER NOT NULL CHECK (severity_level IN (1, 2, 3)),
    license_plate VARCHAR(32),
    object_class VARCHAR(64) NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    bbox JSON,
    crop_image_url VARCHAR(512),
    video_clip_url VARCHAR(512),
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL
);

-- --------------------------------------------------------------------
-- 5. Custom Label Dataset Annotations Table (REQ-007)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS custom_labels (
    id VARCHAR(64) PRIMARY KEY,
    label_name VARCHAR(128) NOT NULL UNIQUE,
    category VARCHAR(64) NOT NULL DEFAULT 'custom',
    sample_count INTEGER NOT NULL DEFAULT 0 CHECK (sample_count >= 0),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 6. KPI Real-time Dashboard Cache Table (REQ-001, REQ-002)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kpi_realtime_cache (
    id VARCHAR(32) PRIMARY KEY DEFAULT 'GLOBAL_KPI',
    gate_vehicles_total INTEGER NOT NULL DEFAULT 0,
    gate_lpr_success INTEGER NOT NULL DEFAULT 0,
    gate_lpr_failed INTEGER NOT NULL DEFAULT 0,
    gate_avg_confidence FLOAT NOT NULL DEFAULT 0.0,
    area_active_objects INTEGER NOT NULL DEFAULT 0,
    area_zone_violations INTEGER NOT NULL DEFAULT 0,
    area_active_machinery INTEGER NOT NULL DEFAULT 0,
    area_total_zones INTEGER NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- Indexes for High-Frequency Realtime Queries & Text-to-SQL Performance
-- --------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_camera_severity ON events(camera_id, severity_level);
CREATE INDEX IF NOT EXISTS idx_events_license_plate ON events(license_plate);
CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicles_license_plate ON vehicles(license_plate);
CREATE INDEX IF NOT EXISTS idx_zones_camera_id ON zones(camera_id);

-- --------------------------------------------------------------------
-- Initial Seed Data
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('1.0.0', 'Initial database schema foundation for SentriAI Mini (CR-002)');

INSERT OR IGNORE INTO cameras (id, name, location, stream_url, fps)
VALUES 
    ('GATE-01', 'Camera Cổng Ván LPR', 'Cổng Chính IN', '/videos/GATE-01.mp4', 15.0),
    ('BAI-KIEM', 'Camera Bãi Kiểm An Ninh', 'Khu Vực Bãi Kiểm', '/videos/BAI-KIEM.mp4', 10.0);

INSERT OR IGNORE INTO kpi_realtime_cache (id, gate_vehicles_total, gate_lpr_success, gate_lpr_failed, gate_avg_confidence, area_active_objects, area_zone_violations, area_active_machinery, area_total_zones)
VALUES ('GLOBAL_KPI', 128, 120, 8, 94.5, 14, 3, 5, 2);

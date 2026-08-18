-- DDL Schema Contract for SQLite (SentriAI Mini)
-- Database design contract artifact (docs/contracts/db-schema.sql)

CREATE TABLE IF NOT EXISTS cameras (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    stream_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS zones (
    id TEXT PRIMARY KEY,
    camera_id TEXT NOT NULL,
    name TEXT NOT NULL,
    polygon_points TEXT NOT NULL, -- JSON array of [x, y] coordinates
    rule_type TEXT NOT NULL, -- 'allow', 'deny', 'lpr'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(camera_id) REFERENCES cameras(id)
);

CREATE TABLE IF NOT EXISTS vehicles (
    license_plate TEXT PRIMARY KEY,
    vehicle_type TEXT,
    list_type TEXT NOT NULL, -- 'whitelist', 'blacklist', 'unknown'
    owner_name TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    camera_id TEXT NOT NULL,
    zone_id TEXT,
    event_type TEXT NOT NULL, -- 'lpr_detected', 'zone_violation', 'custom_label'
    severity INTEGER NOT NULL CHECK(severity IN (1, 2, 3)),
    license_plate TEXT,
    ocr_confidence REAL,
    object_class TEXT,
    snapshot_path TEXT,
    clip_path TEXT,
    is_corrected BOOLEAN DEFAULT 0,
    corrected_plate TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(camera_id) REFERENCES cameras(id),
    FOREIGN KEY(zone_id) REFERENCES zones(id)
);

CREATE TABLE IF NOT EXISTS custom_labels (
    id TEXT PRIMARY KEY,
    label_name TEXT NOT NULL,
    bbox_coordinates TEXT NOT NULL, -- JSON array
    feature_embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_camera_severity ON events(camera_id, severity);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_plate ON events(license_plate);

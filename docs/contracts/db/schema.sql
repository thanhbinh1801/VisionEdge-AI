-- ====================================================================
-- SentriAI Mini - Database Schema DDL (SQLite3)
-- Artifact: schema.sql (TASK-003, TASK-006 & CR-004 TASK-020)
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
-- 2. Polygon Zones Table (REQ-002, REQ-005, CR-001)
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
-- 3. Vehicle Whitelist & Blacklist Table (REQ-006, CR-001)
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
-- 5. Object Label Catalog (REQ-005, REQ-007, CR-001, CR-004)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS custom_labels (
    id VARCHAR(64) PRIMARY KEY,
    label_key VARCHAR(128) UNIQUE,
    label_name VARCHAR(128) NOT NULL,
    label_type VARCHAR(16) NOT NULL DEFAULT 'custom' CHECK (label_type IN ('system', 'custom')),
    category VARCHAR(64) NOT NULL DEFAULT 'custom' CHECK (category IN ('person', 'vehicle_shape', 'custom')),
    sample_count INTEGER NOT NULL DEFAULT 0 CHECK (sample_count >= 0),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    deleted_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(label_name)) > 0),
    CHECK (label_key IS NULL OR length(trim(label_key)) > 0)
);

-- --------------------------------------------------------------------
-- 5b. Dataset Sources Table (REQ-007, CR-001, CR-004)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dataset_sources (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    kind VARCHAR(16) NOT NULL CHECK (kind IN ('img', 'video')),
    url VARCHAR(512),
    storage_path VARCHAR(512),
    public_url VARCHAR(512),
    original_filename VARCHAR(255),
    mime_type VARCHAR(128) CHECK (mime_type IN ('image/jpeg', 'image/png', 'video/mp4', 'video/quicktime')),
    file_size_bytes INTEGER CHECK (file_size_bytes IS NULL OR file_size_bytes > 0),
    sha256 VARCHAR(64) CHECK (sha256 IS NULL OR length(sha256) = 64),
    duration_seconds FLOAT,
    total_frames INTEGER,
    fps FLOAT,
    width INTEGER,
    height INTEGER,
    import_status VARCHAR(32) NOT NULL DEFAULT 'ready' CHECK (import_status IN ('processing', 'ready', 'failed')),
    import_error TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (kind = 'img' OR total_frames IS NULL OR total_frames >= 0),
    CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CHECK (fps IS NULL OR fps > 0),
    CHECK (width IS NULL OR width > 0),
    CHECK (height IS NULL OR height > 0)
);

-- --------------------------------------------------------------------
-- 5c. Bounding Box Dataset Samples Table (REQ-007, CR-001, CR-004)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bbox_samples (
    id VARCHAR(64) PRIMARY KEY,
    label_id VARCHAR(64) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    frame_index INTEGER,
    frame_timestamp_seconds FLOAT,
    x FLOAT NOT NULL,
    y FLOAT NOT NULL,
    w FLOAT NOT NULL,
    h FLOAT NOT NULL,
    coordinate_space VARCHAR(32) NOT NULL DEFAULT 'percent_0_100' CHECK (coordinate_space = 'percent_0_100'),
    category VARCHAR(32) CHECK (category IN ('person', 'vehicle_shape', 'custom')),
    label_name VARCHAR(128),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES dataset_sources(id) ON DELETE CASCADE,
    CHECK (frame_index IS NULL OR frame_index >= 0),
    CHECK (frame_timestamp_seconds IS NULL OR frame_timestamp_seconds >= 0),
    CHECK (x >= 0 AND x <= 100),
    CHECK (y >= 0 AND y <= 100),
    CHECK (w > 0 AND w <= 100),
    CHECK (h > 0 AND h <= 100),
    CHECK (x + w <= 100),
    CHECK (y + h <= 100)
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_object_labels_label_key ON custom_labels(label_key);
CREATE INDEX IF NOT EXISTS idx_object_labels_active_type_key ON custom_labels(is_active, label_type, label_key);
CREATE INDEX IF NOT EXISTS idx_dataset_sources_created_at ON dataset_sources(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dataset_sources_sha256 ON dataset_sources(sha256);
CREATE INDEX IF NOT EXISTS idx_bbox_samples_label ON bbox_samples(label_id);
CREATE INDEX IF NOT EXISTS idx_bbox_samples_source ON bbox_samples(source_id);
CREATE INDEX IF NOT EXISTS idx_bbox_samples_source_frame ON bbox_samples(source_id, frame_index, created_at DESC);

-- --------------------------------------------------------------------
-- Initial Seed Data
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('1.1.0', 'Updated database schema with dataset_sources and bbox_samples for CR-001');

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('1.2.0-cr004-object-labeling', 'CR-004 real object labeling storage contract with system/custom labels, media metadata, soft delete/restore, label references, and bbox constraints');

INSERT OR IGNORE INTO cameras (id, name, location, stream_url, fps)
VALUES 
    ('GATE-01', 'Camera Cổng Ván LPR', 'Cổng Chính IN', '/videos/GATE-01.mp4', 25.0),
    ('BAI-KIEM', 'Camera Bãi Kiểm An Ninh', 'Khu Vực Bãi Kiểm', '/videos/BAI-KIEM.mp4', 25.0),
    ('XUONG-AN-NINH', 'Camera Xưởng An Ninh', 'Xưởng An Ninh Nội Bộ', '/videos/XUONG-AN-NINH.mp4', 16.0);

INSERT OR IGNORE INTO kpi_realtime_cache (id, gate_vehicles_total, gate_lpr_success, gate_lpr_failed, gate_avg_confidence, area_active_objects, area_zone_violations, area_active_machinery, area_total_zones)
VALUES ('GLOBAL_KPI', 128, 120, 8, 94.5, 14, 3, 5, 2);

INSERT OR IGNORE INTO custom_labels (id, label_key, label_name, label_type, category, sample_count, is_active)
VALUES
    ('lbl_system_container', 'container', 'Container', 'system', 'vehicle_shape', 0, 1),
    ('lbl_system_truck', 'truck', 'Xe tải', 'system', 'vehicle_shape', 0, 1),
    ('lbl_system_forklift', 'forklift', 'Xe nâng', 'system', 'vehicle_shape', 0, 1),
    ('lbl_system_crane', 'crane', 'Xe cẩu', 'system', 'vehicle_shape', 0, 1),
    ('lbl_system_car', 'car', 'Xe con', 'system', 'vehicle_shape', 0, 1),
    ('lbl_system_motorbike', 'motorbike', 'Xe máy', 'system', 'vehicle_shape', 0, 1),
    ('lbl_system_bicycle', 'bicycle', 'Xe đạp', 'system', 'vehicle_shape', 0, 1),
    ('lbl_system_person', 'person', 'Người', 'system', 'person', 0, 1);

-- Toạ độ polygon là phần trăm 0-100 của khung hình, vẽ cho bộ clip CCTV cảng
-- HATECO Hải Phòng hiện hành. Nguồn chính tắc của bộ toạ độ này là
-- backend/scripts/seed_area_demo.py (có ghi chú cách vẽ và số đo quỹ đạo);
-- sửa ở đây thì phải sửa cả bên đó, và ngược lại.
--
-- Luật: vùng lối đi bộ cấm máy móc nặng, vùng bãi/thao tác cấm phương tiện cá
-- nhân. Cố tình không cấm 'person' ở zone bãi — cảnh cảng lúc nào cũng có công
-- nhân nên cấm person sẽ biến sổ cảnh báo thành danh sách toàn 'Người'.
--
-- Xác minh bằng hình sau mỗi lần sửa:
--     .venv/Scripts/python.exe backend/scripts/render_zone_overlay.py
INSERT OR IGNORE INTO zones (id, camera_id, name, vertices, allowed_classes, forbidden_classes, color)
VALUES
    -- GATE-01 vẽ lại cho camera biển số 'Cvao-Bien-L2' (clip cắt bằng
    -- backend/scripts/prepare_gate_lpr_clip.py). Camera đặt ngang tầm cản trước và chỉ
    -- ngắm **một** làn, nên bộ này khác hẳn bộ cũ vẽ cho camera toàn cảnh hai làn.
    --
    -- 'Làn IN' bám tâm bbox xe, đo trên clip (86 detection): xe thật ở (28, 25), lúc áp
    -- sát camera kéo tới (50, 50). Biên phải dừng ở 58 để loại một 'container' đứng yên
    -- ở (65, 14) suốt clip — đó là bãi container ở hậu cảnh, không phải xe qua cổng.
    -- Biên dưới dừng ở 56 vì phần dưới khung hình chỉ là mặt đường.
    --
    -- 'Bốt kiểm soát' KHÔNG phải làn vào: tên không bắt đầu bằng "Làn IN" nên
    -- `_is_inbound_lane()` loại nó khỏi luồng LPR. Nó tồn tại để đánh dấu khu bốt bên
    -- phải, nơi bình cứu hoả và vật màu vàng trên cột hay bị nhận nhầm là tấm biển.
    --
    -- forbidden để rỗng: ở cự ly này YOLO-World gọi cùng một chiếc đầu kéo lúc là
    -- 'truck', lúc 'car', lúc 'container' (đo được cả ba trên cùng một xe). Cấm 'car'
    -- như bộ cũ sẽ sinh vi phạm giả mỗi lần nhãn dao động. Zone ở camera cổng phục vụ
    -- việc xác định xe đang ở làn vào để chạy LPR, không phải để bắt vi phạm.
    ('zA', 'GATE-01', 'Làn IN', '[{"x":0,"y":0},{"x":58,"y":0},{"x":58,"y":56},{"x":0,"y":56}]', '["container","truck","car","motorbike"]', '[]', '#30d158'),
    ('zB', 'GATE-01', 'Bốt kiểm soát', '[{"x":60,"y":0},{"x":100,"y":0},{"x":100,"y":40},{"x":60,"y":40}]', '["container","truck","car","motorbike","person"]', '[]', '#2f9bff'),
    ('zK1', 'BAI-KIEM', 'Zone bãi kiểm hoá', '[{"x":54,"y":42},{"x":89,"y":44},{"x":93,"y":78},{"x":55,"y":80}]', '["container","forklift","truck","crane","person"]', '["car","motorbike","bicycle"]', '#30D158'),
    ('zK2', 'BAI-KIEM', 'Zone làn di chuyển', '[{"x":38,"y":42},{"x":52,"y":42},{"x":40,"y":100},{"x":10,"y":100}]', '["container","forklift","truck","crane","person"]', '["car","motorbike","bicycle"]', '#FF9F0A'),
    ('zK3', 'BAI-KIEM', 'Zone bãi container', '[{"x":0,"y":40},{"x":26,"y":38},{"x":30,"y":66},{"x":0,"y":72}]', '["container","forklift","truck","crane","person"]', '["car","motorbike","bicycle"]', '#EF4444'),
    ('zX1', 'XUONG-AN-NINH', 'Zone máy móc xưởng', '[{"x":50,"y":40},{"x":99,"y":44},{"x":99,"y":92},{"x":54,"y":96}]', '["container","forklift","truck","crane","person"]', '["car","motorbike","bicycle"]', '#EF4444'),
    ('zX2', 'XUONG-AN-NINH', 'Zone lối đi bộ', '[{"x":22,"y":48},{"x":50,"y":44},{"x":54,"y":96},{"x":24,"y":100}]', '["person"]', '["forklift","crane","truck","container"]', '#30D158');

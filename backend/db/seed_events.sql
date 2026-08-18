-- SQLite Seed Events (SentriAI Mini)
-- Transferred from docs/contracts/seed_events.sql by TASK-006

INSERT OR REPLACE INTO cameras (id, name, location, stream_url) VALUES
('CAM-GATE-01', 'Camera Cổng Chính', 'Cổng Vô', 'data/sample_videos/GATE-01.mp4'),
('CAM-BAI-KIEM', 'Camera Bãi Kiểm Hàng', 'Bãi Kiểm 01', 'data/sample_videos/BAI-KIEM.mp4');

INSERT OR REPLACE INTO zones (id, camera_id, name, polygon_points, rule_type) VALUES
('ZONE-GATE-LPR', 'CAM-GATE-01', 'LPR Gate Zone', '[[100,100],[500,100],[500,400],[100,400]]', 'lpr'),
('ZONE-BAI-DENY', 'CAM-BAI-KIEM', 'Khu Vực Cấm Xe Máy', '[[50,50],[450,50],[450,350],[50,350]]', 'deny');

INSERT OR REPLACE INTO vehicles (license_plate, vehicle_type, list_type, owner_name, notes) VALUES
('29A-12345', 'xe con', 'whitelist', 'Nguyễn Văn A', 'Xe ban giám đốc'),
('30F-99999', 'xe tải', 'blacklist', 'Không rõ', 'Xe vi phạm quy định bãi');

INSERT OR REPLACE INTO events (id, camera_id, zone_id, event_type, severity, license_plate, ocr_confidence, object_class, snapshot_path, clip_path, created_at) VALUES
('EVT-001', 'CAM-GATE-01', 'ZONE-GATE-LPR', 'lpr_detected', 1, '29A-12345', 0.95, 'xe con', 'snapshots/evt001.jpg', 'clips/evt001.mp4', '2026-08-18 08:00:00'),
('EVT-002', 'CAM-GATE-01', 'ZONE-GATE-LPR', 'lpr_detected', 2, '30F-88888', 0.72, 'xe tải', 'snapshots/evt002.jpg', 'clips/evt002.mp4', '2026-08-18 08:15:00'),
('EVT-003', 'CAM-BAI-KIEM', 'ZONE-BAI-DENY', 'zone_violation', 3, '51G-77777', 0.88, 'xe máy', 'snapshots/evt003.jpg', 'clips/evt003.mp4', '2026-08-18 09:30:00');

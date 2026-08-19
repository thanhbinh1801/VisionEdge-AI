---
artifact: DATABASE-DESIGN.md
version: 1.0.0
owner: design-database
task_id: TASK-003
status: approved
updated_at: "2026-08-19T11:33:56+07:00"
linked_requirements:
  - REQ-001
  - REQ-002
  - REQ-006
  - CR-002
---

# Database & Schema Foundation Design Contract — SentriAI Mini

Tài liệu quy định kiến trúc CSDL SQLite3, thiết kế thực thể, chỉ mục, ràng buộc toàn vẹn và chiến lược migration cho hệ thống Giám sát Camera AI (SentriAI Mini - CR-002 React & YOLOv26).

---

## Traceability

Ma trận vết các yêu cầu sản phẩm và kiến trúc liên quan đến TASK-003:

| Requirement ID | Tiêu đề Yêu cầu | Bảng CSDL & Cột Liên quan | Mô tả Chi tiết |
|---|---|---|---|
| **REQ-001** | LPR Gate Monitoring | `cameras`, `events`, `vehicles` | Lưu bản ghi lượt vào cổng làn IN (GATE-01), chuỗi biển số xe `license_plate`, `confidence`, đường dẫn ảnh crop `crop_image_url`, video 10s `video_clip_url`. |
| **REQ-002** | Area Zone Monitoring | `cameras`, `zones`, `events` | Quản lý camera bãi kiểm (BAI-KIEM), tọa độ đa giác polygon `vertices` (JSON), danh sách đối tượng vi phạm `object_class`, `bbox` (JSON) và `severity_level`. |
| **REQ-006** | Vehicle Whitelist & Blacklist | `vehicles` | Lưu nhãn xe `tag_label` (`known`, `unknown`, `blacklisted`), loại xe `vehicle_type`, thời điểm ghi nhận gần nhất `last_seen_at`, tổng số lượt `total_entries`. |
| **CR-002** | React & YOLOv26 Modernization | `custom_labels`, `kpi_realtime_cache` | Lưu mẫu bbox dataset gán nhãn custom, cache 4 thẻ chỉ số KPI Recharts trực tiếp trên SQLite3. |

---

## Current Data Context

- **Database Engine**: SQLite3 v3.35+ tích hợp sẵn JSON1 extension và Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
- **Storage Strategy**: CSDL SQLite lưu dưới dạng file đơn `backend/database/sentri_ai.db`. Ảnh crop và clip MP4 10s lưu trên đĩa local (`/data/crops/`, `/data/clips/`) và đường dẫn lưu trong DB.
- **ORM / Data Access**: Python SQLAlchemy 2.0 (Async Engine) & Direct SQLite Driver cho độ trễ nhỏ hơn 5ms per query.

---

## Existing Schema Evidence

Khảo sát cấu trúc CSDL hiện tại và bằng chứng mã nguồn trong repository:
- `backend/database/` (Sẽ được khởi tạo bằng `schema.sql`).
- Định dạng dữ liệu sự kiện kế thừa từ Prototype `Intern-LPR-Gate.dc.html`.
- Các bảng được thiết kế đảm bảo tương thích 100% với các JSON Schemas từ `docs/contracts/api-schema.json` của `TASK-002`.

---

## Entities

Hệ thống bao gồm 6 thực thể CSDL chính:

### 1. `cameras`
Bảng quản lý danh sách camera stream:
- `id` (VARCHAR(32), PRIMARY KEY): Mã camera (`GATE-01`, `BAI-KIEM`).
- `name` (VARCHAR(128), NOT NULL): Tên camera hiển thị trên React UI.
- `location` (VARCHAR(255), NOT NULL): Vị trí lắp đặt.
- `stream_url` (VARCHAR(512), NOT NULL): URL RTSP hoặc đường dẫn file MP4 demo.
- `status` (VARCHAR(32), NOT NULL, DEFAULT 'online'): Trạng thái (`online`, `offline`, `degraded`).
- `fps` (FLOAT, NOT NULL, DEFAULT 10.0): Tốc độ xử lý khung hình.
- `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP).

### 2. `zones`
Bảng cấu hình vùng đa giác polygon giám sát an ninh:
- `id` (VARCHAR(64), PRIMARY KEY): Mã vùng đa giác (ví dụ: `ZONE-GATE-IN`, `ZONE-BAI-CAM`).
- `camera_id` (VARCHAR(32), NOT NULL, FOREIGN KEY -> `cameras.id` ON DELETE CASCADE).
- `name` (VARCHAR(128), NOT NULL): Tên vùng zone.
- `vertices` (JSON, NOT NULL): Mảng JSON lưu mảng các điểm `[{"x": 0.1, "y": 0.2}, ...]`.
- `allowed_classes` (JSON, NOT NULL): Mảng JSON tên các đối tượng được phép.
- `forbidden_classes` (JSON, NOT NULL): Mảng JSON tên các đối tượng cấm.
- `is_active` (BOOLEAN, NOT NULL, DEFAULT 1): Bật/tắt zone.
- `color` (VARCHAR(16), DEFAULT '#EF4444'): Mã màu hiển thị trên React SVG Canvas.
- `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP).

### 3. `vehicles`
Bảng quản lý danh sách biển số xe quen / xe lạ / blacklist:
- `id` (VARCHAR(64), PRIMARY KEY): UUID định danh xe.
- `license_plate` (VARCHAR(32), UNIQUE, NOT NULL): Chuỗi biển số xe đã đọc.
- `vehicle_type` (VARCHAR(64), DEFAULT 'car'): Loại phương tiện (`container_truck`, `truck`, `car`, `motorbike`).
- `tag_label` (VARCHAR(32), NOT NULL, DEFAULT 'unknown'): Nhãn phân loại (`known`, `unknown`, `blacklisted`).
- `crop_image_url` (VARCHAR(512)): URL ảnh crop biển số mới nhất.
- `last_seen_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP): Lần xuất hiện gần nhất.
- `total_entries` (INTEGER, DEFAULT 1): Tổng số lần xe vào cổng.
- `notes` (TEXT): Ghi chú bổ sung.

### 4. `events`
Bảng lưu vết toàn bộ sự kiện nhận diện biển số & vi phạm quy tắc zone:
- `id` (VARCHAR(64), PRIMARY KEY): UUID sự kiện.
- `timestamp` (DATETIME, NOT NULL, DEFAULT CURRENT_TIMESTAMP): Mốc thời gian phát sinh.
- `camera_id` (VARCHAR(32), NOT NULL, FOREIGN KEY -> `cameras.id`).
- `zone_id` (VARCHAR(64), FOREIGN KEY -> `zones.id` ON DELETE SET NULL).
- `lane_id` (VARCHAR(32)): Mã làn cổng (`IN_1`, `IN_2`).
- `event_type` (VARCHAR(64), NOT NULL): Loại sự kiện (`LPR_PASSAGE`, `ZONE_VIOLATION`, `RESTRICTED_ACCESS`).
- `severity_level` (INTEGER, NOT NULL, CHECK in (1, 2, 3)): Mức độ rủi ro (1: Green, 2: Yellow, 3: Red).
- `license_plate` (VARCHAR(32)): Chuỗi biển số xe (nếu có).
- `object_class` (VARCHAR(64), NOT NULL): Tên loại đối tượng YOLOv26 phát hiện.
- `confidence` (FLOAT, NOT NULL): Độ tin cậy AI (0.0 -> 1.0).
- `bbox` (JSON): Mảng JSON lưu `[x_min, y_min, x_max, y_max]`.
- `crop_image_url` (VARCHAR(512)): Đường dẫn ảnh crop bbox đối tượng.
- `video_clip_url` (VARCHAR(512)): Đường dẫn file video MP4 10s chứng cứ.

### 5. `custom_labels`
Bảng lưu các mẫu đối tượng custom đã gán nhãn trong dataset tool:
- `id` (VARCHAR(64), PRIMARY KEY): Mã nhãn custom.
- `label_name` (VARCHAR(128), UNIQUE, NOT NULL): Tên nhãn custom.
- `category` (VARCHAR(64), NOT NULL, DEFAULT 'custom'): Nhóm phân loại.
- `sample_count` (INTEGER, DEFAULT 0): Số mẫu hình ảnh/bbox đã gắn.
- `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP).
- `updated_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP).

### 6. `kpi_realtime_cache`
Bảng lưu snapshot các chỉ số thống kê KPI cho 4 thẻ Recharts trên React UI:
- `id` (VARCHAR(32), PRIMARY KEY, DEFAULT 'GLOBAL_KPI'): Mã bản ghi KPI cache.
- `gate_vehicles_total` (INTEGER, DEFAULT 0).
- `gate_lpr_success` (INTEGER, DEFAULT 0).
- `gate_lpr_failed` (INTEGER, DEFAULT 0).
- `gate_avg_confidence` (FLOAT, DEFAULT 0.0).
- `area_active_objects` (INTEGER, DEFAULT 0).
- `area_zone_violations` (INTEGER, DEFAULT 0).
- `area_active_machinery` (INTEGER, DEFAULT 0).
- `area_total_zones` (INTEGER, DEFAULT 0).
- `updated_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP).

---

## Relationships

Sơ đồ mối quan hệ giữa các thực thể (Entity-Relationship):

```
+------------------+          +------------------+          +------------------+
|     CAMERAS      | 1      * |      ZONES       | 1      * |      EVENTS      |
|------------------|<---------|------------------|<---------|------------------|
| id (PK)          |          | id (PK)          |          | id (PK)          |
| name             |          | camera_id (FK)   |          | camera_id (FK)   |
| stream_url       |          | vertices (JSON)  |          | zone_id (FK)     |
+------------------+          +------------------+          | severity_level   |
        |                                                   | license_plate    |
        | 1                                                 | video_clip_url   |
        +-------------------------------------------------->+------------------+
                                                                     |
+------------------+                                                 | * (matching plate)
|     VEHICLES     |-------------------------------------------------+
|------------------|
| id (PK)          |
| license_plate    |
| tag_label        |
+------------------+
```

---

## Invariants and Constraints

1. **Khóa chính & Khóa ngoại**: Tất cả các bảng đều sử dụng `PRIMARY KEY`. Khóa ngoại `FOREIGN KEY (camera_id)` và `FOREIGN KEY (zone_id)` được bật PRAGMA enforcement.
2. **Ràng buộc Mức độ Cảnh báo**: `severity_level CHECK (severity_level IN (1, 2, 3))`.
3. **Ràng buộc Độ tin cậy AI**: `confidence CHECK (confidence >= 0.0 AND confidence <= 1.0)`.
4. **Tính Duy nhất của Biển số**: Cột `license_plate` trong bảng `vehicles` có ràng buộc `UNIQUE` để tránh nhân bản bản ghi xe.

---

## Access Patterns and Indexes

### 1. Frequent Access Patterns
- Truy vấn danh sách sự kiện mới nhất theo thời gian giảm dần: `SELECT * FROM events ORDER BY timestamp DESC LIMIT 20;`.
- Lọc sự kiện vi phạm Mức 3 theo camera: `SELECT * FROM events WHERE camera_id = 'BAI-KIEM' AND severity_level = 3;`.
- Tra cứu biển số xe quen/lạ: `SELECT * FROM vehicles WHERE license_plate = '51H-12345';`.
- AI Chatbot Text-to-SQL query sự kiện theo khoảng thời gian: `SELECT COUNT(*) FROM events WHERE timestamp BETWEEN ? AND ?;`.

### 2. Proposed Indexes
- `idx_events_timestamp`: Index trên `events (timestamp DESC)`.
- `idx_events_camera_severity`: Index tổng hợp `events (camera_id, severity_level)`.
- `idx_events_license_plate`: Index trên `events (license_plate)`.
- `idx_vehicles_license_plate`: Index `UNIQUE` trên `vehicles (license_plate)`.
- `idx_zones_camera_id`: Index trên `zones (camera_id)`.

---

## Transaction and Concurrency

- **WAL Mode**: Kích hoạt `PRAGMA journal_mode=WAL;` cho phép đọc song song (concurrent reads) từ React Web UI mà không bị block khi Backend ghi sự kiện realtime.
- **Busy Timeout**: Thiết lập `PRAGMA busy_timeout = 5000;` để tránh lỗi `database is locked` khi có lượng sự kiện ghi dồn dập.

---

## Migration Strategy

- **Centralized Wave 1 Execution**: File DDL `schema.sql` sẽ được thực thi 1 lần duy nhất khởi tạo CSDL SQLite hoàn chỉnh trước khi phát triển các module backend ở Phase 2.
- **Version Table**: Bảng `schema_migrations` lưu vết lịch sử migration.

---

## Rollback Strategy

- Khi xảy ra sự cố migration, thực thi script rollback xóa bảng theo đúng thứ tự phụ thuộc khóa ngoại:
  ```sql
  DROP TABLE IF EXISTS kpi_realtime_cache;
  DROP TABLE IF EXISTS custom_labels;
  DROP TABLE IF EXISTS events;
  DROP TABLE IF EXISTS vehicles;
  DROP TABLE IF EXISTS zones;
  DROP TABLE IF EXISTS cameras;
  DROP TABLE IF EXISTS schema_migrations;
  ```

---

## Security and Privacy

- **Data Masking**: Biển số xe và dữ liệu cá nhân không chứa mật khẩu hay thông tin định danh nhạy cảm ngoài hình ảnh phương tiện.
- **SQL Injection Prevention**: Tất cả các truy vấn từ `api-gateway` và `llm-qa-agent` BẮT BUỘC dùng Parameterized Queries (`?` placeholders).

---

## Performance Risks

- **Dung lượng Đĩa**: Ảnh crop và video clip 10s ghi liên tục có thể làm đầy ổ đĩa local.
  - *Giải pháp*: Triển khai cronjob tự động xoá clip cũ hơn 30 ngày.
- **Tải Ghi CSDL**: Tần suất ghi 5-15 FPS nếu không qua Cooldown Engine sẽ gây trễ đĩa.
  - *Giải pháp*: Lọc Cooldown 15s trước khi ghi DB (REQ-004 & ADR-003).

---

## Applicability Checklist

- [x] Traceability complete for all linked requirements (`REQ-001`, `REQ-002`, `REQ-006`, `CR-002`).
- [x] SQLite3 engine, tables, constraints, and WAL mode defined.
- [x] Indexes defined for high-frequency queries and Text-to-SQL performance.
- [x] Centralized schema DDL `schema.sql` created for Wave 1 execution.

---

## Open Questions

Hiện tại không còn câu hỏi mở nào. Tất cả thiết kế thực thể và DDL SQL đã được định nghĩa hoàn chỉnh.

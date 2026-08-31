---
artifact: API-CONTRACT.md
version: 1.5.0
owner: design-api
status: approved
updated_at: "2026-08-27T20:10:00+07:00"
linked_requirements:
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-008
  - REQ-009
  - CR-001
  - CR-002
  - CR-003
  - CR-004
  - CR-005
  - CR-007
---

# Hợp Đồng REST API & WebSocket Event Payload (SentriAI Mini — CR-001, CR-002, CR-003, CR-004, CR-005 & CR-007)

Tài liệu quy định chuẩn hợp đồng REST API Foundation toàn cục và giao thức WebSocket real-time cho hệ thống Giám sát Camera AI (SentriAI Mini), hỗ trợ đầy đủ quy tắc nghiệp vụ CR-001 (Phân loại 8 nhóm đối tượng, Xe quen/Xe lạ, SVG Canvas 4 thao tác, BBox Dataset Collector), CR-002 (React Framework), CR-003 (Area realtime metadata lane + in-memory zone cache), CR-004 (real object labeling flow với media import, persisted bbox samples, label CRUD/soft delete/restore, và sync zone rules), CR-005 (Telegram evidence notification vi phạm khu vực), và CR-007 (YOLOv11s finetune cho Area Monitoring, threshold layering, bbox debug container, class-aware zone evaluation và optional tracking readiness).

---

## 1. Summary of REST Endpoints

| Resource | Method | Endpoint Path | Description | Access |
|---|---|---|---|---|
| **Vehicles** | `GET` | `/api/v1/vehicles` | Lấy danh sách biển số đã thu thập & trạng thái nhãn (`quen` / `la`). | Viewer / Admin |
| **Vehicles** | `PUT` | `/api/v1/vehicles/{plate}/tag` | Đổi nhãn phương tiện (`quen` $\leftrightarrow$ `la`). | Admin |
| **Zones** | `GET` | `/api/v1/zones?camera_id={id}` | Lấy danh sách Zone đa giác polygon & bảng quy tắc đối tượng được phép/cấm. | Viewer / Admin |
| **Zones** | `POST` | `/api/v1/zones` | Tạo Zone đa giác polygon mới. | Admin |
| **Zones** | `PUT` | `/api/v1/zones/{id}` | Cập nhật tọa độ đỉnh polygon (Vertex handles) hoặc đổi quy tắc loại đối tượng. | Admin |
| **Zones** | `DELETE` | `/api/v1/zones/{id}` | Xóa Zone đa giác polygon. | Admin |
| **Dataset Labels** | `GET` | `/api/v1/dataset/labels?include_deleted=false` | Lấy catalog nhãn đối tượng gồm 8 system labels và custom labels active/deleted tùy filter. | Viewer / Admin |
| **Dataset Labels** | `POST` | `/api/v1/dataset/labels` | Tạo custom label mới, uniqueness không phân biệt hoa/thường, sync vào mọi zone mặc định `forbidden`. | Admin |
| **Dataset Labels** | `PUT` | `/api/v1/dataset/labels/{label_id}` | Đổi tên/category custom label và cập nhật xuyên suốt zone rules. | Admin |
| **Dataset Labels** | `DELETE` | `/api/v1/dataset/labels/{label_id}` | Soft delete custom label nếu không còn nằm trong zone rules; system labels bị khóa. | Admin |
| **Dataset Labels** | `POST` | `/api/v1/dataset/labels/{label_id}/restore` | Restore custom label và sync lại vào mọi zone mặc định `forbidden`. | Admin |
| **Dataset Sources** | `GET` | `/api/v1/dataset/sources` | List media source đã import, có pagination và metadata file/frame. | Viewer / Admin |
| **Dataset Sources** | `POST` | `/api/v1/dataset/sources` | Upload ảnh/video bằng `multipart/form-data`; backend lưu file và metadata vào managed storage. | Admin |
| **Dataset Sources** | `GET` | `/api/v1/dataset/sources/{source_id}/frame` | Lấy JPEG frame từ imported source theo `frame_index` hoặc `timestamp`. | Viewer / Admin |
| **Dataset Samples** | `GET` | `/api/v1/dataset/samples` | List bbox samples theo `source_id`, `frame_index`, hoặc `label_id`. | Viewer / Admin |
| **Dataset Samples** | `POST` | `/api/v1/dataset/samples:batch` | Lưu batch bbox samples atomically; toàn bộ batch fail nếu có sample invalid. | Admin |
| **Dataset Samples** | `PUT` | `/api/v1/dataset/samples/{sample_id}` | Sửa bbox geometry, frame hoặc label của sample đã lưu. | Admin |
| **Dataset Samples** | `DELETE` | `/api/v1/dataset/samples/{sample_id}` | Xóa sample và recompute `sample_count` của label liên quan. | Admin |
| **Dataset Sync** | `POST` | `/api/v1/dataset/sync-zones` | Đồng bộ active custom labels vào zone rules và refresh zone cache. | Admin |
| **Events** | `GET` | `/api/v1/events?severity_level={level}` | Lấy nhật ký sự kiện LPR và vi phạm khu vực có kèm evidence fields & telegram_status. | Viewer / Admin |
| **Events Video Feed** | `GET` | `/api/v1/events/video-feed?camera_id=BAI-KIEM&conf_threshold={0..1}&show_static_containers=false` | MJPEG stream cho dashboard; `conf_threshold` là ngưỡng hiển thị bbox/debug, không tự sinh event/cảnh báo; `show_static_containers` bật bbox container/shipping_container khi debug model. | Viewer / Admin |
| **Events Evidence** | `GET` | `/api/v1/events/{event_id}/evidence` | Lấy chi tiết bằng chứng vi phạm của sự kiện gồm 10s video clip URL và nhật ký Telegram. | Viewer / Admin |
| **Alerts Test** | `POST` | `/api/v1/alerts/telegram/test` | Kiểm tra kết nối Telegram Bot API và gửi tin nhắn thử nghiệm từ Admin. | Admin |
| **Chatbot** | `POST` | `/api/v1/chatbot/query` | Truy vấn trợ lý AI tiếng Việt, trả về kết quả số liệu kèm đính kèm video clip 10s. | Viewer / Admin |

---

## 2. WebSocket Realtime Events Gateway (`/ws/v1/events`)

### 2.1 Event Types:
- `LPR_DETECTION_EVENT`: Đẩy khi phát hiện xe đi vào làn IN cổng.
- `ZONE_VIOLATION_EVENT`: Đẩy khi phát hiện đối tượng thuộc loại bị cấm hoặc xe lạ đi vào zone.
- `AREA_FRAME_METADATA`: Đẩy snapshot metadata theo frame/sampling interval cho `Area Security Dashboard`, tách biệt khỏi event lane.
- `ALERT_LEVEL_3_NOTIFICATION`: Đẩy khi vi phạm nghiêm trọng (Mức 3), kích hoạt còi bíp trình duyệt `<AudioBeepPlayer>`.

### 2.2 Lane Separation Rules
- `video stream lane`: Phục vụ render hình ảnh/video; không mang trách nhiệm phát cảnh báo hay đồng bộ event history.
- `realtime metadata lane`: Phục vụ overlay, trạng thái đối tượng, zone hit và KPI gần realtime cho `Area Security Dashboard`.
- `event/alert lane`: Chỉ phát sinh sau khi qua luật nghiệp vụ, severity classification và cooldown/dedup; được dùng cho Event Feed, audio beep và notification.
- Backward compatibility: `LPR_DETECTION_EVENT`, `ZONE_VIOLATION_EVENT` và `ALERT_LEVEL_3_NOTIFICATION` được giữ nguyên vai trò. `AREA_FRAME_METADATA` là bổ sung additive cho CR-003.
- CR-007 threshold rules: `video stream lane` có thể hiển thị detection ở ngưỡng thấp hơn để debug/quan sát. `event/alert lane` chỉ nhận object đã qua application/per-class threshold, class filter, zone evaluation theo class và kiểm tra ổn định ngắn. Việc hiển thị bbox trên MJPEG không tự kích hoạt audio, popup hoặc Telegram.

---

## 3. Data Schemas

### 3.1 Zone Config Schema
```json
{
  "id": "zK1",
  "name": "Zone bãi kiểm",
  "camera_id": "BAI-KIEM",
  "color": "#30d158",
  "polygon_points": [[54.0, 52.0], [88.0, 58.0], [92.0, 90.0], [48.0, 92.0]],
  "types": {
    "Container": 1,
    "Xe tải": 1,
    "Xe nâng": 1,
    "Xe cẩu": 0,
    "Xe con": 0,
    "Xe máy": 0,
    "Xe đạp": 0,
    "Người": 0
  }
}
```

### 3.2 Vehicle Record Schema
```json
{
  "plate": "15R-158.45",
  "type": "Container",
  "visits": 42,
  "last_visit": "2026-08-16T08:42:00+07:00",
  "tag": "quen"
}
```

### 3.3 Area Frame Metadata Schema
```json
{
  "camera_id": "BAI-KIEM",
  "frame_id": "BAI-KIEM-1724148600-000321",
  "captured_at": "2026-08-20T10:30:00+07:00",
  "zone_version": 12,
  "stream_status": "online",
  "pipeline_latency_ms": 142,
  "objects": [
    {
      "track_id": "trk-001",
      "object_class": "forklift",
      "raw_class": "forklift",
      "canonical_class": "forklift",
      "confidence": 0.94,
      "bbox": [0.18, 0.32, 0.41, 0.76],
      "bbox_xyxy_norm": [0.18, 0.32, 0.41, 0.76],
      "center_point": { "x": 0.295, "y": 0.54 },
      "zone_eval_method": "footprint_overlap",
      "zone_overlap_ratio": 0.62,
      "detection_frame_id": "BAI-KIEM-1724148600-000321",
      "zone_hits": [
        {
          "zone_id": "zone-a",
          "zone_name": "Khu xe nang",
          "rule_result": "allowed",
          "zone_eval_method": "footprint_overlap",
          "zone_overlap_ratio": 0.62
        }
      ]
    }
  ],
  "kpi_delta": {
    "area_active_objects": 4,
    "area_zone_violations": 1,
    "area_active_machinery": 2,
    "area_total_zones": 6
  }
}
```

CR-007 additive field rules:
- `bbox` giữ nguyên dạng normalized `[x_min, y_min, x_max, y_max]` để tương thích với frontend hiện tại.
- `track_id` là optional/future-compatible; consumer phải hoạt động khi field vắng mặt hoặc `null`.
- `raw_class` giữ class gốc từ YOLOv11s finetune; `canonical_class` là class chuẩn hóa để so rule zone. `object_class` giữ vai trò field tương thích và nên bằng `canonical_class`.
- `zone_eval_method` có giá trị `bottom_center`, `footprint_overlap`, `bbox_overlap_ratio`, `center_point_fallback` hoặc `none`.
- `zone_overlap_ratio` là số `[0,1]` khi method dùng overlap; `null` khi không áp dụng.
- `detection_frame_id` giúp debug tương quan giữa metadata lane và renderer.

### 3.4 Zone Cache Runtime Semantics
- Mỗi camera có một `zone_version` tăng dần sau mọi thao tác CRUD zone thành công.
- `AREA_FRAME_METADATA` phải luôn mang `zone_version` mà frame loop đang áp dụng để UI và backend có thể phát hiện cache cũ.
- API control plane cho zone vẫn đi qua REST `/api/v1/zones*`; việc refresh cache là side-effect bắt buộc của luồng ghi thành công.
- Không yêu cầu thay đổi schema DB chỉ để phục vụ cache runtime của CR-003.

### 3.5 Alert Derivation Rule
- `ALERT_LEVEL_3_NOTIFICATION` chỉ được phát từ event lane đã qua severity classification và cooldown.
- `AREA_FRAME_METADATA` có thể chứa object đang ở trạng thái vi phạm, nhưng payload này không tự tương đương với alert đã được xác nhận.

### 3.6 CR-004 Dataset Object Labeling Schemas

Tất cả JSON endpoint của `/api/v1/dataset/*` dùng envelope chuẩn:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "timestamp": "2026-08-24T19:40:41+07:00",
    "request_id": "req_abc123"
  }
}
```

#### ObjectLabel

```json
{
  "id": "lbl_system_forklift",
  "label_key": "forklift",
  "label_name": "Xe nâng",
  "label_type": "system",
  "category": "vehicle_shape",
  "sample_count": 41,
  "is_active": true,
  "deleted_at": null,
  "created_at": "2026-08-24T19:40:41+07:00",
  "updated_at": "2026-08-24T19:40:41+07:00"
}
```

Rules:
- `label_type = system`: 8 labels mặc định, không rename/delete/restore.
- `label_type = custom`: được create/rename/soft delete/restore.
- `label_key` là key chuẩn hóa để uniqueness không phân biệt hoa/thường.
- Custom label mới hoặc restore phải được sync vào mọi zone với trạng thái mặc định `forbidden`.

#### DatasetSource

```json
{
  "id": "src_01",
  "name": "yard-ca-chieu.mp4",
  "kind": "video",
  "public_url": "/media/dataset/src_01/yard-ca-chieu.mp4",
  "original_filename": "yard-ca-chieu.mp4",
  "mime_type": "video/mp4",
  "file_size_bytes": 38400000,
  "sha256": "64 lowercase hex chars",
  "duration_seconds": 272.0,
  "total_frames": 1360,
  "fps": 5.0,
  "width": 1920,
  "height": 1080,
  "import_status": "ready",
  "import_error": null,
  "created_at": "2026-08-24T19:40:41+07:00",
  "updated_at": "2026-08-24T19:40:41+07:00"
}
```

Upload source dùng `multipart/form-data`, nhận `image/jpeg`, `image/png`, `video/mp4`, `video/quicktime`, tối đa 250 MB trong CR-004. Backend chỉ lưu file trong managed media storage, không nhận hoặc trả absolute filesystem path từ browser.

#### BBoxSample

```json
{
  "id": "bbox_01",
  "label_id": "lbl_system_forklift",
  "source_id": "src_01",
  "frame_index": 45,
  "frame_timestamp_seconds": 1.5,
  "bbox": { "x": 20.5, "y": 30.0, "w": 40.0, "h": 50.0 },
  "coordinate_space": "percent_0_100",
  "label": {
    "id": "lbl_system_forklift",
    "label_key": "forklift",
    "label_name": "Xe nâng"
  },
  "created_at": "2026-08-24T19:40:41+07:00",
  "updated_at": "2026-08-24T19:40:41+07:00"
}
```

Rules:
- Batch save/update/delete samples phải atomic theo request.
- BBox dùng `percent_0_100`; `x/y` trong `[0,100]`, `w/h > 0`, và box không vượt biên canvas.
- Video samples cần `frame_index`; image source normalize về frame `0`.
- `sample_count` của label là derived data, phải recompute/adjust cùng transaction khi sample thay đổi.

#### ZoneSyncResult

```json
{
  "synced_labels": ["ao_phan_quang"],
  "affected_zones": ["zK1", "zK2", "zK3"],
  "default_rule": "forbidden",
  "cache": [
    {
      "camera_id": "BAI-KIEM",
      "zone_version": 18,
      "cache_status": "hot",
      "refreshed_at": "2026-08-24T19:40:41+07:00"
    }
  ]
}
```

### 3.7 CR-004 Error Codes

Các error code bổ sung cho dataset/object-labeling:
- `VALIDATION_ERROR`: request hợp JSON schema nhưng sai rule nghiệp vụ.
- `DUPLICATE_LABEL_NAME`: create/rename/restore trùng label name không phân biệt hoa/thường.
- `SYSTEM_LABEL_LOCKED`: cố sửa/xóa/restore system label.
- `LABEL_IN_USE_BY_ZONE`: soft delete bị chặn vì label vẫn nằm trong zone rules.
- `LABEL_INACTIVE`: annotate bằng deleted/inactive label.
- `SOURCE_NOT_READY`: source chưa ready hoặc import failed.
- `UNSUPPORTED_MEDIA_TYPE`: MIME type/codec không hỗ trợ.
- `UPLOAD_TOO_LARGE`: file vượt 250 MB.
- `FRAME_NOT_AVAILABLE`: frame index/timestamp nằm ngoài media source.
- `ZONE_CACHE_REFRESH_FAILED`: DB đã commit sync nhưng refresh runtime cache fail; client có thể retry sync.

### 3.8 CR-005 Telegram Evidence Notification Schemas & Error Codes

#### AreaViolationEvidence Payload Schema

```json
{
  "event_id": "evt_area_20260824_00192",
  "event_type": "ZONE_VIOLATION_EVENT",
  "severity_level": 3,
  "captured_at": "2026-08-24T22:30:15+07:00",
  "camera_id": "BAI-KIEM",
  "camera_name": "Camera Bãi kiểm",
  "zone_id": "zK1",
  "zone_name": "Khu vực cấm xe máy",
  "object_id": "trk_8821",
  "object_type": "motorbike",
  "object_type_name": "Xe máy",
  "violation_reason_code": "FORBIDDEN_OBJECT_IN_ZONE",
  "violation_reason": "Xe máy đi vào Khu vực cấm xe máy",
  "video_clip_url": "/media/clips/evt_area_20260824_00192.mp4",
  "video_clip_duration_seconds": 10.0,
  "snapshot_url": "/media/snapshots/evt_area_20260824_00192.jpg",
  "telegram_status": "sent",
  "telegram_error": null,
  "telegram_dispatched_at": "2026-08-24T22:30:17+07:00"
}
```

Rules:
- `captured_at`: mốc thời gian vi phạm thực tế từ frame/detector, không lấy thời điểm gửi Telegram HTTP request.
- `telegram_status`: `"pending" | "sent" | "failed" | "skipped"`.
- `telegram_error`: `null` khi gửi thành công; chuỗi mã lỗi (`BOT_TOKEN_INVALID`, `CHAT_ID_NOT_FOUND`, `TELEGRAM_API_TIMEOUT`, `RATE_LIMITED`, `VIDEO_CLIP_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`, `NETWORK_ERROR`) khi thất bại.
- Telegram Bot gửi trực tiếp tin nhắn HTML kèm file đính kèm `video_clip_url` (10s MP4 file).
- Lỗi gửi Telegram không được hủy giao dịch lưu sự kiện hoặc chặn tín hiệu WebSocket đẩy về UI Web.

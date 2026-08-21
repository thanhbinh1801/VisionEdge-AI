---
artifact: API-CONTRACT.md
version: 1.2.0
owner: design-api
status: approved
updated_at: "2026-08-20T18:10:00+07:00"
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
---

# Hợp Đồng REST API & WebSocket Event Payload (SentriAI Mini — CR-001, CR-002 & CR-003)

Tài liệu quy định chuẩn hợp đồng REST API Foundation toàn cục và giao thức WebSocket real-time cho hệ thống Giám sát Camera AI (SentriAI Mini), hỗ trợ đầy đủ quy tắc nghiệp vụ CR-001 (Phân loại 8 nhóm đối tượng, Xe quen/Xe lạ, SVG Canvas 4 thao tác, BBox Dataset Collector), CR-002 (React Framework & YOLOv26) và CR-003 (Area realtime metadata lane + in-memory zone cache).

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
| **Object Labels**| `GET` | `/api/v1/labels` | Lấy danh sách nhãn đối tượng Master Catalog (`Container`, `Xe tải`, `Xe nâng`, `Xe cẩu`, `Xe con`, `Xe máy`, `Xe đạp`, `Người` + Custom). | Viewer / Admin |
| **Object Labels**| `POST` | `/api/v1/labels` | Thêm nhãn đối tượng custom mới (Phân loại `nguoi` / `xe`). Tự động đồng bộ sang mọi Zone. | Admin |
| **Object Labels**| `DELETE` | `/api/v1/labels/{id}` | Xóa nhãn đối tượng custom. | Admin |
| **Samples** | `POST` | `/api/v1/annotation-samples` | Lưu mẫu Bounding Box đã khoanh trên hình ảnh / video frame. | Admin |
| **Events** | `GET` | `/api/v1/events?severity_level={level}` | Lấy nhật ký sự kiện LPR và sự kiện khu vực bãi kiểm. | Viewer / Admin |
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
      "confidence": 0.94,
      "bbox": [0.18, 0.32, 0.41, 0.76],
      "center_point": { "x": 0.295, "y": 0.54 },
      "zone_hits": [
        {
          "zone_id": "zone-a",
          "zone_name": "Khu xe nang",
          "rule_result": "allowed"
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

### 3.4 Zone Cache Runtime Semantics
- Mỗi camera có một `zone_version` tăng dần sau mọi thao tác CRUD zone thành công.
- `AREA_FRAME_METADATA` phải luôn mang `zone_version` mà frame loop đang áp dụng để UI và backend có thể phát hiện cache cũ.
- API control plane cho zone vẫn đi qua REST `/api/v1/zones*`; việc refresh cache là side-effect bắt buộc của luồng ghi thành công.
- Không yêu cầu thay đổi schema DB chỉ để phục vụ cache runtime của CR-003.

### 3.5 Alert Derivation Rule
- `ALERT_LEVEL_3_NOTIFICATION` chỉ được phát từ event lane đã qua severity classification và cooldown.
- `AREA_FRAME_METADATA` có thể chứa object đang ở trạng thái vi phạm, nhưng payload này không tự tương đương với alert đã được xác nhận.

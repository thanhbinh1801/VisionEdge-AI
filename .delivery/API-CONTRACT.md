---
artifact: API-CONTRACT.md
version: 1.1.0
owner: design-api
status: approved
updated_at: "2026-08-19T14:25:00+07:00"
linked_requirements:
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-008
  - REQ-009
  - CR-001
  - CR-002
---

# Hợp Đồng REST API & WebSocket Event Payload (SentriAI Mini — CR-001 & CR-002)

Tài liệu quy định chuẩn hợp đồng REST API Foundation toàn cục và giao thức WebSocket real-time cho hệ thống Giám sát Camera AI (SentriAI Mini), hỗ trợ đầy đủ quy tắc nghiệp vụ CR-001 (Phân loại 8 nhóm đối tượng, Xe quen/Xe lạ, SVG Canvas 4 thao tác, BBox Dataset Collector) và CR-002 (React Framework & YOLOv26).

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
- `ALERT_LEVEL_3_NOTIFICATION`: Đẩy khi vi phạm nghiêm trọng (Mức 3), kích hoạt còi bíp trình duyệt `<AudioBeepPlayer>`.

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

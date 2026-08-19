---
artifact: API-FOUNDATION.md
version: 1.1.0
owner: design-api
task_id: TASK-002
capability: api-foundation-design
status: approved
updated_at: "2026-08-19T14:32:30+07:00"
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

# Global REST API Foundation Contract — SentriAI Mini (CR-001 & CR-002)

Tài liệu quy định chuẩn hợp đồng REST API Foundation toàn cục và giao thức WebSocket real-time cho hệ thống Giám sát Camera AI (SentriAI Mini - CR-001 Polygon Zone & CR-002 React & YOLOv26 Modernization).

---

## Traceability

Ma trận vết các yêu cầu sản phẩm và kiến trúc kỹ thuật liên quan đến TASK-002:

| Requirement ID | Tiêu đề Yêu cầu | Mô tả Phủ trên Hợp đồng API Foundation | Endpoints / WS Event Liên quan |
|---|---|---|---|
| **REQ-001** | Nhận diện biển số Cổng (LPR) | Cung cấp thông số camera GATE-01, stream LPR realtime, dữ liệu 4 thẻ KPI Recharts, video MP4 10s và ảnh crop biển số. | `GET /api/v1/cameras/GATE-01`, `GET /api/v1/events`, `WS: LPR_DETECTION_EVENT` |
| **REQ-002** | Giám sát Khu vực & Phân loại 8 Loại Đối tượng (CR-001) | Quản lý camera BAI-KIEM, phát hiện 8 nhóm đối tượng (Container, Xe tải, Xe nâng, Xe cẩu, Xe con, Xe máy, Xe đạp, Người) bằng YOLOv26, kiểm tra Point-in-polygon và KPI bãi kiểm. | `GET /api/v1/cameras/BAI-KIEM`, `GET /api/v1/zones`, `WS: ZONE_VIOLATION_EVENT` |
| **REQ-003** | Phân cấp Mức độ Cảnh báo | Phân loại 3 cấp độ: Mức 1 (Xanh - Xe quen/Được phép), Mức 2 (Vàng - Xe lạ), Mức 3 (Đỏ - Vi phạm zone cấm). | `GET /api/v1/events?severity_level={1|2|3}`, WebSocket Badge payloads |
| **REQ-005** | Cấu hình Zone Đa giác 4 thao tác (CR-001) | Hỗ trợ CRUD đa giác polygon SVG Canvas (thêm góc, kéo đỉnh, kéo điểm giữa cạnh, kéo thân), bật/tắt quyền theo 8 loại xe/đối tượng qua React UI `<PolygonZoneEditor>`. | `GET /api/v1/zones`, `POST /api/v1/zones`, `PUT /api/v1/zones/{id}`, `DELETE /api/v1/zones/{id}` |
| **REQ-006** | Quản lý Biển số Xe quen / Xe lạ (CR-001) | Tra cứu và 1-click gán nhãn Xe quen (`known` - đã xác thực) / Xe lạ (`unknown` - chưa ghi nhận) qua React Data Table `<VehicleTagTable>`. | `GET /api/v1/vehicles`, `PUT /api/v1/vehicles/{plate_number}/tag`, `GET /api/v1/vehicles/stats` |
| **REQ-007** | Tool Gắn nhãn Mẫu BBox Custom & Sync Zone (CR-001) | Quản lý import frame/ảnh, khoanh BBox tương tác (`<DatasetAnnotator>`), lưu batch mẫu đã gắn, và tự động đồng bộ nhãn mới sang tất cả các zone. | `GET /api/v1/dataset/sources`, `GET /api/v1/dataset/samples`, `POST /api/v1/dataset/samples`, `DELETE /api/v1/dataset/samples/{id}`, `POST /api/v1/dataset/sync-zones`, `WS: DATASET_SAMPLE_SYNC_EVENT` |
| **REQ-008** | AI Assistant Hỏi đáp Sự kiện | REST endpoint cho Chatbot tiếng Việt (Text-to-SQL query), trả về kết quả số liệu kèm đính kèm trình phát `<VideoModal>` clip 10s. | `POST /api/v1/chatbot/query` |
| **REQ-009** | Cảnh báo Tức thì Đa kênh | Đẩy sự kiện Mức 3 qua WebSocket tới React UI (phát `<AudioBeepPlayer>`) và thông báo Telegram Bot đính kèm ảnh crop. | `WS: ALERT_LEVEL_3_NOTIFICATION` |
| **CR-001** | Quy tắc Zone & BBox Dataset Samples | Phân định 8 loại đối tượng, nhãn Xe quen / Xe lạ, đa giác SVG Canvas 4 thao tác, và tự động đồng bộ nhãn custom. | REST APIs `/zones`, `/vehicles`, `/dataset/*` & WebSocket events |
| **CR-002** | React SPA & YOLOv26 Modernization | Đảm bảo kiểu dữ liệu TypeScript & JSON Schema tương thích 100% với Vite + React SPA Client Hooks và FastAPI Backend. | Toàn bộ REST APIs & WebSocket payloads |

---

## Naming and Resource Conventions

### 1. URL Path Structure
Tất cả các tài nguyên REST API tuân theo cấu trúc URL chuẩn mực:
- **Base REST Path**: `/api/v1`
- **Base WebSocket Path**: `/ws/v1/events`
- **Format**: `kebab-case` cho URL paths (ví dụ: `/api/v1/chatbot/query`, `/api/v1/dataset/sync-zones`).
- **Resource Plurality**: Danh từ số nhiều cho REST Resources (`/cameras`, `/zones`, `/vehicles`, `/events`, `/dataset/samples`).

### 2. Standard HTTP Methods
- `GET`: Truy vấn tài nguyên (Idempotent & Safe).
- `POST`: Tạo mới tài nguyên hoặc thực thi tác vụ tính toán / batch action (Non-idempotent).
- `PUT`: Cập nhật toàn bộ tài nguyên (Idempotent).
- `PATCH`: Cập nhật một phần tài nguyên.
- `DELETE`: Xóa tài nguyên (Idempotent).

### 3. Chuẩn hóa Enum Phân loại 8 Đối tượng & Nhãn Phương tiện (CR-001)
- **8 Object Types**:
  - `container`: Xe container
  - `truck`: Xe tải
  - `forklift`: Xe nâng
  - `crane`: Xe cẩu
  - `car`: Xe con
  - `motorbike`: Xe máy
  - `bicycle`: Xe đạp
  - `person`: Người
- **Vehicle Tag Labels**:
  - `known`: Xe quen (Đã xác thực / Được phép)
  - `unknown`: Xe lạ (Chưa ghi nhận / Cần rà soát)

---

## Authentication and Authorization

### 1. Authentication Scheme
- **REST Endpoints**: Sử dụng `Authorization: Bearer <jwt_token>` header cho người dùng giao diện Web UI hoặc `X-API-Key: <api_key>` cho tích hợp hệ thống/bot.
- **WebSocket Gateway**: Truyền Token qua Query Parameter lúc thiết lập Handshake: `ws://<host>/ws/v1/events?token=<jwt_token>` hoặc header `Sec-WebSocket-Protocol`.

### 2. Role-Based Access Control (RBAC) Matrix

| Role | Mô tả | Quyền hạn REST / WS |
|---|---|---|
| `Viewer` | Nhân viên an ninh / Bảo vệ | Read-only trên `/cameras`, `/events`, `/kpi/stats`, `/chatbot/query`, `/vehicles`, và nhận tin nhắn WebSocket real-time. |
| `Admin` | Quản trị viên hệ thống | Toàn quyền CRUD trên `/zones`, `/vehicles/{plate}/tag`, `/dataset/*` (Annotator samples & Sync), và cấu hình hệ thống. |

---

## Request and Response Conventions

### 1. Standard Response Envelope
Tất cả câu trả lời từ REST API (thành công hoặc thất bại) BẮT BUỘC được bọc trong Response Envelope thống nhất:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "timestamp": "2026-08-19T14:32:30+07:00",
    "request_id": "req-9842a8b3-1e9a-4c2d"
  }
}
```

### 2. Standard TypeScript Definitions for Contracts

```typescript
export type ObjectType = 
  | 'container'
  | 'truck'
  | 'forklift'
  | 'crane'
  | 'car'
  | 'motorbike'
  | 'bicycle'
  | 'person';

export type VehicleTagLabel = 'known' | 'unknown';

export interface Point2D {
  x: number; // Percentage 0.0 - 100.0
  y: number; // Percentage 0.0 - 100.0
}

export interface ZoneConfig {
  id: string;
  camera_id: 'BAI-KIEM' | 'GATE-01';
  name: string;
  vertices: Point2D[];
  allowed_object_types: ObjectType[];
  prohibited_object_types: ObjectType[];
  is_active: boolean;
  color?: string;
}

export interface BBoxSample {
  id: string;
  label_id: string;
  source_id: string;
  frame_index?: number;
  x: number;
  y: number;
  w: number;
  h: number;
  category: 'person' | 'vehicle_shape';
  label_name: string;
  created_at: string;
}
```

---

## Error Model

### 1. Unified Error Payload
Khi trường `success` là `false`, đối tượng `error` sẽ chứa thông tin mã lỗi chuẩn và chi tiết phục vụ debug:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_ZONE_POLYGON",
    "message": "Zone đa giác SVG phải có ít nhất 3 đỉnh hợp lệ.",
    "details": [
      {
        "field": "vertices",
        "issue": "Mảng vertices chỉ chứa 2 điểm."
      }
    ]
  },
  "meta": {
    "timestamp": "2026-08-19T14:32:30+07:00",
    "request_id": "req-err-77123"
  }
}
```

### 2. Standard Error Codes & HTTP Status Mapping

| Error Code | HTTP Status | Mô tả Chi tiết |
|---|---|---|
| `BAD_REQUEST` | 400 | Tham số đầu vào không đúng định dạng. |
| `UNAUTHORIZED` | 401 | Thiếu hoặc Token không hợp lệ. |
| `FORBIDDEN` | 403 | Tài khoản không có quyền thực thi thao tác Admin. |
| `NOT_FOUND` | 404 | Tài nguyên (Camera, Zone, Event, BBox Sample) không tồn tại. |
| `INVALID_ZONE_POLYGON` | 422 | Đa giác polygon vẽ trên SVG Canvas bị lỗi hình học (cắt nhau hoặc < 3 đỉnh). |
| `COOLDOWN_ACTIVE` | 429 | Sự kiện nằm trong cửa sổ Cooldown 15s bị bỏ qua. |
| `INTERNAL_SERVER_ERROR` | 500 | Lỗi hệ thống nội bộ từ FastAPI Server. |
| `AI_MODEL_UNAVAILABLE` | 503 | Mô hình YOLOv26 / OCR Engine đang bận hoặc gặp sự cố. |

---

## Pagination Filtering and Sorting

### 1. Standard Query Parameters
Mọi REST Endpoint trả về danh sách hỗ trợ các query parameters sau:

| Parameter | Type | Default | Mô tả |
|---|---|---|---|
| `page` | integer | 1 | Số trang cần truy vấn (>= 1). |
| `limit` | integer | 20 | Số lượng bản ghi trên một trang (Max: 100). |
| `sort_by` | string | `timestamp` | Trường dùng để sắp xếp (`timestamp`, `severity_level`, `created_at`). |
| `order` | string | `desc` | Thứ tự sắp xếp (`asc` hoặc `desc`). |
| `camera_id` | string | null | Lọc theo mã camera (`GATE-01`, `BAI-KIEM`). |
| `tag_label` | string | null | Lọc nhãn xe (`known` hoặc `unknown`). |
| `object_class` | string | null | Lọc theo 8 loại đối tượng (`container`, `forklift`, ...). |
| `severity_level`| integer | null | Lọc theo mức độ rủi ro (1: Green, 2: Yellow, 3: Red). |
| `start_time` | string | null | Mốc thời gian bắt đầu (ISO-8601). |
| `end_time` | string | null | Mốc thời gian kết thúc (ISO-8601). |

---

## Versioning and Compatibility

### 1. Semantic Versioning
- **Major Versioning**: Đưa trực tiếp vào URI Path (`/api/v1/`, `/ws/v1/`). Nâng cấp v2 khi có Breaking Changes trong cấu trúc Schema.
- **Minor / Patch Updates**: Không thay đổi URI path. Các trường bổ sung mới trong Response Envelope không làm hỏng Client cũ (Backward Compatible).

### 2. Client Resilience Rules
- Client React UI BẮT BUỘC bỏ qua các trường dữ liệu mới xuất hiện trong JSON mà Client chưa đăng ký (Ignore Unknown Fields).

---

## Idempotency Audit and Security

### 1. Idempotency Key Header
Các yêu cầu ghi dữ liệu nhạy cảm hoặc tạo lệnh mới hỗ trợ Header `X-Idempotency-Key: <unique_uuid>` để tránh ghi trùng lặp khi mạng bị chập chờn.

### 2. CORS Policy & Input Sanitization
- API Gateway chỉ chấp nhận CORS từ Origin của React Web UI.
- Tất cả câu lệnh truy vấn Text-to-SQL trong `/api/v1/chatbot/query` BẮT BUỘC qua lớp kiểm duyệt SQLAlchemy Read-Only View để chống tấn công SQL Injection.

---

## Extension Rules

### 1. Custom Metadata Extension
Mọi tài nguyên (`Zone`, `Event`, `VehicleTag`, `BBoxSample`) đều có trường `custom_attributes: Record<string, any>` dạng JSON key-value linh hoạt để mở rộng thuộc tính nghiệp vụ mà không cần thay đổi CSDL schema.

### 2. Decoupled AI Pipeline Events
Cấu trúc Payload WebSocket được thiết kế dạng Pub/Sub Event Bus độc lập, cho phép bóc tách `ai-vision-pipeline` hoặc `alert-dispatcher` thành các Microservices độc lập trong tương lai.

---

## Open Questions

Hiện tại không còn câu hỏi mở nào. Tất cả các quy tắc nghiệp vụ về 8 loại đối tượng, nhãn Xe quen / Xe lạ, Polygon Zone 4 thao tác, BBox Dataset Annotator Samples và WebSocket real-time payloads đã được định nghĩa hoàn chỉnh và sẵn sàng triển khai.

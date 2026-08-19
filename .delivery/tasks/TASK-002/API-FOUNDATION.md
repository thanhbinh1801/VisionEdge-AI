---
artifact: API-FOUNDATION.md
version: 1.0.0
owner: design-api
task_id: TASK-002
capability: api-foundation-design
status: approved
updated_at: "2026-08-19T11:23:31+07:00"
linked_requirements:
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-005
  - REQ-008
  - REQ-009
  - CR-002
---

# Global REST API Foundation Contract — SentriAI Mini

Tài liệu quy định chuẩn hợp đồng REST API Foundation toàn cục và giao thức WebSocket real-time cho hệ thống Giám sát Camera AI (SentriAI Mini - CR-002 React & YOLOv26).

---

## Traceability

Ma trận vết các yêu cầu sản phẩm và kiến trúc kỹ thuật liên quan đến TASK-002:

| Requirement ID | Tiêu đề Yêu cầu | Mô tả Phủ trên Hợp đồng API Foundation | Endpoints / WS Event Liên quan |
|---|---|---|---|
| **REQ-001** | Nhận diện biển số Cổng (LPR) | Cung cấp thông số camera GATE-01, stream LPR realtime, dữ liệu 4 thẻ KPI Recharts, video MP4 10s và ảnh crop biển số. | `GET /api/v1/cameras/GATE-01`, `GET /api/v1/events`, `WS: LPR_DETECTION_EVENT` |
| **REQ-002** | Giám sát Khu vực & Quy tắc Zone | Quản lý thông số camera BAI-KIEM, phát hiện 8 loại đối tượng bằng YOLOv26, kiểm tra Point-in-polygon và KPI bãi kiểm. | `GET /api/v1/cameras/BAI-KIEM`, `GET /api/v1/zones`, `WS: ZONE_VIOLATION_EVENT` |
| **REQ-003** | Phân cấp Mức độ Cảnh báo | Phân loại 3 cấp độ: Mức 1 (Xanh - Xe quen/Được phép), Mức 2 (Vàng - Xe lạ), Mức 3 (Đỏ - Vi phạm zone cấm). | `GET /api/v1/events?severity_level={1|2|3}`, WebSocket Badge payloads |
| **REQ-005** | Cấu hình Zone Đa giác | Hỗ trợ CRUD đa giác polygon SVG Canvas, bật/tắt quyền theo loại xe/đối tượng qua React UI `<PolygonZoneEditor>`. | `GET /api/v1/zones`, `POST /api/v1/zones`, `PUT /api/v1/zones/{id}`, `DELETE /api/v1/zones/{id}` |
| **REQ-008** | AI Assistant Hỏi đáp Sự kiện | REST endpoint cho Chatbot tiếng Việt (Text-to-SQL query), trả về kết quả số liệu kèm đính kèm trình phát `<VideoModal>` clip 10s. | `POST /api/v1/chatbot/query` |
| **REQ-009** | Cảnh báo Tức thì Đa kênh | Đẩy sự kiện Mức 3 qua WebSocket tới React UI (phát `<AudioBeepPlayer>`) và thông báo Telegram Bot đính kèm ảnh crop. | `WS: ALERT_LEVEL_3_NOTIFICATION` |
| **CR-002** | React SPA & YOLOv26 Modernization | Đảm bảo kiểu dữ liệu TypeScript & JSON Schema tương thích 100% với Vite + React SPA Client Hooks và FastAPI Backend. | Toàn bộ REST APIs & WebSocket payloads |

---

## Naming and Resource Conventions

### 1. URL Path Structure
Tất cả các tài nguyên REST API tuân theo cấu trúc URL chuẩn mực:
- **Base REST Path**: `/api/v1`
- **Base WebSocket Path**: `/ws/v1/events`
- **Format**: `kebab-case` cho URL paths (ví dụ: `/api/v1/chatbot/query`, `/api/v1/kpi/stats`).
- **Resource Plurality**: Danh từ số nhiều cho REST Resources (`/cameras`, `/zones`, `/vehicles`, `/events`, `/labels`).

### 2. Standard HTTP Methods
- `GET`: Truy vấn tài nguyên (Idempotent & Safe).
- `POST`: Tạo mới tài nguyên hoặc thực thi tác vụ tính toán (Non-idempotent).
- `PUT`: Cập nhật toàn bộ tài nguyên (Idempotent).
- `PATCH`: Cập nhật một phần tài nguyên.
- `DELETE`: Xóa tài nguyên (Idempotent).

### 3. Payload Property Naming
Dữ liệu JSON trong Body và Parameters sử dụng quy chuẩn `snake_case` ở phía Backend Python/FastAPI, và được map tương ứng sang `camelCase` hoặc giữ nguyên `snake_case` trong TypeScript Type Interfaces chuẩn.

---

## Authentication and Authorization

### 1. Authentication Scheme
- **REST Endpoints**: Sử dụng `Authorization: Bearer <jwt_token>` header cho người dùng giao diện Web UI hoặc `X-API-Key: <api_key>` cho tích hợp hệ thống/bot.
- **WebSocket Gateway**: Truyền Token qua Query Parameter lúc thiết lập Handshake: `ws://<host>/ws/v1/events?token=<jwt_token>` hoặc header `Sec-WebSocket-Protocol`.

### 2. Role-Based Access Control (RBAC) Matrix

| Role | Mô tả | Quyền hạn REST / WS |
|---|---|---|
| `Viewer` | Nhân viên an ninh / Bảo vệ | Read-only trên `/cameras`, `/events`, `/kpi/stats`, `/chatbot/query`, và nhận tin nhắn WebSocket real-time. |
| `Admin` | Quản trị viên hệ thống | Toàn quyền CRUD trên `/zones`, `/vehicles` (Whitelist/Blacklist), `/labels` (Dataset custom), và cấu hình hệ thống. |

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
    "timestamp": "2026-08-19T11:17:50+07:00",
    "request_id": "req-9842a8b3-1e9a-4c2d"
  }
}
```

### 2. Paginated Response Envelope
Đối với các API danh sách (`/events`, `/vehicles`), trường `meta` tự động bổ sung thông tin phân trang:

```json
{
  "success": true,
  "data": [ ... ],
  "error": null,
  "meta": {
    "timestamp": "2026-08-19T11:17:50+07:00",
    "request_id": "req-9842a8b3-1e9a-4c2d",
    "page": 1,
    "limit": 20,
    "total_items": 142,
    "total_pages": 8
  }
}
```

### 3. TypeScript Type Definition for Client Apps
```typescript
export interface ApiResponseEnvelope<T> {
  success: boolean;
  data: T | null;
  error: ApiErrorPayload | null;
  meta: ApiMetaPayload;
}

export interface ApiMetaPayload {
  timestamp: string;
  request_id: string;
  page?: number;
  limit?: number;
  total_items?: number;
  total_pages?: number;
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
    "message": "Zone polygon đa giác phải có ít nhất 3 đỉnh hợp lệ.",
    "details": [
      {
        "field": "vertices",
        "issue": "Mảng vertices chỉ chứa 2 điểm."
      }
    ]
  },
  "meta": {
    "timestamp": "2026-08-19T11:17:50+07:00",
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
| `NOT_FOUND` | 404 | Tài nguyên (Camera, Zone, Event) không tồn tại. |
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
Mọi tài nguyên (`Zone`, `Event`, `VehicleTag`) đều có trường `custom_attributes: Record<string, any>` dạng JSON key-value linh hoạt để mở rộng thuộc tính nghiệp vụ mà không cần thay đổi CSDL schema.

### 2. Decoupled AI Pipeline Events
Cấu trúc Payload WebSocket được thiết kế dạng Pub/Sub Event Bus độc lập, cho phép bóc tách `ai-vision-pipeline` hoặc `alert-dispatcher` thành các Microservices độc lập trong tương lai.

---

## Open Questions

Hiện tại không còn câu hỏi mở nào. Tất cả các yêu cầu về REST Envelope, Error Codes, WebSocket real-time payloads và phân quyền RBAC đã được định nghĩa hoàn chỉnh và sẵn sàng triển khai.

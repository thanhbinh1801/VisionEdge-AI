---
artifact: API-CONTRACT.md
version: "1.0"
owner: design-api
status: approved
updated_at: "2026-08-24T22:43:00+07:00"
task_id: TASK-026
depends_on: [TASK-PACKET.md, REQUIREMENTS.md, DOMAIN-MODEL.md, API-CONTRACT.md, TASK-016]
---

# TASK-026 Hợp đồng API Event/Alert Evidence cho Telegram CR-005

Tài liệu thiết kế hợp đồng API tính năng và cấu trúc bằng chứng sự kiện (Event/Alert Evidence Contract) cho tính năng thông báo Telegram vi phạm an ninh khu vực (CR-005), tích hợp nhất quán giữa Event Feed, AI Assistant và Telegram Dispatcher.

---

## Traceability

- **REQ-002**: Đảm bảo event vi phạm an ninh khu vực (`ZONE_VIOLATION_EVENT`) mang đầy đủ mốc thời gian vi phạm phát hiện thực tế (`captured_at`), mã/tên camera (`camera_id`, `camera_name`), mã/tên khu vực (`zone_id`, `zone_name`), loại đối tượng (`object_type`), lý do vi phạm (`violation_reason`), và URL clip chứng cứ 10s MP4.
- **REQ-003**: Duy trì Mức độ nghiêm trọng Mức 3 (`severity_level = 3`) cho các sự kiện vi phạm khu vực cấm làm điều kiện kích hoạt cảnh báo Telegram và còi bíp audio trên web.
- **REQ-004**: Đảm bảo thông báo Telegram chỉ phát sinh từ event lane đã qua bộ lọc suy hao/khử trùng lặp (cooldown/deduplication), tránh gửi lặp lại tin nhắn Telegram cho cùng một vi phạm đang tiếp diễn trong khoảng thời gian cooldown.
- **REQ-008**: Chuẩn hóa đính kèm video clip chứng cứ 10s MP4 (`video_clip_url`, `video_clip_duration_seconds`) dùng chung giữa Telegram Notification Dispatcher và AI Chatbot Assistant.
- **REQ-009**: Đáp ứng tiêu chí nghiệm thu CR-005 bằng cách gửi trực tiếp video clip 10s MP4 qua Telegram Bot API kèm tin nhắn có cấu trúc chuẩn 5 trường thông tin (thời gian vi phạm đúng, camera, zone, loại đối tượng, lý do vi phạm).
- **CR-005**: Mở rộng hợp đồng API sự kiện và cảnh báo toàn cục mà không làm gián đoạn các API hiện có hay làm gián đoạn luồng xử lý chính khi Telegram gặp sự cố mạng/bot token.

---

## Resources and Operations

Mọi API quản lý sự kiện và cảnh báo tuân thủ chuẩn REST envelope toàn cục:

```ts
type ApiResponse<T> =
  | { success: true; data: T; error: null; meta: MetaPayload }
  | { success: false; data: null; error: ErrorPayload; meta: MetaPayload };
```

Danh sách các tài nguyên và thao tác API liên quan đến Event Evidence & Telegram Dispatcher:

| Phương thức | Đường dẫn (Endpoint Path) | Mã trạng thái | Payload dữ liệu trả về | Mô tả nghiệp vụ |
|---|---|---:|---|---|
| `GET` | `/api/v1/events` | 200 | `{ items: AreaViolationEventPayload[], page, limit, total_items, total_pages }` | Truy vấn nhật ký sự kiện LPR & vi phạm khu vực có lọc theo `event_type`, `severity_level`, `camera_id`, `telegram_status`. |
| `GET` | `/api/v1/events/{event_id}/evidence` | 200 | `{ evidence: AreaViolationEvidenceDetail }` | Lấy chi tiết bằng chứng vi phạm của một sự kiện gồm mốc thời gian frame, video clip 10s MP4 và nhật ký gửi Telegram. |
| `POST` | `/api/v1/alerts/telegram/test` | 200 | `{ success: boolean, message: string, bot_username: string }` | Lệnh kiểm tra kết nối Telegram Bot API và cấu hình `chat_id` từ phía quản trị viên. |

Giao thức WebSocket Gateway `/ws/v1/events` đẩy sự kiện thời gian thực:
- `ZONE_VIOLATION_EVENT`: Đẩy sự kiện vi phạm khu vực bổ sung các trường evidence mới (`violation_reason`, `object_type_name`, `video_clip_url`, `telegram_status`).
- `ALERT_LEVEL_3_NOTIFICATION`: Đẩy tín hiệu cảnh báo Mức 3 kèm payload tin nhắn gửi Telegram để UI hiển thị popup/audio beep đồng bộ với Telegram dispatch.

---

## Request Contracts

### 1. Request Query & Path Parameters cho REST Events

- `event_id`: Chuỗi định danh sự kiện (ví dụ: `evt_area_20260824_00192`), dạng string không rỗng, tối đa 96 ký tự.
- `event_type`: Chuỗi phân loại event (ví dụ: `ZONE_VIOLATION_EVENT`, `LPR_DETECTION_EVENT`).
- `severity_level`: Số nguyên đại diện mức độ nghiêm trọng (`1`: Thông tin, `2`: Cảnh báo, `3`: Nghiêm trọng).
- `camera_id`: Chuỗi mã camera (ví dụ: `BAI-KIEM`, `CONG-CHINH`).
- `telegram_status`: Chuỗi lọc trạng thái gửi Telegram (`pending`, `sent`, `failed`, `skipped`).
- `from_time` / `to_time`: Mốc thời gian ISO 8601 dùng để lọc sự kiện theo khoảng thời gian phát hiện.
- `page`: Số trang (integer >= 1, mặc định `1`).
- `limit`: Số bản ghi mỗi trang (integer từ 1 đến 100, mặc định `50`).

### 2. Request Body cho Test Telegram Config (`POST /api/v1/alerts/telegram/test`)

```json
{
  "bot_token": "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
  "chat_id": "-1001234567890",
  "custom_message": "Kiểm tra kết nối Telegram Bot từ SentriAI Mini"
}
```

---

## Response Contracts

### 1. Schemas Dữ liệu TypeScript / Zod cho Event Evidence & Telegram Status

```ts
import { z } from 'zod';

// Phân loại trạng thái gửi Telegram
export const TelegramStatusSchema = z.enum(['pending', 'sent', 'failed', 'skipped']);
export type TelegramStatus = z.infer<typeof TelegramStatusSchema>;

// Mã lỗi chi tiết khi gửi Telegram thất bại
export const TelegramErrorCodeSchema = z.enum([
  'BOT_TOKEN_INVALID',
  'CHAT_ID_NOT_FOUND',
  'TELEGRAM_API_TIMEOUT',
  'RATE_LIMITED',
  'VIDEO_CLIP_UNAVAILABLE',
  'PAYLOAD_TOO_LARGE',
  'NETWORK_ERROR'
]);
export type TelegramErrorCode = z.infer<typeof TelegramErrorCodeSchema>;

// Payload thông tin bằng chứng vi phạm đầy đủ
export const AreaViolationEvidenceSchema = z.object({
  event_id: z.string(),
  event_type: z.literal('ZONE_VIOLATION_EVENT'),
  severity_level: z.number().int().min(1).max(3),
  captured_at: z.string().datetime(), // Mốc thời gian phát hiện vi phạm thực tế từ frame
  camera_id: z.string(),
  camera_name: z.string(),
  zone_id: z.string(),
  zone_name: z.string(),
  object_id: z.string(),
  object_type: z.string(), // e.g. "motorbike", "person", "forklift", "truck"
  object_type_name: z.string(), // e.g. "Xe máy", "Người", "Xe nâng", "Xe tải"
  violation_reason_code: z.string(), // e.g. "FORBIDDEN_OBJECT_IN_ZONE"
  violation_reason: z.string(), // e.g. "Xe máy đi vào Khu vực cấm xe máy"
  video_clip_url: z.string().url().or(z.string().startsWith('/media/')),
  video_clip_duration_seconds: z.number().positive(),
  snapshot_url: z.string().url().or(z.string().startsWith('/media/')),
  telegram_status: TelegramStatusSchema,
  telegram_error: TelegramErrorCodeSchema.nullable(),
  telegram_dispatched_at: z.string().datetime().nullable()
});

export type AreaViolationEvidence = z.infer<typeof AreaViolationEvidenceSchema>;
```

### 2. Cấu trúc Mẫu Tin nhắn Telegram (Telegram Message Template)

Nội dung tin nhắn Telegram gửi đi qua Telegram Bot API (`sendVideo` endpoint) sử dụng định dạng HTML:

```html
⚠️ <b>CẢNH BÁO VI PHẠM AN NINH KHU VỰC</b> ⚠️

⏰ <b>Thời gian:</b> 2026-08-24 22:30:15 (+07:00)
📹 <b>Camera:</b> Camera Bãi kiểm (BAI-KIEM)
📍 <b>Khu vực (Zone):</b> Khu vực cấm xe máy (zK1)
🚗 <b>Đối tượng:</b> Xe máy (motorbike)
❗ <b>Lý do vi phạm:</b> Xe máy đi vào Khu vực cấm xe máy

🎥 <i>Video clip chứng cứ 10s đính kèm bên dưới.</i>
```

Khi gửi, file MP4 tương ứng với `video_clip_url` sẽ được upload trực tiếp làm đính kèm video của tin nhắn Telegram.

### 3. Cấu trúc Response Chi tiết Evidence (`GET /api/v1/events/{event_id}/evidence`)

```json
{
  "success": true,
  "data": {
    "evidence": {
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
  },
  "error": null,
  "meta": {
    "timestamp": "2026-08-24T22:43:00+07:00",
    "request_id": "req_ev_99218"
  }
}
```

---

## Validation

### Các Quy tắc Kiểm tra Hợp lệ (Validation Rules)

1. **Ràng buộc Mốc thời gian Vi phạm (`captured_at`)**:
   - Mốc thời gian `captured_at` bắt buộc phải là thời điểm ghi nhận frame vi phạm từ camera/pipeline, không được dùng mốc thời gian hệ thống tại thời điểm phát HTTP request tới Telegram API.
2. **Kiểm tra File Video Clip Chứng cứ 10s**:
   - `video_clip_url` phải trỏ tới file MP4 có thực trên hệ thống lưu trữ media backend.
   - Thời lượng clip tiêu chuẩn là 10.0 giây (khoảng 5s trước vi phạm và 5s sau vi phạm). Trong trường hợp video nguồn bắt đầu muộn hoặc kết thúc sớm, thời lượng clip được phép ngắn hơn 10s nhưng không được bằng 0 giây.
3. **Độ tương thích và Quy tắc Khử trùng lặp (Deduplication / Cooldown)**:
   - Chỉ duy nhất sự kiện vi phạm đầu tiên vượt qua bộ lọc Cooldown (ví dụ: 60s) mới sinh lệnh gửi Telegram và cắt clip 10s đại diện. Các vi phạm liên tục tiếp theo trong cửa sổ Cooldown không sinh tin nhắn Telegram mới.
4. **Không cô lập lây lan Lỗi (Non-blocking Isolation)**:
   - Nếu việc gửi tin nhắn Telegram thất bại (do sai Bot Token, mất mạng, Telegram API bị rate limit), backend phải ghi nhận `telegram_status: "failed"` và `telegram_error`, đồng thời vẫn ghi thành công sự kiện vi phạm vào DB và phát tín hiệu WebSocket về UI. Lỗi Telegram không được làm crash pipeline hay rollback giao dịch lưu sự kiện.

---

## Error Model

Các mã lỗi API chuẩn liên quan đến Event Evidence & Telegram Alert Dispatcher:

```ts
export const ApiErrorCodeSchema = z.enum([
  'EVENT_NOT_FOUND',
  'TELEGRAM_CONFIG_INVALID',
  'TELEGRAM_DISPATCH_FAILED',
  'CLIP_NOT_FOUND',
  'VALIDATION_ERROR',
  'UNAUTHORIZED',
  'INTERNAL_SERVER_ERROR'
]);
```

### Chi tiết các mã lỗi đặc thù CR-005:

- `EVENT_NOT_FOUND`: Mã sự kiện `event_id` không tồn tại trong hệ thống. (HTTP Status `404`).
- `TELEGRAM_CONFIG_INVALID`: Bot token hoặc Chat ID chưa được cấu hình hoặc cấu hình sai cú pháp. (HTTP Status `400`).
- `TELEGRAM_DISPATCH_FAILED`: Lỗi khi gửi tin nhắn Telegram (chi tiết nằm trong `telegram_error`). (HTTP Status `502` / Recorded status).
- `CLIP_NOT_FOUND`: File video clip chứng cứ 10s chưa được khởi tạo thành công hoặc đã bị dọn dẹp. (HTTP Status `404`).

Cấu trúc Error Payload tiêu chuẩn:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "TELEGRAM_CONFIG_INVALID",
    "message": "Cấu hình Telegram Bot Token hoặc Chat ID không hợp lệ.",
    "details": [
      { "field": "bot_token", "issue": "Token format is invalid" }
    ]
  },
  "meta": {
    "timestamp": "2026-08-24T22:43:00+07:00",
    "request_id": "req_err_0023"
  }
}
```

---

## Authentication and Authorization

1. **REST Endpoints (`/api/v1/events*`, `/api/v1/alerts/*`)**:
   - `Viewer`: Có quyền đọc nhật ký sự kiện (`GET /api/v1/events`) và xem bằng chứng vi phạm (`GET /api/v1/events/{id}/evidence`).
   - `Admin`: Có thêm quyền gọi API test gửi Telegram (`POST /api/v1/alerts/telegram/test`) và thay đổi cấu hình Telegram.
2. **WebSocket Gateway (`/ws/v1/events`)**:
   - Yêu cầu xác thực connection thông qua token/session header hoặc query param chuẩn của WebSocket gateway.

---

## Pagination and Versioning

1. **Phân trang (Pagination)**:
   - Endpoint `GET /api/v1/events` áp dụng phân trang dạng `page` và `limit` kèm thông tin `total_items`, `total_pages` trong `data`.
2. **Phiên bản Hợp đồng (Versioning)**:
   - Endpoint thuộc Namespace API `/api/v1/`. Các bổ sung dữ liệu trong CR-005 là các trường mở rộng (additive fields), bảo đảm tính tương thích ngược với v1.0 / CR-003.

---

## Compatibility

1. **Tương thích ngược với WebSocket Event Handlers hiện tại**:
   - Các consumer đang đọc WebSocket `/ws/v1/events` tiếp tục nhận được `ZONE_VIOLATION_EVENT` và `ALERT_LEVEL_3_NOTIFICATION` với cấu trúc JSON cũ, các trường chứng cứ mới (`violation_reason`, `object_type_name`, `video_clip_url`, `telegram_status`) được bổ sung theo nguyên tắc additive, không xóa hay đổi tên các trường đã có.
2. **Dùng chung Clip Chứng cứ với AI Assistant (CR-002 / REQ-008)**:
   - `video_clip_url` được dùng chung cho cả Telegram notification và tính năng hỏi đáp của AI Assistant khi người dùng yêu cầu xem video vi phạm.

---

## Open Questions

1. **Quản lý thời gian lưu trữ tệp Video Clip 10s MP4**:
   - Các file clip 10s bằng chứng sẽ được lưu trữ trong bao lâu trước khi hệ thống dọn dẹp (retention policy)? Mặc định đề xuất lưu 30 ngày cùng thời hạn nhật ký sự kiện.
2. **Gửi lại tin nhắn Telegram khi gặp sự cố tạm thời (Retry Mechanism)**:
   - Khi Telegram API trả về lỗi tạm thời (`TELEGRAM_API_TIMEOUT` hoặc `RATE_LIMITED`), hệ thống có tự động retry gửi lại sau X giây hay chỉ ghi nhận trạng thái `failed`? Mặc định đề xuất retry tối đa 3 lần với exponential backoff.

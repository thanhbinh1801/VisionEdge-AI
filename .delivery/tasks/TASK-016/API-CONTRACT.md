---
artifact: API-CONTRACT.md
version: "1.0"
task_id: TASK-016
owner: design-api
status: in-review
updated_at: "2026-08-20T18:44:06+07:00"
change_id: CR-003
depends_on:
  - .delivery/REQUIREMENTS.md
  - .delivery/ARCHITECTURE.md
  - .delivery/API-CONTRACT.md
  - .delivery/changes/CR-003/CHANGE-IMPACT.md
---

# API Contract: TASK-016 — Realtime Metadata Contract cho Area Monitoring

## Traceability

| Requirement | Contract coverage |
|---|---|
| `REQ-002` | Tách riêng `video stream lane`, `realtime metadata lane`, `event/alert lane`; định nghĩa payload snapshot theo frame cho Area Dashboard. |
| `REQ-004` | Xác định metadata lane không bị cooldown chặn; event lane vẫn là luồng đã dedup mới được dùng cho event feed và cảnh báo. |
| `REQ-005` | Chuẩn hóa `zone_version`, cache invalidation theo `camera_id`, và side effect bắt buộc sau CRUD zone thành công. |
| `REQ-009` | Khẳng định metadata lane không tự kích hoạt audio/notification; alert mức 3 chỉ phát sinh từ event lane đã qua severity + dedup. |
| `CR-003` | Bổ sung contract additive cho realtime metadata lane, giữ backward compatibility cho consumers đang dùng event lane hiện tại. |

## Resources and Operations

### 1. WebSocket gateway cho realtime runtime

| Operation | Method | Path | Purpose | Auth |
|---|---|---|---|---|
| Subscribe realtime gateway | `WS` | `/ws/v1/events` | Nhận `AREA_FRAME_METADATA` cùng các event hiện hữu trên cùng gateway. | Viewer/Admin |

Transport decision:
- Dùng event type mới `AREA_FRAME_METADATA` trên gateway WebSocket hiện có thay vì tạo channel riêng.
- Lý do: additive, ít phá vỡ client hiện tại, và phù hợp yêu cầu `api-gateway` trong `TASK-016`.

### 2. Zone control-plane với cache semantics bắt buộc

| Operation | Method | Path | Purpose | Auth |
|---|---|---|---|---|
| List zones by camera | `GET` | `/api/v1/zones?camera_id={camera_id}` | Trả zone config hiện hành kèm `zone_version`/`cache_status`. | Viewer/Admin |
| Create zone | `POST` | `/api/v1/zones` | Tạo zone mới và atomically refresh zone cache của camera. | Admin |
| Update zone | `PUT` | `/api/v1/zones/{zone_id}` | Sửa geometry/rules rồi refresh cache trước khi trả `200`. | Admin |
| Delete zone | `DELETE` | `/api/v1/zones/{zone_id}` | Xóa zone rồi invalidate/refresh cache trước khi trả `200`. | Admin |

Contract boundary:
- `TASK-016` không tạo REST endpoint mới cho metadata snapshot.
- UI Area Dashboard consume metadata qua WebSocket; REST chỉ phục vụ control-plane zone và bootstrap state.

### 3. Status codes

| Operation | Status | Meaning |
|---|---|---|
| `WS /ws/v1/events` | `101` | WebSocket upgrade thành công. |
| `GET /api/v1/zones` | `200` | Trả danh sách zone và cache metadata. |
| `POST /api/v1/zones` | `201` | Zone được tạo và cache đã refresh thành công. |
| `PUT /api/v1/zones/{zone_id}` | `200` | Zone được cập nhật và cache đã refresh thành công. |
| `DELETE /api/v1/zones/{zone_id}` | `200` | Zone được xóa và cache đã invalidate/refresh thành công. |
| Zone write ops | `400` | Payload không hợp lệ về shape hoặc business rule. |
| Zone write ops | `401` | Thiếu xác thực. |
| Zone write ops | `403` | Không có quyền `Admin`. |
| Zone write ops | `404` | Không tìm thấy `zone_id`. |
| Zone write ops | `409` | Ghi DB thành công nhưng runtime cache refresh thất bại; request bị coi là thất bại logic và không được xác nhận completed cho client. |
| Zone write ops | `422` | Polygon/field validation thất bại. |
| Any op | `500` | Lỗi không phân loại được. |

## Request Contracts

### Response envelope chuẩn cho REST control-plane

```ts
export type ApiErrorCode =
  | "BAD_REQUEST"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "INVALID_ZONE_POLYGON"
  | "ZONE_CACHE_REFRESH_FAILED"
  | "CONFLICTING_ZONE_RULES"
  | "INTERNAL_SERVER_ERROR";

export interface ApiErrorDetail {
  field: string;
  issue: string;
}

export interface ApiError {
  code: ApiErrorCode;
  message: string;
  details?: ApiErrorDetail[];
}

export interface ApiMeta {
  timestamp: string;
  request_id: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: ApiMeta;
}
```

### Shared schema definitions

```ts
import { z } from "zod";

export const CameraIdSchema = z.enum(["BAI-KIEM"]);

export const ObjectClassSchema = z.enum([
  "container",
  "truck",
  "forklift",
  "crane",
  "car",
  "motorbike",
  "bicycle",
  "person",
]);

export const StreamStatusSchema = z.enum(["online", "degraded", "offline"]);

export const RuleResultSchema = z.enum(["allowed", "prohibited", "observed"]);

export const PointSchema = z.object({
  x: z.number().min(0).max(100),
  y: z.number().min(0).max(100),
});

export const BBoxSchema = z.tuple([
  z.number().min(0).max(1),
  z.number().min(0).max(1),
  z.number().min(0).max(1),
  z.number().min(0).max(1),
]);
```

### WebSocket event envelope

```ts
export const WsEventTypeSchema = z.enum([
  "LPR_DETECTION_EVENT",
  "ZONE_VIOLATION_EVENT",
  "AREA_FRAME_METADATA",
  "ALERT_LEVEL_3_NOTIFICATION",
]);

export const WsEnvelopeSchema = z.object({
  event_type: WsEventTypeSchema,
  timestamp: z.string().datetime({ offset: true }),
  payload: z.unknown(),
});

export type WsEnvelope = z.infer<typeof WsEnvelopeSchema>;
```

### `AREA_FRAME_METADATA` request semantics

- Client chỉ cần subscribe WebSocket; không có message request body bắt buộc.
- Server có thể bỏ qua hoặc đóng kết nối với các client message không được hỗ trợ.
- Không định nghĩa subprotocol riêng trong `TASK-016`.

### REST zone request bodies

```ts
export const ZoneRuleSetSchema = z.object({
  allowed_classes: z.array(ObjectClassSchema).max(8).default([]),
  forbidden_classes: z.array(ObjectClassSchema).max(8).default([]),
}).superRefine((value, ctx) => {
  const overlap = value.allowed_classes.filter((item) =>
    value.forbidden_classes.includes(item),
  );
  if (overlap.length > 0) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["forbidden_classes"],
      message: `Classes cannot be both allowed and forbidden: ${overlap.join(", ")}`,
    });
  }
});

export const ZoneWriteSchema = z.object({
  camera_id: CameraIdSchema,
  name: z.string().trim().min(1).max(80),
  vertices: z.array(PointSchema.or(z.tuple([z.number().min(0).max(100), z.number().min(0).max(100)]))).min(3).max(32),
  allowed_classes: z.array(ObjectClassSchema).default([]),
  forbidden_classes: z.array(ObjectClassSchema).default([]),
  is_active: z.boolean().default(true),
  color: z.string().regex(/^#(?:[0-9a-fA-F]{6})$/),
});

export const ZonePatchSchema = ZoneWriteSchema.partial().refine(
  (value) => Object.keys(value).length > 0,
  { message: "At least one field must be provided" },
);
```

### Query parameters

```ts
export const ZoneListQuerySchema = z.object({
  camera_id: CameraIdSchema,
});
```

## Response Contracts

### `AREA_FRAME_METADATA` payload

```ts
export const ZoneHitSchema = z.object({
  zone_id: z.string().min(1),
  zone_name: z.string().min(1),
  rule_result: RuleResultSchema,
});

export const AreaDetectedObjectSchema = z.object({
  track_id: z.string().min(1),
  object_class: ObjectClassSchema,
  confidence: z.number().min(0).max(1),
  bbox: BBoxSchema,
  center_point: z.object({
    x: z.number().min(0).max(1),
    y: z.number().min(0).max(1),
  }),
  zone_hits: z.array(ZoneHitSchema),
});

export const AreaKpiDeltaSchema = z.object({
  area_active_objects: z.number().int().min(0),
  area_zone_violations: z.number().int().min(0),
  area_active_machinery: z.number().int().min(0),
  area_total_zones: z.number().int().min(0),
});

export const AreaFrameMetadataSchema = z.object({
  camera_id: CameraIdSchema,
  frame_id: z.string().min(1),
  captured_at: z.string().datetime({ offset: true }),
  zone_version: z.number().int().min(1),
  stream_status: StreamStatusSchema,
  pipeline_latency_ms: z.number().min(0),
  objects: z.array(AreaDetectedObjectSchema),
  kpi_delta: AreaKpiDeltaSchema,
});

export const AreaFrameMetadataEventSchema = z.object({
  event_type: z.literal("AREA_FRAME_METADATA"),
  timestamp: z.string().datetime({ offset: true }),
  payload: AreaFrameMetadataSchema,
});

export type AreaFrameMetadata = z.infer<typeof AreaFrameMetadataSchema>;
```

Behavior rules:
- `timestamp` là thời điểm gateway broadcast.
- `payload.captured_at` là thời điểm frame được pipeline xử lý.
- `zone_version` phải phản ánh đúng snapshot cache mà frame loop đã dùng.
- `objects` có thể rỗng khi không phát hiện đối tượng nhưng stream vẫn online.
- `stream_status="offline"` bắt buộc đi kèm `objects=[]`; `kpi_delta` vẫn được phép xuất hiện với giá trị `0`.

### Zone control-plane responses

```ts
export const ZoneCacheStatusSchema = z.object({
  camera_id: CameraIdSchema,
  zone_version: z.number().int().min(1),
  cache_status: z.enum(["hot", "refreshing"]),
  refreshed_at: z.string().datetime({ offset: true }),
});

export const ZoneSchema = z.object({
  id: z.string().min(1),
  camera_id: CameraIdSchema,
  name: z.string().min(1).max(80),
  vertices: z.array(PointSchema).min(3).max(32),
  allowed_classes: z.array(ObjectClassSchema),
  forbidden_classes: z.array(ObjectClassSchema),
  is_active: z.boolean(),
  color: z.string().regex(/^#(?:[0-9a-fA-F]{6})$/),
  version: z.number().int().min(1),
});

export const ZoneListResponseSchema = z.object({
  success: z.literal(true),
  data: z.object({
    items: z.array(ZoneSchema),
    cache: ZoneCacheStatusSchema,
  }),
  error: z.null(),
  meta: z.object({
    timestamp: z.string().datetime({ offset: true }),
    request_id: z.string().min(1),
  }),
});

export const ZoneWriteResponseSchema = z.object({
  success: z.literal(true),
  data: z.object({
    zone: ZoneSchema,
    cache: ZoneCacheStatusSchema,
  }),
  error: z.null(),
  meta: z.object({
    timestamp: z.string().datetime({ offset: true }),
    request_id: z.string().min(1),
  }),
});
```

### Compatibility event rules

- `ZONE_VIOLATION_EVENT` và `ALERT_LEVEL_3_NOTIFICATION` giữ nguyên ý nghĩa hiện tại.
- `AREA_FRAME_METADATA` là additive; client cũ có thể bỏ qua event type lạ mà không phá kết nối.
- Event feed UI vẫn lấy từ event lane; không suy luận event history bằng cách lưu lại metadata snapshots ở client.

## Validation

- `camera_id` cho metadata lane hiện tại chỉ hợp lệ là `BAI-KIEM`.
- `vertices` tối thiểu 3 điểm, tối đa 32 điểm; mọi điểm nằm trong không gian phần trăm `0..100`.
- Một `object_class` không được xuất hiện đồng thời ở `allowed_classes` và `forbidden_classes`.
- `zone_version` tăng đơn điệu theo từng camera sau mỗi CRUD zone thành công.
- `bbox` và `center_point` của metadata lane dùng tọa độ chuẩn hóa `0..1` để tách khỏi kích thước video render thực tế.
- `pipeline_latency_ms` phải là số không âm; không định nghĩa upper bound protocol-level trong task này.
- `frame_id` phải unique trong phạm vi từng camera stream session.
- Nếu DB update thành công nhưng cache refresh không thành công, response phải là lỗi `409 ZONE_CACHE_REFRESH_FAILED`; server không được trả `200/201`.

## Error Model

| Code | HTTP | When |
|---|---|---|
| `BAD_REQUEST` | `400` | Payload sai shape tổng quát hoặc query không hợp lệ. |
| `UNAUTHORIZED` | `401` | Không có thông tin xác thực hợp lệ. |
| `FORBIDDEN` | `403` | Tài khoản không có vai trò `Admin` cho CRUD zone. |
| `NOT_FOUND` | `404` | `zone_id` không tồn tại. |
| `INVALID_ZONE_POLYGON` | `422` | Polygon < 3 điểm, tọa độ ngoài range, hoặc hình học không hợp lệ. |
| `CONFLICTING_ZONE_RULES` | `422` | Có overlap giữa allow/forbid lists. |
| `ZONE_CACHE_REFRESH_FAILED` | `409` | Control-plane chưa đồng bộ được runtime cache sau CRUD thành công ở DB. |
| `INTERNAL_SERVER_ERROR` | `500` | Lỗi không phân loại được. |

Example:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ZONE_CACHE_REFRESH_FAILED",
    "message": "Zone was persisted but runtime cache could not be refreshed for camera BAI-KIEM.",
    "details": [
      {
        "field": "camera_id",
        "issue": "Cache remained stale after write operation"
      }
    ]
  },
  "meta": {
    "timestamp": "2026-08-20T18:39:50+07:00",
    "request_id": "req_01k2x4wsp9m"
  }
}
```

## Authentication and Authorization

- `Viewer` được phép subscribe `/ws/v1/events` và `GET /api/v1/zones`.
- `Admin` là role tối thiểu cho `POST/PUT/DELETE /api/v1/zones*`.
- `TASK-016` chỉ chuẩn hóa policy-level contract; không ràng buộc cơ chế auth cụ thể (JWT/session/API key) vì upstream foundation chưa chốt.
- Khi auth foundation được hoàn tất ở task khác, endpoint/path và payload trong tài liệu này không đổi; chỉ header/cookie contract được gắn thêm.

## Pagination and Versioning

- Pagination: không áp dụng cho `AREA_FRAME_METADATA` vì đây là stream push theo thời gian thực, không phải collection query.
- Pagination: không áp dụng cho `GET /api/v1/zones?camera_id=BAI-KIEM` trong phạm vi hiện tại vì số zone theo camera được giả định nhỏ và cần bootstrap đầy đủ để render editor/dashboard nhất quán.
- Versioning transport:
  - REST tiếp tục dùng prefix `/api/v1`.
  - WebSocket gateway dùng `/ws/v1/events`.
  - Event type mới `AREA_FRAME_METADATA` là additive trong `v1`.
- Versioning runtime:
  - `zone_version` là version nghiệp vụ theo từng camera để phát hiện stale cache/stale overlay.
  - Nếu shape payload metadata thay đổi theo hướng breaking trong tương lai, phải tạo `v2` gateway hoặc `AREA_FRAME_METADATA_V2`; không tái định nghĩa âm thầm event hiện tại.

## Compatibility

- Backend hiện tại expose `/ws/alerts` và frontend `WebSocketClient` mặc định connect vào đường dẫn đó; contract mới yêu cầu migration sang `/ws/v1/events`.
- Frontend `AreaSecurityDashboard.tsx` hiện vẫn polling `fetchLiveDetections` và `fetchLatestEvents`; contract này chốt đích đến là:
  - overlay/KPI area dùng `AREA_FRAME_METADATA`
  - event feed và audio dùng event lane đã dedup
  - annotated MJPEG chỉ là video renderer, không phải nguồn truth cho metadata
- Để giữ backward compatibility ngắn hạn:
  - server có thể duy trì `/ws/alerts` như alias tạm thời hoặc bridge legacy events,
  - nhưng `TASK-017`/`TASK-018` phải coi `/ws/v1/events` + `AREA_FRAME_METADATA` là contract chính thức.
- `docs/contracts/api/api-schema.json` và `docs/contracts/api/websocket-events.json` hiện đã có các field nền tảng gần đúng; thay đổi tiếp theo nên là additive refinement thay vì rename field đã công bố, trừ khi tạo version mới.

## Open Questions

- Task packet hiện ghi `Module: api-gateway`, nhưng chưa có packet `ready` theo contract framework để xác nhận owner và write scope chính thức.
- Upstream foundation chưa khóa cơ chế auth cụ thể; chỉ có thể chốt role semantics ở mức `Viewer/Admin`.
- Chưa chốt liệu server có giữ `/ws/alerts` làm alias lâu dài hay chỉ là bridge migration ngắn hạn.
- Chưa có business rule xác định sampling cadence tối thiểu/tối đa cho `AREA_FRAME_METADATA`; task này chỉ chuẩn hóa shape và semantics, không chốt SLA frame rate.

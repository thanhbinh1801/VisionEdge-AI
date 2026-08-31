---
artifact: API-CONTRACT.md
version: "1.0"
task_id: TASK-030
owner: design-api
status: in-review
updated_at: "2026-08-27T20:13:59+07:00"
change_id: CR-007
depends_on:
  - .delivery/REQUIREMENTS.md
  - .delivery/ARCHITECTURE.md
  - .delivery/API-CONTRACT.md
  - .delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md
  - .delivery/changes/CR-007/CHANGE-IMPACT.md
  - .delivery/tasks/TASK-016/API-CONTRACT.md
  - docs/contracts/api/api-schema.json
  - docs/contracts/api/websocket-events.json
---

# API Contract: TASK-030 — CR-007 Area Detection, BBox Debug và Zone Evaluation

## Traceability

| Yêu cầu | Bao phủ trong contract |
|---|---|
| `REQ-002` | Chốt contract Area Monitoring `BAI-KIEM` dùng YOLOv11s finetune, tách ngưỡng hiển thị/debug khỏi ngưỡng event/alert, bổ sung `show_static_containers`, class mapping, bbox debug fields và class-aware zone evaluation. |
| `REQ-004` | Giữ metadata lane không bị cooldown chặn; `track_id` là optional/future-compatible và không được giả định luôn có trong CR-007. |
| `REQ-009` | Khẳng định bbox/metadata/debug lane không tự kích hoạt audio, popup hoặc Telegram; chỉ event lane đã qua threshold, stability, severity và cooldown mới phát alert Mức 3. |
| `CR-007` | Chuẩn hóa additive API/WS contract cho threshold layering, container debug, metadata fields, zone evaluation method/ratio và ranh giới không đổi LPR/GATE-01. |

Ghi chú phạm vi: `REQ-005` bị ảnh hưởng gián tiếp vì zone polygon là input hình học cho evaluator, nhưng TASK-030 chỉ trace các linked requirements trong packet là `REQ-002`, `REQ-004`, `REQ-009`, `CR-007`.

## Resources and Operations

### 1. MJPEG video stream lane

| Operation | Method | Path | Mục đích | Auth | Status |
|---|---|---|---|---|---|
| Stream video khu vực | `GET` | `/api/v1/events/video-feed` | Trả MJPEG stream có bbox renderer phục vụ hiển thị/debug. | Viewer/Admin | `200`, `400`, `401`, `403`, `503` |

Query parameters:

| Tên | Kiểu | Required | Default | Ràng buộc | Ý nghĩa |
|---|---|---:|---|---|---|
| `camera_id` | string | no | `BAI-KIEM` | `BAI-KIEM` hoặc `GATE-01`; CR-007 chỉ áp dụng debug semantics cho `BAI-KIEM`. | Chọn camera stream. |
| `conf_threshold` | number | no | `settings.DETECTION_CONFIDENCE_THRESHOLD` nếu backend có cấu hình, fallback `0.35` | `0 <= value <= 1` | Ngưỡng hiển thị/debug bbox trên MJPEG; không phải ngưỡng sinh event/alert. |
| `draw_zones` | boolean | no | `true` | boolean string `true/false` | Vẽ polygon zone lên MJPEG. |
| `show_static_containers` | boolean | no | `false` | boolean string `true/false` | Khi `true`, renderer hiển thị bbox `container` và `shipping_container` để debug model; khi `false`, renderer được phép ẩn nhóm này để giảm nhiễu UI. |

Behavior:
- Response thành công là `multipart/x-mixed-replace; boundary=frame`, không dùng JSON envelope.
- Header mỗi frame giữ `X-Frame-Id` và `X-Frame-Timestamp` khi backend có snapshot.
- `conf_threshold` chỉ quyết định bbox nào được render/quan sát trên stream; event persistence, audio, popup và Telegram không được dẫn xuất trực tiếp từ route này.
- Với `camera_id=GATE-01`, route không được thay đổi nghiệp vụ LPR; các tham số CR-007 chỉ là no-op hoặc debug hiển thị nếu backend dùng chung renderer.

### 2. Live detections legacy/debug endpoint

| Operation | Method | Path | Mục đích | Auth | Status |
|---|---|---|---|---|---|
| Lấy detection snapshot legacy | `GET` | `/api/v1/events/live-detections` | Trả mảng detection tương thích frontend cũ; CR-007 yêu cầu field mới chỉ additive nếu route được mở rộng. | Viewer/Admin | `200`, `400`, `401`, `403`, `503` |

Query parameters:
- `camera_id`: mặc định `BAI-KIEM`.
- `conf_threshold`: mặc định `0.35`, `0..1`, chỉ là ngưỡng debug/metadata snapshot của route này.
- `video_time`: optional seconds, chỉ phục vụ tương quan video demo/clip.

Compatibility:
- Body hiện tại là direct array, không phải envelope. TASK-030 không đổi shape này để tránh phá consumer cũ.
- Nếu bổ sung CR-007 fields vào từng item, các field phải optional/additive: `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`, `track_id`.

### 3. WebSocket realtime metadata lane

| Operation | Method | Path | Mục đích | Auth | Status |
|---|---|---|---|---|---|
| Subscribe realtime events | `WS` | `/ws/v1/events` | Nhận `AREA_FRAME_METADATA` cùng các event realtime khác. | Viewer/Admin | `101`, `401`, `403` |

Event type chịu ảnh hưởng trực tiếp:
- `AREA_FRAME_METADATA`: snapshot metadata theo frame/sampling interval cho Area Dashboard.

Lane separation:
- `video stream lane`: render hình ảnh/bbox để quan sát.
- `realtime metadata lane`: publish object/zone/KPI/debug snapshot gần realtime.
- `event/alert lane`: chỉ phát sinh sau khi detection qua application threshold, class-aware zone evaluation, stability ngắn và cooldown/dedup.

### 4. Event/alert lane boundary

TASK-030 không thiết kế endpoint mới cho event persistence hoặc Telegram. Contract này chỉ ràng buộc input semantics cho các event hiện hữu:
- `ZONE_VIOLATION_EVENT` chỉ được sinh từ object đã qua application/per-class threshold và zone evaluation hợp lệ.
- `ALERT_LEVEL_3_NOTIFICATION` chỉ được phát từ event Mức 3 đã qua severity và cooldown.
- `AREA_FRAME_METADATA` hoặc bbox render trên MJPEG không tự tương đương với alert đã xác nhận.

## Request Contracts

### TypeScript/Zod definitions cho request/query

Các định nghĩa dưới đây có thể đặt tại `frontend/src/contracts/api/area-detection.schema.ts` hoặc shared contract tương đương khi aggregate contract được cập nhật.

```ts
import { z } from "zod";

export const CameraIdSchema = z.enum(["GATE-01", "BAI-KIEM"]);
export const AreaCameraIdSchema = z.literal("BAI-KIEM");

export const BooleanQuerySchema = z
  .union([z.boolean(), z.enum(["true", "false", "1", "0"])])
  .transform((value) => value === true || value === "true" || value === "1");

export const ConfidenceThresholdSchema = z.coerce
  .number()
  .min(0)
  .max(1);

export const VideoFeedQuerySchema = z.object({
  camera_id: CameraIdSchema.default("BAI-KIEM"),
  conf_threshold: ConfidenceThresholdSchema.optional(),
  draw_zones: BooleanQuerySchema.default(true),
  show_static_containers: BooleanQuerySchema.default(false),
});

export const LiveDetectionsQuerySchema = z.object({
  camera_id: CameraIdSchema.default("BAI-KIEM"),
  conf_threshold: ConfidenceThresholdSchema.default(0.35),
  video_time: z.coerce.number().min(0).optional(),
});
```

### Threshold policy request semantics

```ts
export const ThresholdLayerSchema = z.enum([
  "inference",
  "display_debug",
  "application_event",
]);

export const CanonicalObjectClassSchema = z.enum([
  "container",
  "shipping_container",
  "truck",
  "container_truck",
  "forklift",
  "crane",
  "car",
  "motorbike",
  "bicycle",
  "person",
]);

export const AreaThresholdDefaultsSchema = z.object({
  inference_threshold: z.number().min(0).max(1).default(0.25),
  display_debug_threshold: z.number().min(0).max(1).default(0.35),
  application_event_threshold: z.number().min(0).max(1).default(0.50),
  per_class_event_thresholds: z.record(CanonicalObjectClassSchema, z.number().min(0).max(1)).partial(),
});
```

Rules:
- `inference_threshold` là ngưỡng thấp nhất để model không bỏ sót ứng viên đáng quan sát.
- `display_debug_threshold` là ngưỡng client/route dùng để hiển thị bbox.
- `application_event_threshold` và `per_class_event_thresholds` là ngưỡng nghiệp vụ trước khi sinh event/alert.
- `conf_threshold` trên `/video-feed` và `/live-detections` không được ghi đè application threshold của event lane.

## Response Contracts

### Response envelope chung

Các REST JSON endpoint tiếp tục dùng envelope aggregate hiện có:

```ts
export interface ApiErrorDetail {
  field: string;
  issue: string;
}

export interface ApiError {
  code:
    | "BAD_REQUEST"
    | "UNAUTHORIZED"
    | "FORBIDDEN"
    | "NOT_FOUND"
    | "VALIDATION_ERROR"
    | "AI_MODEL_UNAVAILABLE"
    | "ZONE_EVALUATION_UNAVAILABLE"
    | "STREAM_SOURCE_UNAVAILABLE"
    | "INTERNAL_SERVER_ERROR";
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

### WebSocket envelope

```ts
export const WsEventTypeSchema = z.enum([
  "LPR_DETECTION_EVENT",
  "ZONE_VIOLATION_EVENT",
  "AREA_FRAME_METADATA",
  "KPI_STATS_UPDATE",
  "ALERT_LEVEL_3_NOTIFICATION",
  "DATASET_SAMPLE_SYNC_EVENT",
]);

export const WsEnvelopeSchema = z.object({
  event_type: WsEventTypeSchema,
  timestamp: z.string().datetime({ offset: true }),
  payload: z.unknown(),
});
```

### Metadata object và CR-007 additive fields

```ts
export const ZoneEvalMethodSchema = z.enum([
  "bottom_center",
  "footprint_overlap",
  "bbox_overlap_ratio",
  "center_point_fallback",
  "none",
]);

export const RuleResultSchema = z.enum(["allowed", "prohibited", "observed"]);

export const NormalizedBBoxXyxySchema = z
  .tuple([
    z.number().min(0).max(1),
    z.number().min(0).max(1),
    z.number().min(0).max(1),
    z.number().min(0).max(1),
  ])
  .refine(([x1, y1, x2, y2]) => x2 >= x1 && y2 >= y1, {
    message: "bbox_xyxy_norm must satisfy x2 >= x1 and y2 >= y1",
  });

export const CenterPointSchema = z.object({
  x: z.number().min(0).max(1),
  y: z.number().min(0).max(1),
});

export const ZoneHitSchema = z.object({
  zone_id: z.string().min(1),
  zone_name: z.string().min(1),
  rule_result: RuleResultSchema,
  zone_eval_method: ZoneEvalMethodSchema.optional(),
  zone_overlap_ratio: z.number().min(0).max(1).nullable().optional(),
});

export const AreaMetadataObjectSchema = z.object({
  track_id: z.string().min(1).nullable().optional(),
  object_class: CanonicalObjectClassSchema,
  raw_class: z.string().min(1).optional(),
  canonical_class: CanonicalObjectClassSchema.optional(),
  display_name: z.string().min(1).optional(),
  confidence: z.number().min(0).max(1),
  bbox: NormalizedBBoxXyxySchema,
  bbox_xyxy_norm: NormalizedBBoxXyxySchema.optional(),
  center_point: CenterPointSchema,
  zone_eval_method: ZoneEvalMethodSchema.optional(),
  zone_overlap_ratio: z.number().min(0).max(1).nullable().optional(),
  detection_frame_id: z.string().min(1).optional(),
  zone_hits: z.array(ZoneHitSchema),
});

export const AreaFrameMetadataPayloadSchema = z.object({
  camera_id: AreaCameraIdSchema,
  frame_id: z.string().min(1),
  captured_at: z.string().datetime({ offset: true }),
  zone_version: z.number().int().min(1),
  stream_status: z.enum(["online", "degraded", "offline"]),
  pipeline_latency_ms: z.number().min(0),
  objects: z.array(AreaMetadataObjectSchema),
  kpi_delta: z.object({
    area_active_objects: z.number().int().min(0),
    area_zone_violations: z.number().int().min(0),
    area_active_machinery: z.number().int().min(0),
    area_total_zones: z.number().int().min(0),
  }),
});

export const AreaFrameMetadataEventSchema = z.object({
  event_type: z.literal("AREA_FRAME_METADATA"),
  timestamp: z.string().datetime({ offset: true }),
  payload: AreaFrameMetadataPayloadSchema,
});
```

Response behavior:
- `bbox` tiếp tục giữ normalized `[x_min, y_min, x_max, y_max]` để tương thích TASK-016.
- `bbox_xyxy_norm` là alias rõ nghĩa, optional trong giai đoạn chuyển tiếp; khi có thì phải bằng `bbox`.
- `object_class` giữ vai trò compatibility field và phải bằng `canonical_class` khi `canonical_class` có mặt.
- `raw_class` giữ tên lớp gốc từ YOLOv11s finetune để debug.
- `track_id` có thể vắng mặt hoặc `null`; consumer không được dùng nó làm required key.
- `detection_frame_id` tương quan metadata với inference frame, không nhất thiết bằng `frame_id` của decoded frame nếu pipeline decode/inference tách thread.

### Zone evaluation contract

```ts
export const ZoneEvaluationPolicySchema = z.object({
  object_class: CanonicalObjectClassSchema,
  method: ZoneEvalMethodSchema,
  minimum_overlap_ratio: z.number().min(0).max(1).nullable(),
  stability_frames: z.number().int().min(1).default(3),
  stability_window_ms: z.number().int().min(0).default(500),
});

export const DefaultZoneEvaluationPolicies: z.infer<typeof ZoneEvaluationPolicySchema>[] = [
  { object_class: "person", method: "bottom_center", minimum_overlap_ratio: null, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "motorbike", method: "bottom_center", minimum_overlap_ratio: null, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "bicycle", method: "bottom_center", minimum_overlap_ratio: null, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "forklift", method: "footprint_overlap", minimum_overlap_ratio: 0.15, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "truck", method: "footprint_overlap", minimum_overlap_ratio: 0.15, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "container_truck", method: "footprint_overlap", minimum_overlap_ratio: 0.15, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "car", method: "footprint_overlap", minimum_overlap_ratio: 0.15, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "crane", method: "footprint_overlap", minimum_overlap_ratio: 0.15, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "container", method: "bbox_overlap_ratio", minimum_overlap_ratio: 0.25, stability_frames: 3, stability_window_ms: 500 },
  { object_class: "shipping_container", method: "bbox_overlap_ratio", minimum_overlap_ratio: 0.25, stability_frames: 3, stability_window_ms: 500 },
];
```

### Legacy live-detections response item

```ts
export const LegacyLiveDetectionSchema = z.object({
  id: z.string().min(1),
  object_class: CanonicalObjectClassSchema,
  vietnamese_name: z.string().min(1),
  label: z.string().min(1),
  confidence: z.number().min(0).max(1),
  bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]),
  severity: z.number().int().min(1).max(3),
  zone_violation: z.boolean(),
  zone_name: z.string().optional(),
  raw_class: z.string().optional(),
  canonical_class: CanonicalObjectClassSchema.optional(),
  bbox_xyxy_norm: NormalizedBBoxXyxySchema.optional(),
  zone_eval_method: ZoneEvalMethodSchema.optional(),
  zone_overlap_ratio: z.number().min(0).max(1).nullable().optional(),
  detection_frame_id: z.string().optional(),
  track_id: z.string().nullable().optional(),
});

export const LegacyLiveDetectionResponseSchema = z.array(LegacyLiveDetectionSchema);
```

## Validation

- `camera_id=BAI-KIEM` là camera duy nhất bắt buộc áp dụng CR-007 Area Monitoring contract.
- `conf_threshold` phải nằm trong `[0,1]`; giá trị ngoài range trả `400 BAD_REQUEST` hoặc `422 VALIDATION_ERROR` tùy foundation implementation.
- `show_static_containers` chỉ ảnh hưởng renderer bbox, không được loại bỏ object khỏi inference result, metadata lane, event lane hoặc zone evaluation.
- `raw_class` là chuỗi gốc từ model; `canonical_class` phải thuộc enum chuẩn. Nếu raw class không map được thì backend được bỏ detection khỏi canonical payload thay vì ép thành `person`.
- `shipping_container` và `container_truck` là canonical classes hợp lệ trong CR-007. Nếu implementation tạm map về `container`/`truck`, phải vẫn giữ `raw_class` để debug và ghi deviation trong `TASK-RESULT.md` của task implementation.
- `bbox`, `bbox_xyxy_norm`, `center_point` đều dùng normalized coordinate `0..1` trong `AREA_FRAME_METADATA`.
- `zone_overlap_ratio` là `null` hoặc absent với `bottom_center`/`none`; là số `0..1` với overlap-based methods.
- `center_point_fallback` chỉ được dùng khi backend không tính được method chính; nếu dùng cho production event phải ghi log hoặc debug field để verification phát hiện.
- `stream_status="offline"` phải đi kèm `objects=[]`; UI vẫn được giữ zone overlay và tự retry.
- Event Mức 3 cho zone violation phải qua tối thiểu stability rule ngắn trước khi vào cooldown/dedup: mặc định 3 frame hoặc 500ms, trừ khi implementation có cấu hình tương đương được ghi rõ.

## Error Model

| Code | HTTP/WS | Khi nào |
|---|---|---|
| `BAD_REQUEST` | `400` | Query param sai kiểu, ví dụ `conf_threshold=abc` hoặc boolean không parse được. |
| `VALIDATION_ERROR` | `422` | Query hợp kiểu nhưng vi phạm rule contract. |
| `UNAUTHORIZED` | `401` | Thiếu xác thực hợp lệ. |
| `FORBIDDEN` | `403` | Tài khoản không đủ quyền xem camera/metadata. |
| `AI_MODEL_UNAVAILABLE` | `503` | YOLOv11s finetune không nạp được và fallback không đáp ứng contract Area Monitoring. |
| `STREAM_SOURCE_UNAVAILABLE` | `503` | Không mở/giải mã được video source camera. |
| `ZONE_EVALUATION_UNAVAILABLE` | `503` | Zone cache/evaluator lỗi khiến backend không thể xác định rule result an toàn. |
| `INTERNAL_SERVER_ERROR` | `500` | Lỗi không phân loại được. |

Error envelope ví dụ cho REST JSON endpoint:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AI_MODEL_UNAVAILABLE",
    "message": "Không thể nạp YOLOv11s finetune cho camera BAI-KIEM.",
    "details": [
      {
        "field": "camera_id",
        "issue": "Area Monitoring không được chạy bằng model không đáp ứng CR-007 nếu không ghi rõ fallback."
      }
    ]
  },
  "meta": {
    "timestamp": "2026-08-27T20:13:59+07:00",
    "request_id": "req_area_030"
  }
}
```

Với MJPEG stream, lỗi trước khi stream bắt đầu dùng HTTP status và `detail` FastAPI hiện hữu; không bọc envelope vì content type thành công là stream byte.

## Authentication and Authorization

- `Viewer` và `Admin` được phép xem `/api/v1/events/video-feed`, `/api/v1/events/live-detections` và subscribe `/ws/v1/events`.
- `Admin` không có quyền đặc biệt nào để làm `conf_threshold` thay đổi event threshold; event threshold là cấu hình backend/contract nghiệp vụ, không phải input tùy ý từ UI vận hành.
- Contract này không chốt cơ chế auth cụ thể (JWT, session hay API key) vì foundation chỉ ràng buộc role semantics. Khi auth foundation được cập nhật, path/query/payload CR-007 không đổi.
- Không endpoint nào trong TASK-030 được nhận absolute filesystem path từ client.

## Pagination and Versioning

- Pagination không áp dụng cho `/api/v1/events/video-feed` vì đây là MJPEG stream liên tục.
- Pagination không áp dụng cho `/api/v1/events/live-detections` vì endpoint trả snapshot hiện tại, không phải collection history.
- Pagination không áp dụng cho `AREA_FRAME_METADATA` vì WebSocket push theo thời gian thực.
- REST giữ prefix `/api/v1`; WebSocket giữ `/ws/v1/events`.
- CR-007 fields là additive trong version `v1`. Không được rename hoặc đổi nghĩa các field TASK-016 đã công bố như `bbox`, `center_point`, `zone_hits`, `kpi_delta`.
- Nếu tương lai bắt buộc breaking change về bbox coordinate hoặc event derivation, phải tạo `/api/v2` hoặc event type mới như `AREA_FRAME_METADATA_V2`.

## Compatibility

- Tương thích TASK-016: `AREA_FRAME_METADATA` giữ các required fields cũ; CR-007 chỉ thêm optional fields.
- Tương thích frontend hiện tại: `AreaSecurityDashboard.tsx` đang lấy MJPEG qua `getVideoFeedUrl(activeCam, { drawZones: false })`; helper cần mở rộng optional `confThreshold` và `showStaticContainers`, nhưng call cũ vẫn phải chạy với default.
- Tương thích backend hiện tại: `/api/v1/events/video-feed` đang default `conf_threshold=0.50` và ẩn `container` hard-code; implementation TASK-031 phải đổi default theo contract và thêm `show_static_containers`.
- Tương thích metadata hiện tại: `area_metadata.py` chưa publish `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`; TASK-031 phải bổ sung additive fields mà không bỏ `display_name`.
- Tương thích event/alert: thay zone evaluation có thể đổi số lượng event hợp lệ; đây là thay đổi nghiệp vụ được CR-007 duyệt, nhưng alert vẫn phải qua cooldown/dedup hiện hữu.
- Tương thích GATE-01: không thay đổi LPR route, OCR, vehicle tag hoặc gate event semantics; chỉ chạy regression vì có thể dùng chung helper renderer/detection.

## Open Questions

- Per-class event threshold cuối cùng nên lấy từ cấu hình nào (`settings`, file JSON, DB hay constants) chưa được foundation chốt; contract chỉ yêu cầu có tầng application/per-class tách biệt.
- Giá trị `minimum_overlap_ratio` mặc định trong tài liệu này là baseline thiết kế để implementation/test bắt đầu; Product Owner có thể tinh chỉnh sau verification footage thật.
- `container_truck` và `shipping_container` đang là canonical classes trong requirements/API aggregate; nếu model finetune chỉ trả raw label khác, implementation phải map rõ và giữ `raw_class`.
- Tracking đầy đủ và dedup theo `track_id` là phạm vi tương lai; CR-007 chỉ yêu cầu optional readiness field.

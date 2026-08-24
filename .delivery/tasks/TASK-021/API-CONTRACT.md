---
artifact: API-CONTRACT.md
version: "1.0"
owner: design-api
status: approved
updated_at: "2026-08-24T19:40:41+07:00"
task_id: TASK-021
depends_on: [TASK-PACKET.md, REQUIREMENTS.md, ARCHITECTURE.md, API-CONTRACT.md, TASK-020]
---

# TASK-021 API Contract - Luồng Dataset Object Labeling

## Traceability

- REQ-005: `POST /api/v1/dataset/sync-zones`, side effect khi create/rename/restore custom label, và metadata `cache` trong response đảm bảo active custom labels được đưa vào zone rules với mặc định `forbidden`, đồng thời backend có đủ tín hiệu để refresh zone cache sau khi ghi DB.
- REQ-007: Contract này bao phủ upload/list/detail dataset source, lấy frame từ source, label CRUD + soft delete/restore, list/batch create/update/delete bbox samples, atomic batch validation, persisted reload, khóa nhãn hệ thống, uniqueness không phân biệt hoa/thường, và `sample_count`.
- CR-004: Toàn bộ endpoint dưới đây chuyển `Cài đặt > Nhãn đối tượng` từ mock/local state sang media, labels, samples và zone sync persisted ở backend. API không hứa AI realtime sẽ nhận diện custom class mới.

## Resources and Operations

Mọi JSON endpoint dùng base path `/api/v1/dataset` và response envelope chuẩn:

```ts
type ApiResponse<T> =
  | { success: true; data: T; error: null; meta: MetaPayload }
  | { success: false; data: null; error: ErrorPayload; meta: MetaPayload };
```

Operations:

| Method | Path | Status | Data payload |
|---|---|---:|---|
| `GET` | `/api/v1/dataset/labels?include_deleted=false` | 200 | `{ items: ObjectLabel[] }` |
| `POST` | `/api/v1/dataset/labels` | 201 | `{ label: ObjectLabel, sync: ZoneSyncResult }` |
| `PUT` | `/api/v1/dataset/labels/{label_id}` | 200 | `{ label: ObjectLabel, sync: ZoneSyncResult }` |
| `DELETE` | `/api/v1/dataset/labels/{label_id}` | 200 | `{ label: ObjectLabel }` |
| `POST` | `/api/v1/dataset/labels/{label_id}/restore` | 200 | `{ label: ObjectLabel, sync: ZoneSyncResult }` |
| `GET` | `/api/v1/dataset/sources?page=1&limit=50&kind=video` | 200 | `{ items: DatasetSource[], page, limit, total_items, total_pages }` |
| `POST` | `/api/v1/dataset/sources` | 201 | `{ source: DatasetSource }` |
| `GET` | `/api/v1/dataset/sources/{source_id}` | 200 | `{ source: DatasetSource }` |
| `GET` | `/api/v1/dataset/sources/{source_id}/frame?frame_index=10` | 200 | binary `image/jpeg` with frame headers |
| `GET` | `/api/v1/dataset/samples?source_id=...&frame_index=10&label_id=...` | 200 | `{ items: BBoxSample[] }` |
| `POST` | `/api/v1/dataset/samples:batch` | 201 | `{ saved_count: number, samples: BBoxSample[], labels: ObjectLabel[] }` |
| `PUT` | `/api/v1/dataset/samples/{sample_id}` | 200 | `{ sample: BBoxSample, labels: ObjectLabel[] }` |
| `DELETE` | `/api/v1/dataset/samples/{sample_id}` | 200 | `{ deleted_id: string, labels: ObjectLabel[] }` |
| `POST` | `/api/v1/dataset/sync-zones` | 200 | `{ sync: ZoneSyncResult }` |

`POST /api/v1/dataset/sources` phải nhận `multipart/form-data` gồm `file`, optional `name`, optional `idempotency_key`. Backend lưu file vào managed media storage và tạo một dataset source. JSON legacy `POST /dataset/sources` với `url` tự do không phải đường CR-004.

`GET /api/v1/dataset/sources/{source_id}/frame` trả binary JPEG, không bọc envelope khi thành công. Response bắt buộc có headers `X-Dataset-Source-Id`, `X-Video-Fps`, `X-Video-Frame-Count`, `X-Frame-Index`, `X-Frame-Timestamp`. Với image source, nếu không truyền selector thì trả frame 0.

## Request Contracts

### Query and path parameters

- `label_id`, `source_id`, `sample_id`: string không rỗng, tối đa 96 ký tự.
- `include_deleted`: boolean, mặc định `false`.
- `kind`: optional `img | video`.
- `page`: integer >= 1, mặc định `1`.
- `limit`: integer từ 1 đến 100, mặc định `50`.
- Filter `source_id` và `label_id` của samples là optional; `frame_index` chỉ hợp lệ khi có `source_id`.
- Frame retrieval nhận đúng một trong `frame_index` hoặc `timestamp`; nếu bỏ cả hai thì hiểu là image preview/frame 0.

### JSON request examples

```json
POST /api/v1/dataset/labels
{
  "label_name": "Áo phản quang",
  "category": "person"
}
```

```json
PUT /api/v1/dataset/labels/lbl_custom_01
{
  "label_name": "Xe kéo hàng",
  "category": "vehicle_shape"
}
```

```json
POST /api/v1/dataset/samples:batch
{
  "samples": [
    {
      "label_id": "lbl_system_forklift",
      "source_id": "src_01",
      "frame_index": 45,
      "frame_timestamp_seconds": 1.5,
      "bbox": { "x": 20.5, "y": 30, "w": 40, "h": 50 }
    }
  ]
}
```

```json
PUT /api/v1/dataset/samples/bbox_01
{
  "label_id": "lbl_custom_01",
  "frame_index": 45,
  "bbox": { "x": 21, "y": 31, "w": 38, "h": 49 }
}
```

### Multipart source upload

```text
POST /api/v1/dataset/sources
Content-Type: multipart/form-data

file=<binary image/video>
name=yard-ca-chieu.mp4
idempotency_key=optional-client-token
```

Media types được nhận: `image/jpeg`, `image/png`, `video/mp4`, `video/quicktime`. Giới hạn CR-004: 250 MB. Backend có thể từ chối codec không hỗ trợ bằng `UNSUPPORTED_MEDIA_TYPE`.

## Response Contracts

Response JSON chuẩn:

```json
{
  "success": true,
  "data": {
    "items": []
  },
  "error": null,
  "meta": {
    "timestamp": "2026-08-24T19:40:41+07:00",
    "request_id": "req_abc123"
  }
}
```

`ObjectLabel`:

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

`DatasetSource`:

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

`BBoxSample`:

```json
{
  "id": "bbox_01",
  "label_id": "lbl_system_forklift",
  "source_id": "src_01",
  "frame_index": 45,
  "frame_timestamp_seconds": 1.5,
  "bbox": { "x": 20.5, "y": 30.0, "w": 40.0, "h": 50.0 },
  "coordinate_space": "percent_0_100",
  "label": { "id": "lbl_system_forklift", "label_key": "forklift", "label_name": "Xe nâng" },
  "created_at": "2026-08-24T19:40:41+07:00",
  "updated_at": "2026-08-24T19:40:41+07:00"
}
```

`ZoneSyncResult`:

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

### Machine-Verifiable TypeScript/Zod Contract

Đường dẫn dự kiến khi triển khai: `frontend/src/contracts/api/dataset.schema.ts` hoặc shared package tương đương.

```ts
import { z } from 'zod';

export const DateTimeString = z.string().datetime({ offset: true });

export const ErrorCode = z.enum([
  'BAD_REQUEST',
  'UNAUTHORIZED',
  'FORBIDDEN',
  'NOT_FOUND',
  'VALIDATION_ERROR',
  'DUPLICATE_LABEL_NAME',
  'SYSTEM_LABEL_LOCKED',
  'LABEL_IN_USE_BY_ZONE',
  'LABEL_INACTIVE',
  'SOURCE_NOT_READY',
  'UNSUPPORTED_MEDIA_TYPE',
  'UPLOAD_TOO_LARGE',
  'FRAME_NOT_AVAILABLE',
  'ZONE_CACHE_REFRESH_FAILED',
  'INTERNAL_SERVER_ERROR',
]);

export const ErrorPayload = z.object({
  code: ErrorCode,
  message: z.string().min(1),
  details: z.array(z.object({
    field: z.string(),
    issue: z.string(),
  })).default([]),
});

export const MetaPayload = z.object({
  timestamp: DateTimeString,
  request_id: z.string().min(1),
  page: z.number().int().positive().optional(),
  limit: z.number().int().positive().optional(),
  total_items: z.number().int().nonnegative().optional(),
  total_pages: z.number().int().nonnegative().optional(),
});

export const makeApiResponse = <T extends z.ZodTypeAny>(data: T) => z.discriminatedUnion('success', [
  z.object({ success: z.literal(true), data, error: z.null(), meta: MetaPayload }),
  z.object({ success: z.literal(false), data: z.null(), error: ErrorPayload, meta: MetaPayload }),
]);

export const ObjectLabelCategory = z.enum(['person', 'vehicle_shape', 'custom']);
export const ObjectLabelType = z.enum(['system', 'custom']);
export const DatasetSourceKind = z.enum(['img', 'video']);
export const ImportStatus = z.enum(['processing', 'ready', 'failed']);
export const CoordinateSpace = z.literal('percent_0_100');

export const ObjectLabel = z.object({
  id: z.string().min(1).max(96),
  label_key: z.string().min(1).max(128).regex(/^[a-z0-9_ -]+$/),
  label_name: z.string().min(1).max(128),
  label_type: ObjectLabelType,
  category: ObjectLabelCategory,
  sample_count: z.number().int().nonnegative(),
  is_active: z.boolean(),
  deleted_at: DateTimeString.nullable(),
  created_at: DateTimeString,
  updated_at: DateTimeString,
});

export const CreateLabelRequest = z.object({
  label_name: z.string().trim().min(1).max(128),
  category: z.enum(['person', 'vehicle_shape']),
});

export const UpdateLabelRequest = z.object({
  label_name: z.string().trim().min(1).max(128).optional(),
  category: z.enum(['person', 'vehicle_shape']).optional(),
}).refine((v) => v.label_name !== undefined || v.category !== undefined, {
  message: 'At least one field is required.',
});

export const DatasetSource = z.object({
  id: z.string().min(1).max(96),
  name: z.string().min(1).max(128),
  kind: DatasetSourceKind,
  public_url: z.string().min(1),
  original_filename: z.string().min(1).max(255),
  mime_type: z.enum(['image/jpeg', 'image/png', 'video/mp4', 'video/quicktime']),
  file_size_bytes: z.number().int().positive(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  duration_seconds: z.number().nonnegative().nullable(),
  total_frames: z.number().int().nonnegative().nullable(),
  fps: z.number().positive().nullable(),
  width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(),
  import_status: ImportStatus,
  import_error: z.string().nullable(),
  created_at: DateTimeString,
  updated_at: DateTimeString,
});

export const BBoxPercent = z.object({
  x: z.number().min(0).max(100),
  y: z.number().min(0).max(100),
  w: z.number().gt(0).max(100),
  h: z.number().gt(0).max(100),
}).refine((b) => b.x + b.w <= 100 && b.y + b.h <= 100, {
  message: 'BBox must fit within percent_0_100 coordinate space.',
});

export const BBoxSampleLabelSummary = z.object({
  id: z.string().min(1).max(96),
  label_key: z.string().min(1).max(128),
  label_name: z.string().min(1).max(128),
});

export const BBoxSample = z.object({
  id: z.string().min(1).max(96),
  label_id: z.string().min(1).max(96),
  source_id: z.string().min(1).max(96),
  frame_index: z.number().int().nonnegative().nullable(),
  frame_timestamp_seconds: z.number().nonnegative().nullable(),
  bbox: BBoxPercent,
  coordinate_space: CoordinateSpace,
  label: BBoxSampleLabelSummary,
  created_at: DateTimeString,
  updated_at: DateTimeString,
});

export const CreateBBoxSampleItem = z.object({
  label_id: z.string().min(1).max(96),
  source_id: z.string().min(1).max(96),
  frame_index: z.number().int().nonnegative().nullable().optional(),
  frame_timestamp_seconds: z.number().nonnegative().nullable().optional(),
  bbox: BBoxPercent,
});

export const BatchCreateSamplesRequest = z.object({
  samples: z.array(CreateBBoxSampleItem).min(1).max(200),
});

export const UpdateBBoxSampleRequest = z.object({
  label_id: z.string().min(1).max(96).optional(),
  frame_index: z.number().int().nonnegative().nullable().optional(),
  frame_timestamp_seconds: z.number().nonnegative().nullable().optional(),
  bbox: BBoxPercent.optional(),
}).refine((v) => v.label_id !== undefined || v.frame_index !== undefined || v.frame_timestamp_seconds !== undefined || v.bbox !== undefined, {
  message: 'At least one field is required.',
});

export const ZoneCacheInfo = z.object({
  camera_id: z.string().min(1),
  zone_version: z.number().int().positive(),
  cache_status: z.enum(['hot', 'refreshing']),
  refreshed_at: DateTimeString,
});

export const ZoneSyncResult = z.object({
  synced_labels: z.array(z.string()),
  affected_zones: z.array(z.string()),
  default_rule: z.literal('forbidden'),
  cache: z.array(ZoneCacheInfo),
});

export const LabelListResponse = makeApiResponse(z.object({ items: z.array(ObjectLabel) }));
export const LabelMutationResponse = makeApiResponse(z.object({ label: ObjectLabel, sync: ZoneSyncResult.optional() }));
export const SourceListResponse = makeApiResponse(z.object({
  items: z.array(DatasetSource),
  page: z.number().int().positive(),
  limit: z.number().int().positive(),
  total_items: z.number().int().nonnegative(),
  total_pages: z.number().int().nonnegative(),
}));
export const SourceResponse = makeApiResponse(z.object({ source: DatasetSource }));
export const SampleListResponse = makeApiResponse(z.object({ items: z.array(BBoxSample) }));
export const BatchCreateSamplesResponse = makeApiResponse(z.object({
  saved_count: z.number().int().nonnegative(),
  samples: z.array(BBoxSample),
  labels: z.array(ObjectLabel),
}));
export const SampleMutationResponse = makeApiResponse(z.object({
  sample: BBoxSample.optional(),
  deleted_id: z.string().optional(),
  labels: z.array(ObjectLabel),
}));
export const SyncZonesResponse = makeApiResponse(z.object({ sync: ZoneSyncResult }));
```

## Validation

- `label_name` được trim trước khi sinh key; tên rỗng trả `VALIDATION_ERROR`.
- Create/rename/restore custom label phải chặn duplicate không phân biệt hoa/thường bằng `DUPLICATE_LABEL_NAME`.
- System label bị chặn `PUT`, `DELETE`, restore bằng `SYSTEM_LABEL_LOCKED`.
- Soft delete custom label đang nằm trong zone allowed/forbidden rules bị chặn bằng `LABEL_IN_USE_BY_ZONE`.
- Deleted/inactive label không được dùng để tạo hoặc update bbox sample; trả `LABEL_INACTIVE`.
- Batch samples là all-or-nothing. Backend validate toàn bộ source, label, frame selector và bbox trước khi ghi.
- Video samples bắt buộc có `frame_index`; image samples nếu thiếu `frame_index` thì response normalize về `0`.
- BBox dùng `percent_0_100`; bbox rỗng/quá nhỏ trả `VALIDATION_ERROR`.
- Source upload phải tính metadata và trả `import_status`. Chỉ source `ready` mới được annotate.
- Zone sync không được xóa cấu hình allowed/forbidden hiện có; chỉ append active custom labels còn thiếu vào forbidden.

## Error Model

Mọi JSON error dùng envelope chuẩn với `success: false`, `data: null`, và `ErrorPayload` cụ thể.

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `BAD_REQUEST` | Request sai cấu trúc hoặc truyền tham số loại trừ nhau. |
| 400 | `VALIDATION_ERROR` | JSON hợp schema nhưng sai business validation. |
| 400 | `DUPLICATE_LABEL_NAME` | Create/rename/restore vi phạm uniqueness không phân biệt hoa/thường. |
| 400 | `SYSTEM_LABEL_LOCKED` | Đang cố rename/delete/restore system label. |
| 409 | `LABEL_IN_USE_BY_ZONE` | Soft delete bị chặn vì label còn trong zone rules. |
| 409 | `LABEL_INACTIVE` | Đang annotate bằng inactive/deleted label. |
| 409 | `SOURCE_NOT_READY` | Source đang processing/failed hoặc thiếu media metadata. |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | MIME type hoặc codec không hỗ trợ. |
| 413 | `UPLOAD_TOO_LARGE` | File vượt giới hạn 250 MB. |
| 404 | `NOT_FOUND` | Không tìm thấy label, source, sample hoặc frame. |
| 404 | `FRAME_NOT_AVAILABLE` | Frame index/timestamp nằm ngoài giới hạn source. |
| 409 | `ZONE_CACHE_REFRESH_FAILED` | DB sync đã commit nhưng refresh runtime cache fail; client có thể retry sync. |
| 500 | `INTERNAL_SERVER_ERROR` | Lỗi backend không mong muốn. |

Binary frame endpoint khi lỗi vẫn trả JSON envelope với `application/json`.

## Authentication and Authorization

- Local deployment hiện chưa có auth layer; contract vẫn ghi role để giữ compatibility sau này.
- Viewer/Admin được đọc labels, sources, samples và frame previews.
- Chỉ Admin được upload source, create/rename/delete/restore labels, create/update/delete samples và sync zones.
- Khi chưa có auth, backend có thể cho phép local unauthenticated requests, nhưng code endpoint phải dễ gắn role checks mà không đổi schema.
- Uploaded media chỉ được ghi trong managed backend storage; API không nhận/trả unsafe absolute filesystem paths.

## Pagination and Versioning

- `GET /dataset/sources` phân trang bằng `page` và `limit`; default `page=1`, `limit=50`, max `100`.
- Label list và sample list chưa phân trang trong CR-004 vì annotation screen dự kiến ít item. Nếu tăng dữ liệu, pagination phải là additive và dùng cùng meta shape.
- API version giữ `/api/v1`; CR-004 là additive trong v1.
- Upload source nên hỗ trợ idempotency bằng `idempotency_key` và/hoặc `sha256`; upload lặp cùng key trả source cũ với HTTP 200, không tạo duplicate.
- Response schemas strict cho required fields. Backend-internal fields không được emit nếu chưa có task approved bổ sung contract.

## Compatibility

- `backend/app/api/v1/dataset.py` hiện trả direct arrays/objects ở vài endpoint. `TASK-023` phải chuẩn hóa JSON endpoints của CR-004 sang global envelope trong contract này.
- Frontend hiện dùng local `objLabels`, `annSources`, `annSamples`. `TASK-024` phải map UI types: `ObjectLabel.kind` từ `category`, `AnnotationSource.img` từ `public_url`, `AnnotationSample.frame` từ `frame_index`.
- `/api/v1/zones/video-frame` hiện vẫn dùng cho camera background preview. Dataset frame từ imported source phải dùng `/api/v1/dataset/sources/{source_id}/frame`.
- Global API contract cũ có nhắc `/api/v1/labels` và `/api/v1/annotation-samples`; đó là legacy naming. CR-004 dùng `/api/v1/dataset/*` theo router hiện hữu.
- `zones.allowed_classes` và `zones.forbidden_classes` tiếp tục dùng string label keys/classes. Sync phải giữ system object keys hiện có và append custom keys mặc định forbidden.

## Open Questions

- Không có blocker. Requirements và `TASK-020` đã quyết định managed backend storage, sync mặc định `forbidden`, soft delete/restore, bbox edit support, và không hứa realtime custom-class inference.

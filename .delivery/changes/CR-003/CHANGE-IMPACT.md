---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: approved
updated_at: "2026-08-20T17:25:00+07:00"
change_id: CR-003
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, API-CONTRACT.md, MASTER-PLAN.md]
---

# Đánh giá Ảnh hưởng Thay đổi (Change Impact Assessment) cho CR-003

## Ghi chú thực thi skill
- Requested skill: `assess-change-impact`
- Status: không có trong danh sách skill của workspace hiện tại vào ngày 2026-08-20.
- Fallback executed: tạo artifact đánh giá ảnh hưởng theo đúng mục tiêu của skill, không sửa code ứng dụng, không thay thế `MASTER-PLAN.md` dùng chung.

## Tóm tắt thay đổi
- Business delta: Luồng `Giám sát khu vực` phải chuyển từ polling detections/events sang realtime metadata riêng; sử dụng zone cache in-memory theo `camera_id`; giữ video stream renderer tách biệt khỏi metadata stream; và không đưa database vào hot path mỗi frame.
- Phạm vi focus: chỉ tác động lên pipeline `Area Zone Monitoring` và các hợp đồng runtime/API phục vụ tab `Area Security Dashboard`.
- Affected requirements: `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`

## Bằng chứng baseline
- Hiện trạng contract vẫn đưa UI theo hướng WebSocket event tổng hợp và REST polling cho `events`, chưa có kênh realtime metadata riêng cho area monitoring.
- Hiện trạng backend đã có dấu hiệu phù hợp với hướng mới ở `backend/app/services/video_stream.py`: `CameraFramePipeline` duy trì `_zones` in-memory và `ProcessedFrameSnapshot` tach frame với detections.
- Hiện trạng `backend/app/services/event_manager.py` vẫn có hot path gắn với clip slicing/file I/O cho event sau khi trigger; cần xác lập rõ ranh giới giữa realtime metadata và persistence/event recording.

## Tác động trực tiếp
Những task/hop dong chịu tác động trực tiếp bởi CR-003:
- `REQ-002` cần bổ sung yêu cầu metadata realtime riêng cho camera khu vực, UI không phụ thuộc polling detections/events để cập nhật mỗi frame.
- `REQ-004` cần làm rõ cooldown/dedup chỉ áp dụng cho event persistence và alert, không chặn luồng metadata frame-to-frame.
- `REQ-005` cần làm rõ zone update được đẩy vào zone cache in-memory theo `camera_id` và có hiệu lực ngay cho pipeline không qua DB read mỗi frame.
- `REQ-009` cần làm rõ thông báo Mức 3 xuất phát từ event lane riêng, không trùng với metadata lane.
- `.delivery/ARCHITECTURE.md` cần bổ sung boundary mới: `area-metadata-stream` và `zone-cache` nằm ngoài DB hot path.
- `.delivery/API-CONTRACT.md` cần bổ sung hoặc tach hop dong cho metadata stream riêng của `Area Security Dashboard`, đồng thời giữ stream video/annotated video thành kênh tách biệt.
- `docs/contracts/api/websocket-events.json` cần thêm schema payload metadata theo frame/snapshot cho area monitoring, hoặc schema cho kênh subscription riêng.
- `docs/contracts/api/api-schema.json` cần cập nhật object schema cho area snapshot metadata, zone cache invalidation/versioning, và readiness/health fields.

## Tác động task bắc cầu
- `TASK-002` — module `none` — status `ready` — `direct` candidate — packet action `supplement-contract`
- `TASK-007` — module `ai-vision-pipeline` — status `ready` — `direct` candidate — packet action `split-or-supersede`
- `TASK-010` — module `web-ui` — status `blocked` — `direct` candidate — packet action `create-follow-up`
- `TASK-012` — module `web-ui` — status `blocked` — `transitive` candidate — packet action `create-follow-up`
- `TASK-014` — module `alert-dispatcher` — status `ready` — `transitive` candidate — packet action `supplement-contract`
- `TASK-015` — module `none` — status `ready` — `transitive` candidate — packet action `extend-verification`

## Bằng chứng không ảnh hưởng
- `REQ-001` luong LPR cong vào không cần đổi giao thức hot path theo CR-003.
- `REQ-006`, `REQ-007`, `REQ-008` và storage cho whitelist/custom labels/AI assistant không nam trong hot path mỗi frame của area monitoring, nên chỉ bị ảnh hưởng gián tiếp nếu event schema doi.
- Không có yêu cầu thay đổi schema DB để đáp ứng zone cache in-memory; DB vẫn là source-of-truth cho CRUD zone và event history, nhưng không được nằm trên đường xử lý mỗi frame.

## Tác động contract và artifact

### Impact on `.delivery/REQUIREMENTS.md`
- Cần thêm audit trail `CR-003` mới.
- Cần cập nhật `REQ-002` để mô tả hai luồng riêng: `video stream` và `area metadata stream`.
- Cần cập nhật `REQ-004` để tách `event deduplication` khỏi `per-frame metadata publication`.
- Cần cập nhật `REQ-005` để bắt buộc cache zone in-memory theo `camera_id`, có cơ chế refresh/invalidate sau CRUD zone.
- Có thể cập nhật `REQ-009` để lam rõ alert lane consume event đã dedup thay vì consume metadata snapshot trực tiếp.

### Impact on `.delivery/ARCHITECTURE.md`
- Cần bo sung module/trách nhiệm `zone-cache` thuộc backend runtime.
- Cần cập nhật data flow: `CameraFramePipeline` -> `Area Metadata Publisher` -> UI; event persistence và alert tro thành lane song song.
- Cần ghi rõ DB chỉ được dung cho control plane (`zone CRUD`, `event history`, `analytics/query`), không được đọc trong frame loop.
- Cần đánh dấu xung đột định danh: file hien đang có dòng `CR-003 Audit` mang nghĩa khác (YOLO-World v2). Không rewrite trong bước này; cần đổi tên audit cũ hoặc đổi ma change request lịch sử trong đợt tài liệu sau.

### Impact on `.delivery/API-CONTRACT.md`
- Cần thêm section mới cho `Area Realtime Metadata Contract`.
- Cần xác định rõ transport:
  `Option A`: WebSocket event type mới, vi du `AREA_FRAME_METADATA`.
  `Option B`: subscription/channel riêng, vi du `/ws/v1/area-metadata`.
- Cần xác định payload tối thiểu:
  `camera_id`, `frame_id`, `captured_at`, `zone_version`, `objects[]`, `zone_hits[]`, `pipeline_latency_ms`, `stream_status`.
- Cần ghi rõ `events`/`alerts` la derived stream, không dùng để vẽ overlay mỗi frame.

### Impact on `MASTER-PLAN.md`
- Không sua để tránh thay thế shared plan.
- Cần bổ sung một plan riêng cho CR-003, liên kết tham chiếu ve `MASTER-PLAN.md`.
- Các task cũ không nên rewrite; nên tạo task mới để bo sung contract/backend/frontend/verification cho CR-003.

### Impact on `.delivery/tasks`
- Nen tao task mới thay vì sua packet cu.
- De xuat it nhat 3 task mới:
  `TASK-016`: thiết kế contract metadata realtime và cache semantics.
  `TASK-017`: backend implementation cho area metadata lane + zone cache invalidation.
  `TASK-018`: frontend Area Dashboard consume metadata lane riêng, giữ video stream renderer tách biệt.
- Có thêm `TASK-019` verification nếu đổi scope cần nghiệm thu performance/non-regression.

## Khóa chọn lọc
- Khoa chon loc cac phạm vi tài liệu và implementation có rủi rõ cao: `ai-vision-pipeline`, `api-gateway`, `web-ui`, `alert-dispatcher`, `docs/contracts/api`.
- Không khóa `database-storage` theo nghia migration/schema, vi CR-003 chủ yếu giảm DB khỏi hot path thay vì đổi data model lưu trữ.

## Hành động packet
- Tao plan bo sung cho `CR-003`, không chỉnh sửa `MASTER-PLAN.md`.
- Tao task mới `TASK-016`, `TASK-017`, `TASK-018`, `TASK-019` trong `.delivery/tasks/`.
- Đánh dấu `TASK-010` và `TASK-012` cần follow-up từ CR-003, không mở lại packet cũ trong bước này.

## Quyết định cần owner xác nhận
- Xac nhan có chấp nhận sự tồn tại của hai nghia `CR-003` trong lịch sử tài liệu hay yêu cầu đổi tên audit cũ trong đợt tiep theo.
- Chon hình thức contract realtime metadata: event type mới trên WebSocket hiện tại hay channel riêng.
- Xac nhan UI Area Dashboard sẽ render overlay bbox/zone từ đâu:
  từ backend annotated video,
  hay từ metadata stream/client overlay,
  hay che do hybrid.

## Thứ tự cập nhật
1. Phe duyet `CR-003/CHANGE-IMPACT.md`.
2. Tao plan bo sung cho `CR-003` ma không sua `MASTER-PLAN.md`.
3. Tao task packets mới được trace từ CR-003.
4. Sau khi được phê duyệt mới cập nhật `REQUIREMENTS.md`, `ARCHITECTURE.md`, `API-CONTRACT.md` và `docs/contracts/api/*`.

## Kế hoạch xác minh
- Review traceability từ `CR-003` sang `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`.
- Kiểm tra contract draft có tach rõ `video stream`, `metadata stream`, `event stream`.
- Kiểm tra task mới không overwrite task cũ và không sua `MASTER-PLAN.md`.

---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: in-review
updated_at: "2026-08-20T17:25:00+07:00"
change_id: CR-003
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, API-CONTRACT.md, MASTER-PLAN.md]
---

# Danh gia Anh huong Thay doi (Change Impact Assessment) cho CR-003

## Skill Execution Note
- Requested skill: `assess-change-impact`
- Status: khong co trong danh sach skill cua workspace hien tai vao ngay 2026-08-20.
- Fallback executed: tao artifact danh gia anh huong theo dung muc tieu cua skill, khong sua code ung dung, khong thay the `MASTER-PLAN.md` dung chung.

## Change Summary
- Business delta: Luong `Giam sat khu vuc` phai chuyen tu polling detections/events sang realtime metadata rieng; su dung zone cache in-memory theo `camera_id`; giu video stream renderer tach biet khoi metadata stream; va khong dua database vao hot path moi frame.
- Scope focus: chi tac dong len pipeline `Area Zone Monitoring` va cac hop dong runtime/API phuc vu tab `Area Security Dashboard`.
- Affected requirements: `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`

## Baseline Evidence
- Hien trang contract van dua UI theo huong WebSocket event tong hop va REST polling cho `events`, chua co kenh realtime metadata rieng cho area monitoring.
- Hien trang backend da co dau hieu phu hop voi huong moi o `backend/app/services/video_stream.py`: `CameraFramePipeline` duy tri `_zones` in-memory va `ProcessedFrameSnapshot` tach frame voi detections.
- Hien trang `backend/app/services/event_manager.py` van co hot path gan voi clip slicing/file I/O cho event sau khi trigger; can xac lap ro ranh gioi giua realtime metadata va persistence/event recording.

## Direct Impact
Nhung task/hop dong chiu tac dong truc tiep boi CR-003:
- `REQ-002` can bo sung yeu cau metadata realtime rieng cho camera khu vuc, UI khong phu thuoc polling detections/events de cap nhat moi frame.
- `REQ-004` can lam ro cooldown/dedup chi ap dung cho event persistence va alert, khong chan luong metadata frame-to-frame.
- `REQ-005` can lam ro zone update duoc day vao zone cache in-memory theo `camera_id` va co hieu luc ngay cho pipeline khong qua DB read moi frame.
- `REQ-009` can lam ro thong bao Muc 3 xuat phat tu event lane rieng, khong trung voi metadata lane.
- `.delivery/ARCHITECTURE.md` can bo sung boundary moi: `area-metadata-stream` va `zone-cache` nam ngoai DB hot path.
- `.delivery/API-CONTRACT.md` can bo sung hoac tach hop dong cho metadata stream rieng cua `Area Security Dashboard`, dong thoi giu stream video/annotated video thanh kenh tach biet.
- `docs/contracts/api/websocket-events.json` can them schema payload metadata theo frame/snapshot cho area monitoring, hoac schema cho kenh subscription rieng.
- `docs/contracts/api/api-schema.json` can cap nhat object schema cho area snapshot metadata, zone cache invalidation/versioning, va readiness/health fields.

## Transitive Task Impact
- `TASK-002` — module `none` — status `ready` — `direct` candidate — packet action `supplement-contract`
- `TASK-007` — module `ai-vision-pipeline` — status `ready` — `direct` candidate — packet action `split-or-supersede`
- `TASK-010` — module `web-ui` — status `blocked` — `direct` candidate — packet action `create-follow-up`
- `TASK-012` — module `web-ui` — status `blocked` — `transitive` candidate — packet action `create-follow-up`
- `TASK-014` — module `alert-dispatcher` — status `ready` — `transitive` candidate — packet action `supplement-contract`
- `TASK-015` — module `none` — status `ready` — `transitive` candidate — packet action `extend-verification`

## Unaffected Evidence
- `REQ-001` luong LPR cong vao khong can doi giao thuc hot path theo CR-003.
- `REQ-006`, `REQ-007`, `REQ-008` va storage cho whitelist/custom labels/AI assistant khong nam trong hot path moi frame cua area monitoring, nen chi bi anh huong gian tiep neu event schema doi.
- Khong co yeu cau thay doi schema DB de dap ung zone cache in-memory; DB van la source-of-truth cho CRUD zone va event history, nhung khong duoc nam tren duong xu ly moi frame.

## Contract and Artifact Impact

### Impact on `.delivery/REQUIREMENTS.md`
- Can them audit trail `CR-003` moi.
- Can cap nhat `REQ-002` de mo ta hai luong rieng: `video stream` va `area metadata stream`.
- Can cap nhat `REQ-004` de tach `event deduplication` khoi `per-frame metadata publication`.
- Can cap nhat `REQ-005` de bat buoc cache zone in-memory theo `camera_id`, co co che refresh/invalidate sau CRUD zone.
- Co the cap nhat `REQ-009` de lam ro alert lane consume event da dedup thay vi consume metadata snapshot truc tiep.

### Impact on `.delivery/ARCHITECTURE.md`
- Can bo sung module/trach nhiem `zone-cache` thuoc backend runtime.
- Can cap nhat data flow: `CameraFramePipeline` -> `Area Metadata Publisher` -> UI; event persistence va alert tro thanh lane song song.
- Can ghi ro DB chi duoc dung cho control plane (`zone CRUD`, `event history`, `analytics/query`), khong duoc doc trong frame loop.
- Can danh dau xung dot dinh danh: file hien dang co dong `CR-003 Audit` mang nghia khac (YOLO-World v2). Khong rewrite trong buoc nay; can doi ten audit cu hoac doi ma change request lich su trong dot tai lieu sau.

### Impact on `.delivery/API-CONTRACT.md`
- Can them section moi cho `Area Realtime Metadata Contract`.
- Can xac dinh ro transport:
  `Option A`: WebSocket event type moi, vi du `AREA_FRAME_METADATA`.
  `Option B`: subscription/channel rieng, vi du `/ws/v1/area-metadata`.
- Can xac dinh payload toi thieu:
  `camera_id`, `frame_id`, `captured_at`, `zone_version`, `objects[]`, `zone_hits[]`, `pipeline_latency_ms`, `stream_status`.
- Can ghi ro `events`/`alerts` la derived stream, khong dung de ve overlay moi frame.

### Impact on `MASTER-PLAN.md`
- Khong sua de tranh thay the shared plan.
- Can bo sung mot plan rieng cho CR-003, lien ket tham chieu ve `MASTER-PLAN.md`.
- Cac task cu khong nen rewrite; nen tao task moi de bo sung contract/backend/frontend/verification cho CR-003.

### Impact on `.delivery/tasks`
- Nen tao task moi thay vi sua packet cu.
- De xuat it nhat 3 task moi:
  `TASK-016`: thiet ke contract metadata realtime va cache semantics.
  `TASK-017`: backend implementation cho area metadata lane + zone cache invalidation.
  `TASK-018`: frontend Area Dashboard consume metadata lane rieng, giu video stream renderer tach biet.
- Co them `TASK-019` verification neu doi scope can nghiem thu performance/non-regression.

## Selective Lock
- Khoa chon loc cac pham vi tai lieu va implementation co rui ro cao: `ai-vision-pipeline`, `api-gateway`, `web-ui`, `alert-dispatcher`, `docs/contracts/api`.
- Khong khoa `database-storage` theo nghia migration/schema, vi CR-003 chu yeu giam DB khoi hot path thay vi doi data model luu tru.

## Packet Actions
- Tao plan bo sung cho `CR-003`, khong chinh sua `MASTER-PLAN.md`.
- Tao task moi `TASK-016`, `TASK-017`, `TASK-018`, `TASK-019` trong `.delivery/tasks/`.
- Danh dau `TASK-010` va `TASK-012` can follow-up tu CR-003, khong mo lai packet cu trong buoc nay.

## Owner Decisions Required
- Xac nhan co chap nhan su ton tai cua hai nghia `CR-003` trong lich su tai lieu hay yeu cau doi ten audit cu trong dot tiep theo.
- Chon hinh thuc contract realtime metadata: event type moi tren WebSocket hien tai hay channel rieng.
- Xac nhan UI Area Dashboard se render overlay bbox/zone tu dau:
  tu backend annotated video,
  hay tu metadata stream/client overlay,
  hay che do hybrid.

## Update Order
1. Phe duyet `CR-003/CHANGE-IMPACT.md`.
2. Tao plan bo sung cho `CR-003` ma khong sua `MASTER-PLAN.md`.
3. Tao task packets moi duoc trace tu CR-003.
4. Sau khi duoc phe duyet moi cap nhat `REQUIREMENTS.md`, `ARCHITECTURE.md`, `API-CONTRACT.md` va `docs/contracts/api/*`.

## Validation Plan
- Review traceability tu `CR-003` sang `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`.
- Kiem tra contract draft co tach ro `video stream`, `metadata stream`, `event stream`.
- Kiem tra task moi khong overwrite task cu va khong sua `MASTER-PLAN.md`.


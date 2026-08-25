---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T19:32:23+07:00"
task_id: TASK-017
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Gói Task: TASK-017 — Backend Area Metadata Lane và Zone Cache

- Mã task: TASK-017
- Loại task: implementation
- Phạm vi: feature
- Module: ai-vision-pipeline
- Năng lực: backend-implementation
- Yêu cầu liên kết: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Phụ thuộc: TASK-016
- Phạm vi ghi: .delivery/tasks/TASK-017/
- Đầu vào: `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `backend/app/api/v1/events.py`, `backend/app/api/v1/zones.py`, `backend/app/api/v1/websocket.py`, `backend/app/services/video_stream.py`, `backend/app/services/vision_pipeline.py`, `backend/database/repository.py`
- Đầu ra dự kiến: `backend/app/services/zone_cache.py`, `backend/app/services/area_metadata.py`, backend runtime updates under `backend/app/api/v1/` and `backend/app/services/`, backend tests, `.delivery/tasks/TASK-017/TASK-RESULT.md`
- Điều kiện hoàn thành: Frame loop area monitoring không đọc DB mỗi frame; zone rules được lấy từ in-memory cache theo `camera_id`; metadata realtime và event persistence được tách lane rõ ràng.
- Chính sách phê duyệt: Project owner review required before promoting `TASK-RESULT.md` from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if implementation requires changing approved contracts, database schema, frontend code, or files outside backend scope plus `.delivery/tasks/TASK-017/`.

## Execution Brief

### Objective
Implement the backend CR-003 area metadata lane and in-memory zone cache so area monitoring does not read the database on every frame and metadata/event persistence lanes are separated.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-017/TASK-PACKET.md`
- `.delivery/tasks/TASK-017/TASK-RESULT.md`
- `.delivery/tasks/TASK-017/BUG-DIAGNOSIS.md` if present
- `.delivery/tasks/TASK-017/BUG-001.md` through `.delivery/tasks/TASK-017/BUG-004.md` if present
- `.delivery/tasks/TASK-016/API-CONTRACT.md`
- `.delivery/ARCHITECTURE.md`
- `backend/app/api/v1/events.py`
- `backend/app/api/v1/zones.py`
- `backend/app/api/v1/websocket.py`
- `backend/app/services/video_stream.py`
- `backend/app/services/vision_pipeline.py`
- `backend/database/repository.py`
- `.delivery/MASTER-PLAN.md` section `TASK-017 Backend Area Metadata Lane và Zone Cache`

### Allowed write scope
- Historical task scope: `backend/app/`, `backend/tests/`, `.delivery/tasks/TASK-017/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-017/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `BUG-*.md`, `BUG-DIAGNOSIS.md`, frontend code, approved API contracts, database schema, runtime DB files, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-017`, capability `backend-implementation`, dependency `TASK-016`, linked requirements, expected outputs, and completion gate.
- Frame loop uses cached zone rules by `camera_id` instead of DB reads per frame.
- Backend emits realtime metadata lane per TASK-016 contract while preserving violation event persistence and alert behavior.
- Bug records and diagnosis artifacts remain historical evidence, not rewritten conclusions.

### Edge cases / risks
- MASTER-PLAN status is `needs-revision`; TASK-RESULT/bugs must be read before claiming completion.
- Zone cache invalidation can become stale after zone CRUD updates.
- Event persistence can regress if metadata emission bypasses violation creation.
- Not specified in source artifacts: cache TTL, concurrency model under multiple cameras, max metadata payload size, and performance benchmark threshold beyond "no DB each frame".

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python -m pytest backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py backend/tests/test_gate_zones.py -q`.
- Also validate bug-specific regressions documented under TASK-017 when present.

### Escalation conditions
- Escalate before changing approved contracts, database schema, frontend code, persistence semantics, or files outside backend scope plus `.delivery/tasks/TASK-017/`.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Implementation summary.
- Verification evidence with exact pytest output.
- Deviations and bug follow-up.
- Blockers and scope-change requests.

### Skill/capability to run
- `backend-implementation`.

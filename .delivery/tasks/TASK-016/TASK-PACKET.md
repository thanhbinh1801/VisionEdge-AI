---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T18:44:06+07:00"
task_id: TASK-016
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Gói Task: TASK-016 — Thiết kế Contract Realtime Metadata cho Area Monitoring

- Mã task: TASK-016
- Loại task: design
- Phạm vi: feature
- Module: api-gateway
- Năng lực: api-design
- Yêu cầu liên kết: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Phụ thuộc: none
- Phạm vi ghi: .delivery/tasks/TASK-016/
- Đầu vào: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`
- Đầu ra dự kiến: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`
- Điều kiện hoàn thành: Xác định được contract metadata lane tách biệt với event lane, payload schema, versioning zone cache, và kỳ vọng tương thích ngược.
- Chính sách phê duyệt: Project owner review required before promoting task artifacts from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if changes outside `.delivery/tasks/TASK-016/` are required or if upstream approved contracts become contradictory.

## Required decisions
- Chọn WebSocket event type mới hay channel riêng.
- Chọn nguồn vẽ overlay của Area Dashboard.

## Execution Brief

### Objective
Design the CR-003 realtime metadata contract for Area Monitoring, separating video stream, realtime metadata, and event/alert lanes while preserving backward compatibility.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-016/TASK-PACKET.md`
- `.delivery/tasks/TASK-016/TASK-RESULT.md`
- `.delivery/tasks/TASK-016/API-CONTRACT.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/API-CONTRACT.md`
- `.delivery/changes/CR-003/CHANGE-IMPACT.md`
- `docs/contracts/api/api-schema.json`
- `docs/contracts/api/websocket-events.json`
- `.delivery/MASTER-PLAN.md` section `TASK-016 Thiết kế Contract Realtime Metadata cho Area Monitoring`

### Allowed write scope
- Historical task scope: `.delivery/tasks/TASK-016/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-016/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, draft JSON files, global contracts, production backend/frontend code, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-016`, capability `api-design`, linked requirements, expected outputs, and completion gate.
- Preserve the historical decision to use additive event type `AREA_FRAME_METADATA` on `/ws/v1/events`.
- Contract must define metadata lane payload, zone cache versioning, compatibility notes, and relationship to event/alert persistence.

### Edge cases / risks
- MASTER-PLAN now lists dependencies `TASK-010`, `TASK-014`, while the historical packet front matter listed no dependency; do not rewrite history in this packet.
- Contract drift may occur if global docs diverge from `.delivery/tasks/TASK-016/API-CONTRACT.md`.
- Not specified in source artifacts: complete production rollout procedure, client feature-flag plan, and all non-area-monitoring WebSocket events.

### Verification commands or validation method
- Historical validation: design validator for `TASK-016` passed per TASK-RESULT.
- Planned verification command from MASTER-PLAN: `python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-016 --scope feature`.
- Validate global JSON contract parseability when editing promoted contract artifacts.

### Escalation conditions
- Escalate if changes outside `.delivery/tasks/TASK-016/` are required, upstream approved contracts contradict each other, or compatibility assumptions need to change.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Design summary and required decisions.
- Verification evidence.
- Deviations from source artifacts.
- Blockers and scope-change requests.

### Skill/capability to run
- `api-design`.

---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-012
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-006, TASK-008]
---

# Gói Task: TASK-012 - Zone and Tag Settings

- Mã task: TASK-012
- Loại task: implementation
- Phạm vi: feature
- Module: web-ui
- Năng lực: frontend-implementation
- Yêu cầu liên kết: REQ-005, REQ-006, REQ-007, CR-001, CR-002
- Phụ thuộc: TASK-006, TASK-008
- Phạm vi ghi: .delivery/tasks/TASK-012/
- Đầu vào: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md, frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/
- Đầu ra dự kiến: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/, and .delivery/tasks/TASK-012/TASK-RESULT.md
- Điều kiện hoàn thành: Zone & Tag Settings supports polygon editing, known/unknown vehicle labeling, dataset BBox labeling, and synchronizes zone geometry/name to Area Dashboard state.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate if implementation requires backend schema changes, approved contract changes, or edits outside Zone/Tag frontend scope plus .delivery/tasks/TASK-012/.

## Ghi chú tái dựng

This packet was restored because `.delivery/tasks/TASK-012/TASK-PACKET.md` was missing while `TASK-RESULT.md` still exists.

## Execution Brief

### Objective
Implement or preserve Zone & Tag Settings with polygon editing, known/unknown vehicle labeling, dataset BBox tooling, and synchronization to Area Dashboard state.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-012/TASK-PACKET.md`
- `.delivery/tasks/TASK-012/TASK-RESULT.md`
- `.delivery/tasks/TASK-006/TASK-RESULT.md`
- `.delivery/tasks/TASK-008/TASK-RESULT.md`
- `docs/contracts/API-FOUNDATION.md` or `.delivery/API-CONTRACT.md`
- `docs/contracts/UI-UX-FOUNDATION.md` if present
- `frontend/src/pages/ZoneTagSettings.tsx`
- `frontend/src/components/zone/`
- `.delivery/MASTER-PLAN.md` section `TASK-012 Triển khai Tab 3 — Zone & Tag Settings`

### Allowed write scope
- Historical task scope: `frontend/src/pages/ZoneTagSettings.tsx`, `frontend/src/components/zone/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-012/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-012/TASK-RESULT.md`, backend schema/API code, unrelated frontend code, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-012`, capability `frontend-implementation`, dependencies `TASK-006`, `TASK-008`, linked requirements, expected outputs, and completion gate.
- UI supports SVG polygon editing, known/unknown vehicle label assignment, dataset BBox labeling, and zone geometry/name sync to Area Dashboard state.
- Historical reconstructed packet note remains intact.

### Edge cases / risks
- Packet was reconstructed from existing TASK-RESULT and master-plan data.
- Later CR-004 replaces mock/local object labeling with real persisted flows and must not be recorded as original TASK-012 behavior.
- Not specified in source artifacts: exact drag/resize handles, keyboard accessibility behavior, video scrubber frame extraction method, and original QA screenshots.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `npm --prefix frontend run build`.
- Use historical TASK-RESULT evidence when present and document missing original evidence as reconstructed.

### Escalation conditions
- Escalate before requiring backend schema changes, approved contract changes, or edits outside Zone/Tag frontend scope plus task artifacts.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Implementation summary.
- Verification evidence.
- Deviations, including reconstruction notes.
- Blockers and scope-change requests.

### Skill/capability to run
- `frontend-implementation`.

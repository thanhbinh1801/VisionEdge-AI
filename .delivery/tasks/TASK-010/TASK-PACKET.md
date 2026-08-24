---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-010
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-007, TASK-008]
---

# Gói Task: TASK-010 - Area Security Dashboard Baseline

- Mã task: TASK-010
- Loại task: implementation
- Phạm vi: feature
- Module: web-ui
- Năng lực: frontend-implementation
- Yêu cầu liên kết: REQ-002, CR-001, CR-002
- Phụ thuộc: TASK-007, TASK-008
- Phạm vi ghi: .delivery/tasks/TASK-010/
- Đầu vào: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md, frontend/src/pages/AreaSecurityDashboard.tsx, frontend/src/services/api.ts
- Đầu ra dự kiến: frontend/src/pages/AreaSecurityDashboard.tsx baseline area monitoring dashboard and .delivery/tasks/TASK-010/TASK-RESULT.md
- Điều kiện hoàn thành: Area Dashboard renders BAI-KIEM stream, displays zone-rule monitoring context for 8 object classes, and uses backend annotated MJPEG as the visual source of truth.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate if implementation requires backend changes, approved contract changes, or edits outside frontend Area Dashboard scope plus .delivery/tasks/TASK-010/.

## Ghi chú tái dựng

This packet was restored because `.delivery/tasks/TASK-010/TASK-PACKET.md` was missing while `TASK-RESULT.md` still exists.

## Execution Brief

### Objective
Implement or preserve the baseline Area Security Dashboard for BAI-KIEM stream monitoring, zone-rule context, and backend-annotated visual output.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-010/TASK-PACKET.md`
- `.delivery/tasks/TASK-010/TASK-RESULT.md`
- `.delivery/tasks/TASK-007/TASK-RESULT.md`
- `.delivery/tasks/TASK-008/TASK-RESULT.md`
- `docs/contracts/API-FOUNDATION.md` or `.delivery/API-CONTRACT.md`
- `docs/contracts/UI-UX-FOUNDATION.md` if present
- `frontend/src/pages/AreaSecurityDashboard.tsx`
- `frontend/src/services/api.ts`
- `.delivery/MASTER-PLAN.md` section `TASK-010 Triển khai Tab 2 — Area Security Dashboard (Bãi kiểm)`

### Allowed write scope
- Historical task scope: `frontend/src/pages/AreaSecurityDashboard.tsx`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-010/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-010/TASK-RESULT.md`, backend code, unrelated frontend pages/components, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-010`, capability `frontend-implementation`, dependencies `TASK-007`, `TASK-008`, linked requirements, expected output, and completion gate.
- Area Dashboard renders BAI-KIEM stream and displays zone-rule monitoring context for approved object classes.
- Backend annotated MJPEG remains the baseline visual source of truth, consistent with the restored packet note.

### Edge cases / risks
- Packet was reconstructed from existing TASK-RESULT and master-plan data.
- Later CR-003 work changes realtime metadata behavior and must not be back-applied as if it happened during TASK-010.
- Not specified in source artifacts: original UI screenshot, exact KPI list, browser matrix, and original manual QA notes.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `npm --prefix frontend run build`.
- Validate against existing TASK-RESULT evidence if present; otherwise mark missing historical evidence clearly.

### Escalation conditions
- Escalate before requiring backend changes, approved contract changes, or edits outside frontend Area Dashboard scope plus task artifacts.

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

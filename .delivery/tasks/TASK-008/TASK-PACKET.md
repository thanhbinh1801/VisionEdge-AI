---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-008
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-004, TASK-005]
---

# Gói Task: TASK-008 - Shared UI Components

- Mã task: TASK-008
- Loại task: implementation
- Phạm vi: feature
- Module: web-ui
- Năng lực: frontend-implementation
- Yêu cầu liên kết: REQ-003, REQ-009, CR-002
- Phụ thuộc: TASK-004, TASK-005
- Phạm vi ghi: .delivery/tasks/TASK-008/
- Đầu vào: docs/contracts/UI-UX-FOUNDATION.md
- Đầu ra dự kiến: frontend/src/components/ Header, Sidebar, AudioBeepPlayer, VideoModal
- Điều kiện hoàn thành: Shared Header, Sidebar, AudioBeepPlayer, and VideoModal components are implemented for the React UI.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate for approved UI contract changes, backend changes, or edits outside shared frontend component scope.

## Execution Brief

### Objective
Build the shared React UI components used across the SentriAI Mini tabs, including navigation, audio alert playback, and evidence video viewing.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-008/TASK-PACKET.md`
- `.delivery/tasks/TASK-008/TASK-RESULT.md`
- `.delivery/tasks/TASK-004/TASK-RESULT.md`
- `docs/contracts/UI-UX-FOUNDATION.md` if present
- Existing `frontend/src/components/`
- `.delivery/MASTER-PLAN.md` section `TASK-008 Phát triển Bộ Shared UI Components`

### Allowed write scope
- Historical task scope: `frontend/src/components/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-008/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-008/TASK-RESULT.md`, backend code, page-specific feature logic, database/API contracts, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-008`, capability `frontend-implementation`, dependencies `TASK-004`, `TASK-005`, linked requirements, expected output, and completion gate.
- Shared components include Header, Sidebar, AudioBeepPlayer for severity level 3 beep, and VideoModal for 10s evidence clips.
- Components follow the approved UI/UX foundation and remain reusable across feature pages.

### Edge cases / risks
- Browser audio policies may prevent immediate beep playback.
- Video evidence URLs may be missing, delayed, or point to placeholder files.
- Not specified in source artifacts: exact modal keyboard behavior, accessibility test matrix, media fallback copy, and component prop contracts.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `npm --prefix frontend run test`.
- If no frontend test runner exists, use lint/typecheck/build and document the limitation in TASK-RESULT.

### Escalation conditions
- Escalate before changing approved UI contract, backend/API contracts, alert semantics, or writing outside shared component scope.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Component summary.
- Verification evidence.
- Deviations/accessibility limitations.
- Blockers and scope-change requests.

### Skill/capability to run
- `frontend-implementation`.

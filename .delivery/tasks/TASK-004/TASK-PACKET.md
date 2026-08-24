---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-004
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-002]
---

# Gói Task: TASK-004 - UI/UX Foundation and React Design System

- Mã task: TASK-004
- Loại task: foundation-design
- Phạm vi: global
- Module: none
- Năng lực: ui-ux-foundation-design
- Yêu cầu liên kết: REQ-001, REQ-002, REQ-003, REQ-005, CR-002
- Phụ thuộc: TASK-002
- Phạm vi ghi: .delivery/tasks/TASK-004/
- Đầu vào: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Đầu ra dự kiến: docs/contracts/UI-UX-FOUNDATION.md, frontend/src/assets/
- Điều kiện hoàn thành: Publish UI/UX foundation defining palette, alert colors, four-tab layout, and Lucide icon system.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate if UI foundation changes product scope or approved navigation structure.

## Execution Brief

### Objective
Define the UI/UX foundation and React design system for the four-tab SentriAI Mini operator experience.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-004/TASK-PACKET.md`
- `.delivery/tasks/TASK-004/TASK-RESULT.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/ARCHITECTURE.md`
- Existing frontend assets/components if present
- `.delivery/MASTER-PLAN.md` section `TASK-004 Thiết kế UI/UX Foundation & React Design System`

### Allowed write scope
- Historical task scope: `docs/contracts/UI-UX-FOUNDATION.md`, `frontend/src/assets/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-004/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-004/TASK-RESULT.md`, production pages/components beyond the historical asset scope, backend code, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-004`, capability `ui-ux-foundation-design`, dependency `TASK-002`, linked requirements, expected outputs, and completion gate.
- UI foundation defines palette, alert color semantics, four-tab layout, Lucide icon use, and reusable design constraints for later frontend tasks.
- Foundation must support Gate Dashboard, Area Security Dashboard, Zone & Tag Settings, and AI Chatbot Assistant.

### Edge cases / risks
- UI choices may accidentally expand product scope or alter approved navigation.
- Accessibility and responsive behavior may be under-specified in early source artifacts.
- Not specified in source artifacts: exact typography scale, breakpoint table, focus-state matrix, and detailed empty/error state copy.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `npm --prefix frontend run test`.
- If the test script is unavailable, record the available substitute validation and limitation in TASK-RESULT.

### Escalation conditions
- Escalate before changing approved navigation, product scope, frontend stack, or writing outside the documented UI foundation scope.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Design-system summary.
- Verification evidence.
- Deviations and unresolved design gaps.
- Blockers and scope-change requests.

### Skill/capability to run
- `ui-ux-foundation-design`.

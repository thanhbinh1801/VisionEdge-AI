---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-005
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-002]
---

# Gói Task: TASK-005 - Backend and Frontend Scaffolding

- Mã task: TASK-005
- Loại task: foundation-design
- Phạm vi: global
- Module: none
- Năng lực: ui-ux-foundation-design
- Yêu cầu liên kết: REQ-001, REQ-002, REQ-005, CR-001, CR-002
- Phụ thuộc: TASK-002
- Phạm vi ghi: .delivery/tasks/TASK-005/
- Đầu vào: .delivery/ARCHITECTURE.md
- Đầu ra dự kiến: frontend/src/ Vite React SPA structure, backend/ Python module structure
- Điều kiện hoàn thành: Backend and frontend scaffolds exist with React, Tailwind, Lucide, Recharts, SVG Canvas support, and Python backend module layout.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate if scaffolding changes stack choice, runtime layout, or approved app boundaries.

## Execution Brief

### Objective
Create the initial backend and frontend scaffold for the approved monolithic Python FastAPI plus Vite React SPA architecture.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-005/TASK-PACKET.md`
- `.delivery/tasks/TASK-005/TASK-RESULT.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/MASTER-PLAN.md` section `TASK-005 Khởi tạo Cấu trúc Dự án Backend & Frontend Scaffolding`

### Allowed write scope
- Historical task scope: `frontend/src/App.tsx`, `frontend/src/main.tsx`, `backend/main.py`, and scaffold files needed under the stated backend/frontend structure.
- Current packet-normalization scope: only `.delivery/tasks/TASK-005/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-005/TASK-RESULT.md`, production feature logic beyond scaffold initialization, database schema, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-005`, capability `ui-ux-foundation-design`, dependency `TASK-002`, linked requirements, expected outputs, and completion gate.
- Scaffold includes React SPA structure with Tailwind CSS, Lucide React, Recharts, SVG Canvas Editor support, and Python backend module layout.
- Stack and runtime boundaries match the approved architecture.

### Edge cases / risks
- Scaffold can drift into feature implementation beyond foundation.
- Existing files may already contain later implementation work and must not be reset.
- Not specified in source artifacts: exact package versions, route skeleton list, CI setup, and deployment environment configuration.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `npm --prefix frontend run build`.
- Also validate backend import/startup if a local backend command is specified by architecture; otherwise record `Not specified in source artifacts`.

### Escalation conditions
- Escalate before changing stack choice, runtime layout, app boundaries, dependency manager, or writing outside scaffold scope.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Scaffold summary.
- Verification evidence.
- Deviations.
- Blockers and scope-change requests.

### Skill/capability to run
- `ui-ux-foundation-design`.

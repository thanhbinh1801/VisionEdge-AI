---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-19T14:02:00+07:00"
task_id: TASK-012
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-012 Chẩn đoán lỗi Tab 3 — Zone & Tag Settings (SVG Canvas Editor)

- Task ID: TASK-012
- Task type: bug
- Scope: feature
- Module: web-ui
- Capability: frontend-implementation
- Linked requirements: REQ-005, REQ-006, REQ-007, CR-002
- Dependencies: TASK-006, TASK-008
- Write scope: .delivery/tasks/TASK-012/
- Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md
- Expected outputs: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/
- Completion gate: Trang Cài đặt tích hợp SVG Canvas Polygon Editor, bảng gán nhãn xe 1-click và timeline scrubber gán nhãn dataset custom.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

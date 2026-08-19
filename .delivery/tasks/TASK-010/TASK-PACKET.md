---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-19T13:42:33+07:00"
task_id: TASK-010
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-010 Triển khai Tab 2 — Area Security Dashboard (Bãi kiểm)

- Task ID: TASK-010
- Task type: implementation
- Scope: feature
- Module: web-ui
- Capability: frontend-implementation
- Linked requirements: REQ-002, CR-002
- Dependencies: TASK-007, TASK-008
- Write scope: .delivery/tasks/TASK-010/
- Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md
- Expected outputs: frontend/src/pages/AreaSecurityDashboard.tsx
- Completion gate: Trang Bãi Kiểm & Xưởng An Ninh render 2 luồng video (`BAI_KIEM.mp4` 10s & `XUONG_AN_NINH.mp4` 4m32s), phát hiện vi phạm quy tắc zone bằng YOLO-World v2 & Ray-Casting PIP, bộ 4 thẻ Recharts KPI visualizers và luồng sự kiện vi phạm real-time.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

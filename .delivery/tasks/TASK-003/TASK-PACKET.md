---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-19T11:25:30+07:00"
task_id: TASK-003
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-003 Thiết kế CSDL & Database Schema Foundation

- Task ID: TASK-003
- Task type: foundation-design
- Scope: global
- Module: none
- Capability: database-design
- Linked requirements: REQ-001, REQ-002, REQ-006, CR-002
- Dependencies: TASK-002
- Write scope: .delivery/tasks/TASK-003/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Expected outputs: docs/contracts/db/schema.sql, .delivery/tasks/TASK-003/DATABASE-DESIGN.md, .delivery/tasks/TASK-003/TASK-RESULT.md
- Completion gate: Xuất bản tài liệu thiết kế CSDL (`DATABASE-DESIGN.md`), định nghĩa các thực thể Camera, Zone, Event, Tag và Script khởi tạo `schema.sql`.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

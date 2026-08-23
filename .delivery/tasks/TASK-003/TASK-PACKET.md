---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-003
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-002]
---

# Gói Task: TASK-003 - Đãtabase Schema Foundation

- Mã task: TASK-003
- Loại task: foundation-design
- Phạm vi: global
- Module: none
- Năng lực: database-design
- Yêu cầu liên kết: REQ-001, REQ-002, REQ-006, CR-002
- Phụ thuộc: TASK-002
- Phạm vi ghi: .delivery/tasks/TASK-003/
- Đầu vào: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Đầu ra dự kiến: .delivery/tasks/TASK-003/DATABASE-DESIGN.md, docs/contracts/db/schema.sql
- Điều kiện hoàn thành: Publish database design for Camera, Zone, Event, known/unknown vehicles, and BBox dataset samples.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate for schema changes that require migration or break current data access code.

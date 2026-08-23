---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-002
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-001]
---

# Gói Task: TASK-002 - Global API Foundation Contract

- Mã task: TASK-002
- Loại task: foundation-design
- Phạm vi: global
- Module: none
- Năng lực: api-foundation-design
- Yêu cầu liên kết: REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-009, CR-001, CR-002
- Phụ thuộc: TASK-001
- Phạm vi ghi: .delivery/tasks/TASK-002/
- Đầu vào: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Đầu ra dự kiến: .delivery/tasks/TASK-002/API-FOUNDATION.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Điều kiện hoàn thành: Publish REST API foundation covering 8 object classes, known/unknown vehicle labels, zone rules, and BBox dataset samples.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate if API design changes approved requirement semantics or breaks existing consumers.

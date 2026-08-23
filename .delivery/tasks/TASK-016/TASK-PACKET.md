---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T18:44:06+07:00"
task_id: TASK-016
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Gói Task: TASK-016 — Thiết kế Contract Realtime Metadata cho Area Monitoring

- Mã task: TASK-016
- Loại task: design
- Phạm vi: feature
- Module: api-gateway
- Năng lực: api-design
- Yêu cầu liên kết: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Phụ thuộc: none
- Phạm vi ghi: .delivery/tasks/TASK-016/
- Đầu vào: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`
- Đầu ra dự kiến: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`
- Điều kiện hoàn thành: Xác định được contract metadata lane tách biệt với event lane, payload schema, versioning zone cache, và kỳ vọng tương thích ngược.
- Chính sách phê duyệt: Project owner review required before promoting task artifacts from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if changes outside `.delivery/tasks/TASK-016/` are required or if upstream approved contracts become contradictory.

## Required decisions
- Chọn WebSocket event type mới hay channel riêng.
- Chọn nguồn vẽ overlay của Area Dashboard.

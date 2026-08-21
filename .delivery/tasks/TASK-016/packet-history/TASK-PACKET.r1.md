---
artifact: TASK-PACKET.md
version: "1.0"
task_id: TASK-016
owner: design-api
status: proposed
updated_at: "2026-08-20T17:25:00+07:00"
change_id: CR-003
---

# Task Packet: TASK-016 — Thiết kế Contract Realtime Metadata cho Area Monitoring

- Task type: thiết kế
- Scope: tính năng
- Module: api-gateway
- Capability: design-api
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Dependencies: `.delivery/changes/CR-003/CHANGE-IMPACT.md`
- Inputs: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`
- Outputs:
  - `.delivery/tasks/TASK-016/API-CONTRACT-ADDENDUM.md`
  - bản nháp cập nhật cho `docs/contracts/api/api-schema.json`
  - bản nháp cập nhật cho `docs/contracts/api/websocket-events.json`
- Completion gate: Xác định được contract metadata lane tách biệt với event lane, payload schema, versioning zone cache, và kỳ vọng tương thích ngược.
- Verification method: Rà soát artifact đối chiếu với `CR-003/CHANGE-IMPACT.md`
- Parallelizable: yes

## Required decisions
- Chọn WebSocket event type mới hay channel riêng.
- Chọn nguồn vẽ overlay của Area Dashboard.

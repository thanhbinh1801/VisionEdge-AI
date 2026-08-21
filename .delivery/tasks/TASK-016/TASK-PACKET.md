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

# Task Packet: TASK-016 — Thiết kế Contract Realtime Metadata cho Area Monitoring

- Task ID: TASK-016
- Task type: design
- Scope: feature
- Module: api-gateway
- Capability: api-design
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Dependencies: none
- Write scope: .delivery/tasks/TASK-016/
- Inputs: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`
- Expected outputs: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`
- Completion gate: Xác định được contract metadata lane tách biệt với event lane, payload schema, versioning zone cache, và kỳ vọng tương thích ngược.
- Approval policy: Project owner review required before promoting task artifacts from `in-review` to `approved`.
- Escalation policy: Escalate only if changes outside `.delivery/tasks/TASK-016/` are required or if upstream approved contracts become contradictory.

## Required decisions
- Chọn WebSocket event type mới hay channel riêng.
- Chọn nguồn vẽ overlay của Area Dashboard.

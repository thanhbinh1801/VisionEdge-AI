---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-27T10:45:12+07:00"
task_id: TASK-014
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-014 Tích hợp Realtime WebSocket Events & Multi-channel Alert

- Task ID: TASK-014
- Task type: implementation
- Scope: feature
- Module: alert-dispatcher
- Capability: frontend-implementation
- Linked requirements: REQ-003, REQ-009, CR-002
- Dependencies: TASK-007, TASK-008
- Write scope: .delivery/tasks/TASK-014/
- Inputs: docs/contracts/API-FOUNDATION.md
- Expected outputs: frontend/src/context/AlertContext.tsx, backend/api/websocket_gateway.py
- Completion gate: Phát còi bíp cảnh báo Mức 3 thời gian thực trên trình duyệt qua `<AudioBeepPlayer>` và gửi tin nhắn đính kèm ảnh crop sang Telegram Bot.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

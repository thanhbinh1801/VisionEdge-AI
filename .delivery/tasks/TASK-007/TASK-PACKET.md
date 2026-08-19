---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-19T12:22:14+07:00"
task_id: TASK-007
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-007 Triển khai Core AI Engine & React Custom Hooks

- Task ID: TASK-007
- Task type: implementation
- Scope: feature
- Module: ai-vision-pipeline
- Capability: backend-implementation
- Linked requirements: REQ-004, REQ-007, CR-002
- Dependencies: TASK-001, TASK-006
- Write scope: .delivery/tasks/TASK-007/
- Inputs: .delivery/ARCHITECTURE.md, docs/contracts/API-FOUNDATION.md
- Expected outputs: backend/ai/ (Evaluator & Slicer), backend/data/videos/ (2 Video Streams for Area Zone Monitoring), frontend/src/hooks/ (WebSocket & Sound Hooks)
- Completion gate: Triển khai thuật toán Point-in-Polygon, cửa sổ trượt lọc trùng lặp Cooldown 15s, 10s Ring Buffer Slicer tích hợp 2 video streams cho Area Zone Monitoring (BAI-KIEM 10s & XUONG-AN-NINH 4m32s) và custom hooks (`useWebSocket`, `useAudioAlert`).
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

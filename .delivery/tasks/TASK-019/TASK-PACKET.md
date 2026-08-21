---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T20:00:59+07:00"
task_id: TASK-019
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Task Packet: TASK-019 — Verification cho CR-003 Realtime Area Metadata

- Task ID: TASK-019
- Task type: verification
- Scope: feature
- Module: none
- Capability: feature-verification
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Dependencies: TASK-017
- Write scope: .delivery/tasks/TASK-019/
- Inputs: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `.delivery/tasks/TASK-018/TASK-RESULT.md`, backend/frontend implementation under `backend/app/` and `frontend/src/`
- Expected outputs: `.delivery/tasks/TASK-019/TEST-REPORT.md`, `.delivery/tasks/TASK-019/TASK-RESULT.md`, bug records if verification fails
- Completion gate:
  - Xác minh không có DB read trong hot path mỗi frame.
  - Xác minh area metadata stream cập nhật realtime mà không phụ thuộc polling detections/events.
  - Xác minh event/alert lane vẫn đúng cho severity và notification.
- Approval policy: Project owner review required before promoting verification artifacts from `in-review` to `approved`.
- Escalation policy: Escalate only if verification requires repairing production code, changing approved contracts, or running unavailable external infrastructure.

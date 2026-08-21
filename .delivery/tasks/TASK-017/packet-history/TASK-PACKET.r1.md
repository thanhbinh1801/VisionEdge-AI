---
artifact: TASK-PACKET.md
version: "1.0"
task_id: TASK-017
owner: implement-backend
status: proposed
updated_at: "2026-08-20T17:25:00+07:00"
change_id: CR-003
---

# Task Packet: TASK-017 — Backend Area Metadata Lane và Zone Cache

- Task type: triển khai
- Scope: tính năng
- Module: ai-vision-pipeline
- Capability: implement-backend
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Dependencies: `TASK-016`
- Inputs: `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-016/API-CONTRACT-ADDENDUM.md`
- Outputs:
  - ghi chú thiết kế/triển khai backend runtime
  - các hook invalidation zone cache sau CRUD zone
  - metadata publisher lane tách biệt với event persistence lane
- Completion gate: Frame loop area monitoring không đọc DB mỗi frame; zone rules được lấy từ in-memory cache theo `camera_id`; metadata realtime và event persistence được tách lane rõ ràng.
- Verification method: Backend tests + bằng chứng instrumentation không có DB trong hot path
- Parallelizable: no

---
artifact: TASK-PACKET.md
version: "1.0"
task_id: TASK-018
owner: implement-frontend
status: proposed
updated_at: "2026-08-20T17:25:00+07:00"
change_id: CR-003
---

# Task Packet: TASK-018 — Frontend Area Dashboard consume Realtime Metadata Riêng

- Task type: triển khai
- Scope: tính năng
- Module: web-ui
- Capability: implement-frontend
- Linked requirements: REQ-002, REQ-005, REQ-009, CR-003
- Dependencies: `TASK-016`, `TASK-017`
- Inputs: contract addendum của `TASK-016`
- Outputs:
  - kế hoạch tích hợp `Area Security Dashboard`
  - luồng state phía client được cập nhật cho metadata lane so với event lane
- Completion gate: UI area monitoring không cần polling detections/events để cập nhật metadata mỗi frame; video stream renderer vẫn là lane tách biệt.
- Verification method: Frontend integration checks + kiểm tra realtime thủ công
- Parallelizable: yes

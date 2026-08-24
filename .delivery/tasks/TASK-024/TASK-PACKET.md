---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T21:35:01+07:00"
task_id: TASK-024
packet_revision: 4
supersedes: none
depends_on: [BUG-001.md, TASK-021, TASK-022, TASK-023]
---

# TASK-024 Fix BUG-001 Zone Rule Toggle Semantics

- Task ID: TASK-024
- Task type: implementation
- Scope: feature
- Module: web-ui
- Capability: frontend-implementation
- Linked requirements: REQ-005, REQ-007, CR-004
- Dependencies: TASK-021, TASK-022, TASK-023
- Write scope: .delivery/tasks/TASK-024/
- Inputs: .delivery/tasks/TASK-024/BUG-001.md, .delivery/tasks/TASK-021/API-CONTRACT.md, .delivery/tasks/TASK-022/UI-UX-CONTRACT.md, .delivery/tasks/TASK-022/UI-SPEC.md, .delivery/tasks/TASK-022/UX-FLOW.md, .delivery/tasks/TASK-023/TASK-RESULT.md, frontend/src/pages/ZoneTagSettings.tsx, frontend/src/context/AppContext.tsx, frontend/src/services/api.ts, frontend/src/contracts/api/dataset.schema.ts.
- Expected outputs: frontend BUG-001 fix, frontend verification evidence, .delivery/tasks/TASK-024/TASK-RESULT.md.
- Completion gate: Tab Vẽ zone hiển thị nhãn custom active từ backend và dùng semantics `✓` = selected/allowed, `✕` = không chọn/không referenced; khi toggle off phải gỡ `label_key` khỏi cả `allowed_classes` và `forbidden_classes`. Fix phải xử lý cả stale data đã sync trước đó: nếu UI hiển thị `✕` thì dữ liệu backend cũng phải không còn `label_key` trong `allowed_classes` hoặc `forbidden_classes`, kể cả cần cleanup trước khi gọi xóa label. Label custom chỉ còn bị chặn xóa khi thật sự đang `✓`/referenced trong ít nhất một zone.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop before backend changes, database changes, contract changes, destructive actions, or scope expansion beyond TASK-024 frontend fix.

---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-007
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-001, TASK-006]
---

# Gói Task: TASK-007 - Core AI Engine and React Custom Hooks

- Mã task: TASK-007
- Loại task: implementation
- Phạm vi: feature
- Module: ai-vision-pipeline
- Năng lực: backend-implementation
- Yêu cầu liên kết: REQ-004, REQ-007, CR-001, CR-002
- Phụ thuộc: TASK-001, TASK-006
- Phạm vi ghi: .delivery/tasks/TASK-007/
- Đầu vào: .delivery/ARCHITECTURE.md, docs/contracts/API-FOUNDATION.md
- Đầu ra dự kiến: backend/ai/ evaluator and slicer, frontend/src/hooks/ WebSocket and sound hooks
- Điều kiện hoàn thành: Implement 8 object classes, point-in-polygon evaluation, 15s cooldown deduplication, and React hooks for WebSocket/audio alert behavior.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate for approved contract changes, DB schema changes, or edits outside AI pipeline and hook scope.

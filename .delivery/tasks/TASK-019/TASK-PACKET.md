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

# Gói Task: TASK-019 — Verification cho CR-003 Realtime Area Metadata

- Mã task: TASK-019
- Loại task: verification
- Phạm vi: feature
- Module: none
- Năng lực: feature-verification
- Yêu cầu liên kết: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Phụ thuộc: TASK-017
- Phạm vi ghi: .delivery/tasks/TASK-019/
- Đầu vào: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `.delivery/tasks/TASK-018/TASK-RESULT.md`, backend/frontend implementation under `backend/app/` and `frontend/src/`
- Đầu ra dự kiến: `.delivery/tasks/TASK-019/TEST-REPORT.md`, `.delivery/tasks/TASK-019/TASK-RESULT.md`, bug records if verification fails
- Điều kiện hoàn thành:
  - Xác minh không có DB read trong hot path mỗi frame.
  - Xác minh area metadata stream cập nhật realtime mà không phụ thuộc polling detections/events.
  - Xác minh event/alert lane vẫn đúng cho severity và notification.
- Chính sách phê duyệt: Project owner review required before promoting verification artifacts from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if verification requires repairing production code, changing approved contracts, or running unavailable external infrastructure.

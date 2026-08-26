---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: approved
updated_at: "2026-08-25T15:10:00+07:00"
task_id: TASK-026
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-026 Vẽ BBox Bám Theo Frame vào Clip Chứng cứ 10s

- Task ID: TASK-026
- Task type: implementation
- Scope: feature
- Module: event-clip-manager
- Capability: backend-implementation
- Linked requirements: REQ-008, CR-002
- Dependencies: TASK-007
- Write scope: .delivery/tasks/TASK-026/
- Inputs: .delivery/REQUIREMENTS.md (REQ-008 acceptance criteria 2), backend/app/services/event_manager.py, backend/app/services/vision_pipeline.py
- Expected outputs: backend/app/services/event_manager.py, backend/tests/test_event_clip_bbox.py
- Completion gate: Clip 10s ghi ra có khung bbox bám theo đối tượng qua từng frame và nhãn lớp tiếng Việt; clip tải về mang sẵn bbox mà không cần frontend vẽ thêm. Báo cáo thời gian sinh một clip trước và sau thay đổi để định lượng chi phí suy luận theo frame; nếu vượt ngưỡng chấp nhận được của đường ghi sự kiện thì dừng và nêu phương án (giảm tần suất suy luận hoặc sinh clip bất đồng bộ) thay vì âm thầm làm chậm hot path.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T19:37:31+07:00"
task_id: TASK-018
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Gói Task: TASK-018 — Frontend Area Dashboard consume Realtime Metadata Riêng

- Mã task: TASK-018
- Loại task: implementation
- Phạm vi: feature
- Module: web-ui
- Năng lực: frontend-implementation
- Yêu cầu liên kết: REQ-002, REQ-005, REQ-009, CR-003
- Phụ thuộc: TASK-016
- Phạm vi ghi: .delivery/tasks/TASK-018/
- Đầu vào: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/services/api.ts`, `frontend/src/services/websocket.ts`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/types/index.ts`, `frontend/src/context/AppContext.tsx`
- Đầu ra dự kiến: frontend metadata-lane integration updates under `frontend/src/`, production verification evidence, `.delivery/tasks/TASK-018/TASK-RESULT.md`
- Điều kiện hoàn thành: UI area monitoring không cần polling detections/events để cập nhật metadata mỗi frame; video stream renderer vẫn là lane tách biệt.
- Chính sách phê duyệt: Project owner review required before promoting `TASK-RESULT.md` from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if implementation requires backend changes, approved contract changes, or edits outside frontend scope plus `.delivery/tasks/TASK-018/`.

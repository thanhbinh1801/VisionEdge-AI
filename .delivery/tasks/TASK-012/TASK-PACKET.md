---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-012
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-006, TASK-008]
---

# Gói Task: TASK-012 - Zone and Tag Settings

- Mã task: TASK-012
- Loại task: implementation
- Phạm vi: feature
- Module: web-ui
- Năng lực: frontend-implementation
- Yêu cầu liên kết: REQ-005, REQ-006, REQ-007, CR-001, CR-002
- Phụ thuộc: TASK-006, TASK-008
- Phạm vi ghi: .delivery/tasks/TASK-012/
- Đầu vào: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md, frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/
- Đầu ra dự kiến: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/, and .delivery/tasks/TASK-012/TASK-RESULT.md
- Điều kiện hoàn thành: Zone & Tag Settings supports polygon editing, known/unknown vehicle labeling, dataset BBox labeling, and synchronizes zone geometry/name to Area Dashboard state.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate if implementation requires backend schema changes, approved contract changes, or edits outside Zone/Tag frontend scope plus .delivery/tasks/TASK-012/.

## Ghi chú tái dựng

This packet was restored because `.delivery/tasks/TASK-012/TASK-PACKET.md` was missing while `TASK-RESULT.md` still exists.

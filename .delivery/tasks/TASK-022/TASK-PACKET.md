---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T19:56:33+07:00"
task_id: TASK-022
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-022 Thiết kế UI/UX cho Cài đặt > Nhãn đối tượng

- Task ID: TASK-022
- Task type: feature-design
- Scope: feature
- Module: web-ui
- Capability: ui-ux-design
- Linked requirements: REQ-005, REQ-007, CR-004
- Dependencies: TASK-020
- Write scope: .delivery/tasks/TASK-022/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/tasks/TASK-020/DATABASE-DESIGN.md, frontend/src/pages/ZoneTagSettings.tsx, frontend/src/context/AppContext.tsx, frontend/src/components/zone/PolygonZoneEditor.tsx
- Expected outputs: .delivery/tasks/TASK-022/UI-UX-CONTRACT.md, .delivery/tasks/TASK-022/TASK-RESULT.md
- Completion gate: Thiết kế xong workflow UI cho import media thật, scrub frame video, tạo/sửa/xóa bbox, trạng thái nhãn hệ thống/custom, xác nhận xóa, restore, lỗi batch validation và phản hồi sync mà chưa sửa frontend production.
- Approval policy: Chủ dự án là người duyệt duy nhất.
- Escalation policy: Dừng lại khi có thay đổi phá tương thích, ảnh hưởng bảo mật, phát sinh chi phí đáng kể, migration phá hủy/khó đảo ngược, mở rộng phạm vi, hoặc tác động tới work đang in-progress/completed.

## Execution Brief

### Objective
Design the CR-004 UI/UX contract for `Cài đặt > Nhãn đối tượng`, replacing mock/local labeling flows with a real persisted object-labeling workflow in later implementation.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-022/TASK-PACKET.md`
- `.delivery/tasks/TASK-022/TASK-RESULT.md` if present
- `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md` if present
- `.delivery/REQUIREMENTS.md`
- `.delivery/DOMAIN-MODEL.md`
- `.delivery/tasks/TASK-020/DATABASE-DESIGN.md`
- `frontend/src/pages/ZoneTagSettings.tsx`
- `frontend/src/context/AppContext.tsx`
- `frontend/src/components/zone/PolygonZoneEditor.tsx`
- `.delivery/MASTER-PLAN.md` section `TASK-022 Thiết kế UI/UX cho Cài đặt > Nhãn đối tượng`

### Allowed write scope
- Historical/planned task scope: `.delivery/tasks/TASK-022/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-022/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, production frontend code, backend code, API/database contracts outside TASK-022, `.delivery/tasks/TASK-022/TASK-RESULT.md`, `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md`, bug/test-report artifacts, or unrelated delivery artifacts during packet normalization.

### Acceptance criteria
- Packet remains consistent with task id `TASK-022`, capability `ui-ux-design`, dependency `TASK-020`, linked requirements, expected outputs, and completion gate.
- UI/UX contract covers real media import, video frame scrubbing, bbox create/edit/delete, system/custom label states, confirm delete, restore, batch validation errors, and sync feedback.
- Design does not modify production frontend files.

### Edge cases / risks
- System labels must be visibly protected from edits/deletes while custom labels support soft delete/restore.
- Batch validation errors need to remain actionable without losing valid samples.
- Video frame selection and bbox editing may conflict with existing polygon zone editor interactions.
- Not specified in source artifacts: exact microcopy, keyboard shortcut set, thumbnail dimensions, canvas zoom/pan behavior, and high-fidelity visual mockups.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python D:\Skill\SKILLs\design-ui-ux\scripts\validate_ui_ux_design.py D:\Hilab\Project34 TASK-022`.
- Cross-check the contract against existing ZoneTagSettings and PolygonZoneEditor constraints.

### Escalation conditions
- Escalate for breaking compatibility, security posture changes, material cost, destructive migration implications, scope expansion, or impact to in-progress/completed work.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- UI/UX design summary.
- Validation evidence.
- Explicit note that production frontend was not changed.
- Open risks/Not specified items.
- Blockers and scope-change requests.

### Skill/capability to run
- `ui-ux-design`.

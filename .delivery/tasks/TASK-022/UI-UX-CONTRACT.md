---
artifact: UI-UX-CONTRACT.md
version: "1.0"
owner: design-ui-ux
status: in-review
updated_at: "2026-08-24T20:14:24+07:00"
task_id: TASK-022
depends_on: [UI-SPEC.md, UX-FLOW.md, TASK-PACKET.md]
---

# TASK-022 Hợp đồng UI/UX

Artifact tổng hợp này đáp ứng expected output trong packet/master-plan: `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md`.

Nguồn canonical cho implementation:

- `UI-SPEC.md`: inventory màn hình/component, ranh giới component, states, responsive rules, validation và accessibility.
- `UX-FLOW.md`: actors, entry points, happy path, alternative paths, failure/recovery và completion states.

Guardrails cho implementation:

- TASK-024 không được giữ mock/local-only state cho media sources, labels hoặc BBox samples.
- TASK-024 phải consume API contract đã duyệt của TASK-021 khi artifact đó có.
- TASK-024 phải giữ đúng semantics từ TASK-020: khóa nhãn hệ thống và soft delete/restore nhãn custom.
- Tạo mới/restore nhãn custom phải hiển thị zone sync feedback và tác động zone rule mặc định `cấm`.
- Batch save samples phải được thể hiện trong UI như một thao tác atomic.

Các mục còn mở được ghi trong `UI-SPEC.md` và `UX-FLOW.md`; không có blocker cho thiết kế UI/UX vì các điểm đó thuộc phần chốt API của TASK-021 hoặc chi tiết implementation của TASK-024.

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

# TASK-024 Triển khai Frontend Cài đặt > Nhãn đối tượng & Fix BUG-001 Zone Rule Toggle Semantics

- Task ID: TASK-024
- Task type: implementation
- Scope: feature
- Module: web-ui
- Capability: frontend-implementation
- Linked requirements: REQ-005, REQ-007, CR-004
- Dependencies: TASK-021, TASK-022, TASK-023
- Write scope: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/context/AppContext.tsx, frontend/src/services/api.ts, frontend/src/types/, frontend/src/components/zone/, .delivery/tasks/TASK-024/
- Inputs: .delivery/tasks/TASK-024/BUG-001.md, .delivery/tasks/TASK-021/API-CONTRACT.md, .delivery/tasks/TASK-022/UI-UX-CONTRACT.md, .delivery/tasks/TASK-022/UI-SPEC.md, .delivery/tasks/TASK-022/UX-FLOW.md, .delivery/tasks/TASK-023/TASK-RESULT.md, frontend/src/pages/ZoneTagSettings.tsx, frontend/src/context/AppContext.tsx, frontend/src/services/api.ts, frontend/src/contracts/api/dataset.schema.ts
- Expected outputs: Chỉnh sửa frontend object-labeling integration, sửa lỗi BUG-001, bằng chứng xác minh frontend/build, .delivery/tasks/TASK-024/TASK-RESULT.md
- Completion gate: UI `Cài đặt > Nhãn đối tượng` tích hợp đầy đủ API thật cho media sources, custom labels và bbox samples; dữ liệu persisted khi reload; tab Vẽ zone hiển thị đúng nhãn custom active từ backend với semantics `✓` = selected/allowed, `✕` = không chọn/không referenced; khi toggle off phải gỡ `label_key` khỏi cả `allowed_classes` và `forbidden_classes`; xử lý triệt để stale data đã sync trước đó và chỉ chặn xóa nhãn custom khi thực sự đang referenced trong zone.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại trước khi sửa backend, thay đổi database, thay đổi hợp đồng API, thực hiện thao tác phá hủy dữ liệu, hoặc mở rộng phạm vi ngoài sửa đổi frontend TASK-024.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Triển khai tích hợp frontend cho tính năng Object Labeling (CR-004) tại trang `Cài đặt > Nhãn đối tượng` theo hợp đồng API (TASK-021), UI/UX contract (TASK-022) và backend (TASK-023). Đồng thời xử lý triệt để BUG-001 liên quan tới ngữ nghĩa toggle zone rule custom label: đảm bảo khi bỏ chọn label custom trong zone (`✕`), `label_key` phải được gỡ bỏ khỏi cả `allowed_classes` và `forbidden_classes` trên backend, giải phóng hoàn toàn liên kết để có thể xóa custom label mà không bị chặn nhầm.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-024/TASK-PACKET.md`
- `.delivery/tasks/TASK-024/BUG-001.md`
- `.delivery/tasks/TASK-024/TASK-RESULT.md` (nếu có)
- `.delivery/tasks/TASK-021/API-CONTRACT.md`
- `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md`
- `.delivery/tasks/TASK-022/UI-SPEC.md`
- `.delivery/tasks/TASK-022/UX-FLOW.md`
- `.delivery/tasks/TASK-023/TASK-RESULT.md`
- `frontend/src/pages/ZoneTagSettings.tsx`
- `frontend/src/context/AppContext.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/contracts/api/dataset.schema.ts`
- Phần `TASK-024 Frontend Cài đặt > Nhãn đối tượng theo Design đã Duyệt` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- Code frontend: `frontend/src/pages/ZoneTagSettings.tsx`, `frontend/src/context/AppContext.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/`, `frontend/src/components/zone/`.
- Phạm vi task lịch sử/kế hoạch: `.delivery/tasks/TASK-024/`.

### Phạm vi cấm (Forbidden scope)
- Không sửa code backend (`backend/`), không thay đổi database schema, không sửa hợp đồng API toàn cục (`.delivery/API-CONTRACT.md`), không sửa MASTER-PLAN.md hay các task artifact khác ngoài phạm vi TASK-024.

### Tiêu chí nghiệm thu (Acceptance criteria)
- UI `Nhãn đối tượng` chuyển từ dữ liệu mock/local state sang gọi API thật cho media import, danh sách nhãn, tạo/sửa/xóa nhãn custom, lưu/sửa/xóa bbox samples.
- Reload trang giữ nguyên dữ liệu đã lưu (persisted data).
- Xử lý các hộp thoại xác nhận xóa (confirm delete dialog), khôi phục nhãn soft-deleted (restore), kiểm tra lỗi batch validation và hiển thị lỗi rõ ràng.
- Đã khắc phục BUG-001: Trong tab Vẽ zone, nhãn custom hiển thị đúng trạng thái `✓` (selected) hoặc `✕` (unselected). Khi chuyển sang `✕`, `label_key` bị gỡ khỏi cả hai mảng class của zone. Xóa nhãn custom chỉ bị chặn khi nhãn thực sự đang ở trạng thái `✓` trong ít nhất 1 zone.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- **Stale data cleanup**: Dữ liệu cũ đã sync trước đó có thể chứa `label_key` trong `forbidden_classes` dù UI hiển thị không chọn (`✕`). Frontend/workflow phải tự động dọn dẹp (cleanup) các stale reference này trước hoặc trong quá trình toggle/xóa nhãn.
- **Xử lý bất đồng bộ (Async state)**: Quá trình sync zone rules hoặc xóa nhãn cần loading state phù hợp trên UI để tránh thao tác đúp (double submit).

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh kiểm tra build frontend: `npm --prefix frontend run build`.
- Kiểm tra thủ công luồng giao diện: Tải ảnh/video, tạo custom label, gán/bỏ gán trong zone rule, kiểm tra toggle `✓`/`✕` và thực hiện xóa custom label thành công khi không còn referenced.

### Điều kiện leo thang (Escalation conditions)
- Dừng lại và báo cáo nếu cần thay đổi API contract backend, sửa database schema, hoặc phát sinh thay đổi phạm vi lớn ngoài frontend task TASK-024.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Trạng thái / Kết quả (Status/outcome).
- Đầu vào đã dùng (Inputs used).
- Đầu ra đã tạo (Outputs created).
- Tóm tắt thay đổi Frontend & Fix BUG-001 (Frontend implementation & BUG-001 fix summary).
- Bằng chứng xác minh (Validation evidence - npm build output, manual test notes).
- Các tệp tin đã thay đổi (Changed files).
- Điểm chặn và yêu cầu thay đổi phạm vi (Blockers and scope-change requests).

### Skill/capability cần chạy (Skill/capability to run)
- `frontend-implementation`.

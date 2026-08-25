---
artifact: TASK-RESULT.md
version: "1.2"
owner: implement-frontend
status: approved
updated_at: "2026-08-24T21:45:22+07:00"
task_id: TASK-024
depends_on: [TASK-PACKET.md, BUG-001.md]
---

# TASK-024 Kết quả fix BUG-001

- Task ID: TASK-024
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-024/BUG-001.md`, `.delivery/tasks/TASK-024/TASK-PACKET.md`, `.delivery/tasks/TASK-021/API-CONTRACT.md`, `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md`, `.delivery/tasks/TASK-022/UI-SPEC.md`, `.delivery/tasks/TASK-022/UX-FLOW.md`, `frontend/src/pages/ZoneTagSettings.tsx`, `frontend/src/services/api.ts`, `frontend/src/contracts/api/dataset.schema.ts`.
- Outputs produced: cập nhật `frontend/src/context/AppContext.tsx`; cập nhật `frontend/src/pages/ZoneTagSettings.tsx`; cập nhật `frontend/src/components/zone/ObjectLabelingTab.tsx`; cập nhật `.delivery/tasks/TASK-024/TASK-RESULT.md`.
- Validation evidence: `npm --prefix frontend run lint` pass; `npx --prefix frontend tsc -p frontend/tsconfig.json --noEmit` pass; `npm --prefix frontend run build` pass ngoài sandbox do Vite/esbuild bị `spawn EPERM` trong sandbox; `python D:\Skill\SKILLs\implement-frontend\scripts\validate_frontend_implementation.py D:\Hilab\Project34 TASK-024` pass.
- Changed files: `frontend/src/context/AppContext.tsx`; `frontend/src/pages/ZoneTagSettings.tsx`; `frontend/src/components/zone/ObjectLabelingTab.tsx`; `.delivery/tasks/TASK-024/TASK-RESULT.md`.
- Tests changed: Không thêm test file mới vì frontend hiện chưa có test runner/component test seam riêng; dùng TypeScript compiler check, lint script và production build làm bằng chứng.
- Commands run: `npm --prefix frontend run lint`; `npx --prefix frontend tsc -p frontend/tsconfig.json --noEmit`; `npm --prefix frontend run build`; `npm --prefix frontend run build` ngoài sandbox; `python D:\Skill\SKILLs\implement-frontend\scripts\validate_frontend_implementation.py D:\Hilab\Project34 TASK-024`.
- Deviations: Không sửa backend, database hoặc contract upstream. Không dùng `objLabels` mock/local cho rule buttons của tab `Vẽ zone`; tab này hiện tải nhãn active từ backend qua `fetchDatasetLabels(false)`.
- Blockers: none
- Scope change requests: none

## Changed files

- `frontend/src/context/AppContext.tsx`: thêm `refreshZones()` để các màn frontend có thể reload zone rules từ backend sau khi cleanup stale data.
- `frontend/src/pages/ZoneTagSettings.tsx`: khi mở tab `Vẽ zone`, tải nhãn active từ backend, cleanup các custom `label_key` đang nằm trong `forbidden_classes` nhưng không nằm trong `allowed_classes`, gọi API update zone, rồi reload lại zone từ backend; toggle `✕` tiếp tục gỡ key khỏi cả hai mảng.
- `frontend/src/components/zone/ObjectLabelingTab.tsx`: trước khi xóa nhãn custom, tải zone từ backend, chặn xóa nếu label còn thật sự `✓` trong `allowed_classes`, cleanup key khỏi `forbidden_classes` khi label đang `✕`, reload dữ liệu backend rồi mới gọi delete; sau khi xóa vẫn ở chế độ không hiện nhãn đã xóa; sau khi khôi phục cũng quay về chế độ không hiện nhãn đã xóa; đổi checkbox thành `Hiện nhãn đã xóa`, bật checkbox thì chỉ hiển thị nhãn đã xóa; đưa `Sửa`/`Xóa` xuống dưới dòng `Custom` và `x mẫu` để cột `Khóa`/`Custom` cùng hàng dọc.
- `.delivery/tasks/TASK-024/TASK-RESULT.md`: ghi kết quả fix và bằng chứng kiểm thử.

## Verification details

- `npm --prefix frontend run lint`
  - Exit code: 0
  - Output chính: `tsc --noEmit`.
- `npx --prefix frontend tsc -p frontend/tsconfig.json --noEmit`
  - Exit code: 0.
- `npm --prefix frontend run build`
  - Exit code: 1 trong sandbox.
  - Lỗi môi trường: `Error: spawn EPERM` khi Vite/esbuild spawn process.
- `npm --prefix frontend run build` ngoài sandbox
  - Exit code: 0.
  - Output chính: `41 modules transformed`, `built in 1.25s`.
- `python D:\Skill\SKILLs\implement-frontend\scripts\validate_frontend_implementation.py D:\Hilab\Project34 TASK-024`
  - Exit code: 0.
  - Output chính: `OK: validated frontend implementation task TASK-024`.

## Functional evidence

- Tab `Vẽ zone` không còn render rule labels bằng `objLabels.map(...)`.
- Tab `Vẽ zone` hiển thị loading/error/empty states cho danh sách nhãn từ backend.
- Nút rule dùng `label.label_name` để hiển thị và `label.label_key` để cập nhật zone rules.
- `✕` trong tab `Vẽ zone` hiện là không chọn/không referenced: toggle off xóa key khỏi cả `allowed_classes` và `forbidden_classes`.
- Dữ liệu stale đã sync trước đó được xử lý: khi mở tab `Vẽ zone`, custom label đang hiển thị `✕` sẽ bị gỡ khỏi `forbidden_classes` bằng API update zone và zones được reload lại từ backend.
- Trước khi xóa nhãn custom, frontend cleanup `forbidden_classes` rồi reload backend; chỉ chặn xóa khi label vẫn còn trong `allowed_classes` của ít nhất một zone.
- Row nhãn custom trong tab `Nhãn đối tượng` hiển thị `Sửa` và `Xóa` ở cuối dòng chính, cùng hàng với `Custom` và `x mẫu`.
- Khi bật `Hiện nhãn đã xóa`, danh sách chỉ hiển thị nhãn đã xóa; nếu chưa có nhãn đã xóa thì danh sách không render thêm nhãn nào.
- Sau khi xóa nhãn custom, checkbox `Hiện nhãn đã xóa` vẫn tắt và danh sách ở trang nhãn active.
- Sau khi khôi phục nhãn custom, checkbox `Hiện nhãn đã xóa` được tắt và UI quay về trang nhãn active.
- Nút `Sửa` và `Xóa` nằm dưới dòng metadata `Custom`/`x mẫu`; nhãn trạng thái `Khóa`, `Custom`, `Đã xóa` và số mẫu nằm trong cùng cột dọc để dễ scan.

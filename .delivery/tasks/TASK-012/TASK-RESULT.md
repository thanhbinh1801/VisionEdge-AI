---
artifact: TASK-RESULT.md
version: 1.3.0
task_id: TASK-012
owner: implement-frontend
status: blocked
updated_at: "2026-08-20T17:04:12+07:00"
---

# Kết quả Task: TASK-012 — Đồng bộ Zone Editor sang Area Dashboard

- Mã task: TASK-012
- Kết quả: blocked
- Đầu vào đã dùng: TASK-012 packet/diagnosis và approved inputs đọc từ `HEAD`; backend frame/pipeline và frontend TASK-010/TASK-012 hiện tại.
- Đầu ra đã tạo: Area Dashboard hiển thị tức thì geometry/name của zone vừa chỉnh từ shared state; MJPEG hỗ trợ tắt backend zone rendering để tránh polygon trùng; backend tiếp tục là bbox renderer duy nhất.
- Bằng chứng xác minh: Backend compile và scoped Ruff pass; toàn bộ backend 31 passed; frontend lint và TypeScript pass; production Vite build pass với 38 modules transformed; scoped diff check pass.
- Changed files: `backend/app/api/v1/events.py`, `frontend/src/services/api.ts`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `.delivery/tasks/TASK-012/TASK-RESULT.md`.
- Tests changed: Không thêm frontend test vì repo không có test runner; full backend regression suite và strict frontend compiler/build được dùng làm verification.
- Commands run: `python -m compileall -q backend` (exit 0); `python -m ruff check --select F,I backend/app/api/v1/events.py` (exit 0); `python -m pytest backend/tests -q` (31 passed, exit 0); `npm run lint` (exit 0); `npx tsc --noEmit` (exit 0); `npm run build` ngoài sandbox (exit 0, 38 modules transformed); scoped `git diff --check` (exit 0).
- Sai lệch: Không thay đổi response body contract. `/events/video-feed` chỉ nhận thêm optional `draw_zones` mặc định `true`, nên client cũ giữ nguyên hành vi.
- Điểm chặn: Formal skill validation remains blocked because `.delivery/tasks/TASK-012/TASK-PACKET.md` and approved upstream `.delivery` artifacts were already deleted in the working tree; owner: project owner/user must restore or approve restoring those artifacts before validator rerun. Implementation and all executable checks pass.
- Yêu cầu đổi phạm vi: none

## Implementation summary

- Area Dashboard tiếp tục nhận annotated MJPEG có bbox/detection từ backend nhưng yêu cầu `draw_zones=false`.
- Polygon và label zone được vẽ từ `zonesByCam`, cùng state mà Zone Editor cập nhật, nên chuyển tab không cần refetch/reload để thấy thay đổi.
- Tọa độ vẫn là phần trăm trong viewBox `0 0 100 100`; geometry không phụ thuộc kích thước viewport.
- Không khôi phục React bbox overlay; trách nhiệm bbox vẫn chỉ nằm ở backend.

## Verification notes

Production bundle hoàn tất thành công; JavaScript 216.33 kB, gzip 64.46 kB. Sáu backend warnings là deprecation từ PyTorch/Ultralytics.

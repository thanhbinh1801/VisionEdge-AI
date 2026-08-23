---
artifact: TASK-RESULT.md
version: 1.4.0
task_id: TASK-010
owner: implement-frontend
status: blocked
updated_at: "2026-08-20T16:39:42+07:00"
---

# Kết quả Task: TASK-010 — Đồng bộ Area Security Dashboard với annotated MJPEG

- Mã task: TASK-010
- Kết quả: blocked
- Đầu vào đã dùng: `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-010/TASK-PACKET.md`, `.delivery/tasks/TASK-010/BUG-DIAGNOSIS.md`, approved API/UI foundation từ `HEAD`, `docs/contracts/api/api-schema.json`, và kết quả backend TASK-010 version 1.3.0.
- Đầu ra đã tạo: Area Security Dashboard dùng annotated MJPEG làm renderer duy nhất; loading/stream error/AI degraded states; strict dashboard API error propagation; production frontend bundle.
- Bằng chứng xác minh: `npm run lint` pass; `npx tsc --noEmit` pass; `npm run build` pass ngoài sandbox với 38 modules transformed; `git diff --check` pass cho frontend scope.
- Changed files: `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/services/api.ts`, `.delivery/tasks/TASK-010/TASK-RESULT.md`.
- Tests changed: Không thêm test file vì `frontend/package.json` không có test runner; regression được kiểm bằng strict TypeScript, lint script và production Vite build.
- Commands run: `npm run lint` (exit 0); `npx tsc --noEmit` (exit 0); `npm run build` trong sandbox (exit 1, `spawn EPERM`); `npm run build` ngoài sandbox (exit 0, 38 modules transformed); `git diff --check -- frontend/src/pages/AreaSecurityDashboard.tsx frontend/src/services/api.ts .delivery/tasks/TASK-010/TASK-RESULT.md` (exit 0).
- Sai lệch: Không sửa backend, API body contract, Master Plan, requirements, architecture hoặc database. Custom frame identity headers được đọc như optional metadata; bbox/violation chỉ được backend render trên annotated MJPEG.
- Điểm chặn: Formal skill validation remains blocked because `.delivery/tasks/TASK-010/TASK-PACKET.md` and approved upstream `.delivery` artifacts were already deleted in the working tree; owner: project owner/user must restore or approve restoring those artifacts before validator rerun. Frontend implementation, lint, typecheck and production build all pass.
- Yêu cầu đổi phạm vi: none

## Implementation summary

- Giữ `<img>` cho endpoint MJPEG; không đổi sang `<video>`.
- Xóa React bbox overlay và SVG annotation overlay khỏi viewport để backend là nơi duy nhất vẽ frame annotations.
- Polling live detections chỉ cập nhật KPI và trạng thái AI, không vẽ lớp hình ảnh độc lập.
- API lỗi không còn bị chuyển thành mảng rỗng tại luồng Area Dashboard; UI giữ dữ liệu cuối cùng và hiển thị trạng thái degraded/error riêng.
- Thêm trạng thái chờ frame đầu tiên, stream error, reconnect, AI degraded, zone degraded và event error với ARIA live/alert.

## Verification notes

Production build ban đầu không thể spawn `esbuild` trong sandbox Windows (`EPERM`). Cùng lệnh chạy ngoài sandbox thành công; đây là hạn chế sandbox, không phải lỗi source hoặc bundle.

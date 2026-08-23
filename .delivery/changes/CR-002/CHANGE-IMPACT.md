---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: in-review
updated_at: "2026-08-19T11:02:43+07:00"
change_id: CR-002
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, MASTER-PLAN.md]
---

# Đánh giá Ảnh hưởng Thay đổi (Change Impact Assessment) cho CR-002

## Tóm tắt thay đổi
- Business delta: Chuyển đổi giao diện người dùng từ HTML5/Vanilla JS sang React Framework hiện đại (Vite + React / Next.js, Tailwind CSS, Lucide React icons, Recharts cho đồ thị KPI, SVG Canvas cho Zone Editor) kết hợp React State & Hooks quản lý luồng dữ liệu thời gian thực. Cập nhật mô hình AI Vision mặc định sang YOLOv26.
- Affected requirements: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`, `REQ-006`, `REQ-007`, `REQ-008`, `REQ-009`

## Tác động trực tiếp
Các task chịu tác động trực tiếp từ thay đổi stack Web UI sang React và YOLOv26:
- `TASK-001` (Nâng cấp mô hình phát hiện đối tượng AI Pipeline sang Ultralytics YOLOv26)
- `TASK-002` (Thiết kế lại hợp đồng API & WebSocket event payload cho React Client Hooks)
- `TASK-003` (Cấu trúc lại giao diện UI Foundation với React SPA, Tailwind CSS và Lucide Icons)
- `TASK-004` (Xây dựng Shared Components: Header, Sidebar, AudioBeepPlayer, VideoModal 10s)
- `TASK-005` (Phát triển SVG Canvas Component cho Polygon Zone Editor)
- `TASK-006` (Cập nhật Schema CSDL & API endpoints đồng bộ nhãn YOLOv26)
- `TASK-007` (Xây dựng Custom Hooks cho WebSockets `useWebSocket` & Audio Alerts)
- `TASK-008` (Triển khai Trang Tab 1: Gate Dashboard LPR với Recharts visualizers)
- `TASK-009` (Triển khai Trang Tab 2: Area Security Dashboard với Recharts visualizers)
- `TASK-010` (Triển khai Trang Tab 3: Zone & Tag Settings với SVG Canvas)
- `TASK-012` (Triển khai Trang Tab 4: AI Chatbot Assistant với VideoModal 10s)
- `TASK-013` (Tích hợp WebSocket Realtime Events với React Context & AudioBeepPlayer)
- `TASK-014` (Kiểm thử toàn diện E2E & Kiểm thử hồi quy cho hệ thống React UI + YOLOv26)

## Tác động task bắc cầu
- `TASK-001` — module `ai-vision-pipeline` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-002` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-003` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-004` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-005` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-006` — module `database-storage` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-007` — module `shared-engine-utils` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-008` — module `web-ui` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-009` — module `lpr-gate-module` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-010` — module `area-monitoring-module` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-012` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-013` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-014` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`

## Bằng chứng không ảnh hưởng
- Các thành phần Backend không liên quan đến giao diện như Video Stream Capture loop (`video-stream-service`) và SQLite storage engine nền tảng duy trì nguyên vẹn giao thức hoạt động baseline.

## Khóa chọn lọc
- Khóa chọn lọc các module bị ảnh hưởng: `web-ui`, `ai-vision-pipeline`, `lpr-gate-module`, `area-monitoring-module` và các tài liệu hợp đồng giao tiếp liên quan để cập nhật sang React & YOLOv26.

## Hành động packet
- Tự động vô hiệu hóa (invalidate-automatically) các gói task (task packets) ở trạng thái `planned` hoặc `ready` thuộc danh sách các task bị tác động trực tiếp để tái khởi tạo theo hợp đồng React UI mới.

## Quyết định cần owner xác nhận
- Phê duyệt phạm vi thay đổi CR-002 và xác nhận hủy/lập lại kế hoạch giao hàng cho các task bị ảnh hưởng.

## Thứ tự cập nhật
1. Cập nhật Yêu cầu sản phẩm `.delivery/REQUIREMENTS.md` (Đã hoàn thành CR-002)
2. Cập nhật Kiến trúc kỹ thuật `.delivery/ARCHITECTURE.md` (Đã hoàn thành stack React & YOLOv26)
3. Cập nhật kế hoạch giao hàng tổng thể `.delivery/MASTER-PLAN.md`
4. Khởi tạo lại các gói task packet phát triển React UI (`frontend/src/`) và kiểm thử nghiệm thu.

## Kế hoạch xác minh
- Chạy công cụ kiểm tra hợp đồng tài liệu `validate_artifacts.py`.
- Trình tài liệu `CHANGE-IMPACT.md` tới Project Owner để phê duyệt chính thức.

---
artifact: TASK-RESULT.md
version: "1.1"
task_id: TASK-027
owner: implement-backend
status: approved
updated_at: "2026-08-24T23:34:00+07:00"
depends_on: [TASK-PACKET.md, API-CONTRACT.md, BUG-001.md]
---

# Kết quả Thực hiện Task: TASK-027 — Sửa Lỗi BUG-001 Telegram Evidence Notification & Múi giờ Hiển thị

- Task ID: TASK-027
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-027/TASK-PACKET.md`, `.delivery/tasks/TASK-027/BUG-001.md`, `.delivery/tasks/TASK-026/API-CONTRACT.md`, `.env`, `backend/app/core/config.py`, `backend/app/services/alert_dispatcher.py`, `backend/app/api/v1/events.py`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `backend/tests/test_alerts.py`.
- Outputs produced: `.delivery/tasks/TASK-027/TASK-RESULT.md`, `backend/app/core/config.py`, `backend/app/services/alert_dispatcher.py`, `backend/app/api/v1/events.py`, `backend/tests/test_alerts.py`, `.env`.
- Changed files: `backend/app/core/config.py`, `backend/app/services/alert_dispatcher.py`, `backend/app/api/v1/events.py`, `.env`.
- Tests changed: `backend/tests/test_alerts.py`.
- Commands run: `.\venv\Scripts\python.exe -m pytest backend/tests/test_alerts.py -v`, `npx tsc --noEmit`.
- Validation evidence: Thực thi bộ kiểm thử backend `pytest backend/tests/test_alerts.py -v` đạt 6/6 tests passed (exit code 0); kiểm tra kiểu dữ liệu frontend `npx tsc --noEmit` đạt exit code 0.
- Deviations: none
- Blockers: none
- Scope change requests: none

## Tóm tắt Công việc Thực hiện (Implementation Details)

1. **Khắc phục Lỗi Tìm Tệp Video Clip Chứng cứ 10s MP4**:
   - Thêm biến cấu hình môi trường `CLIPS_DIR=backend/data/clips` vào tệp `.env`.
   - Cập nhật validator `normalize_paths` trong `backend/app/core/config.py` để tự động phân giải `CLIPS_DIR` thành đường dẫn tuyệt đối chuẩn hóa dựa trên `PROJECT_ROOT` (`PROJECT_ROOT / "backend" / "data" / "clips"`).
   - Cập nhật `resolve_clip_filepath` trong `backend/app/services/alert_dispatcher.py` để kiểm tra cả đường dẫn tuyệt đối cấu hình và các đường dẫn fallback, đảm bảo tìm thấy tệp MP4 bất kể tiến trình Python được khởi chạy từ thư mục nào.

2. **Khắc phục Lỗi Múi giờ Thông báo Telegram (`format_telegram_message`)**:
   - Cập nhật `format_telegram_message` trong `AlertDispatcher`: parse mọi dạng `captured_at` (chuỗi ISO UTC hoặc naive datetime) sang timezone Việt Nam `Asia/Ho_Chi_Minh` (ICT +07:00).
   - Định dạng mốc thời gian vi phạm chuẩn xác hiển thị trên tin nhắn Telegram dạng `YYYY-MM-DD HH:MM:SS (+07:00)`.

3. **Chuẩn hóa Múi giờ REST API Response (`events.py`)**:
   - Cập nhật `_event_response_from_model` trong `backend/app/api/v1/events.py`: tự động gắn múi giờ ISO 8601 offset (`+00:00` hoặc ISO offset) cho trường `timestamp` trước khi trả về REST API.
   - Giúp trình duyệt tại `AreaSecurityDashboard.tsx` chuyển đổi và hiển thị đúng mốc giờ local Việt Nam trên Nhật ký sự kiện Web UI.

## Bằng chứng Xác minh (Verification Evidence)

- **Backend Pytest**: `.\venv\Scripts\python.exe -m pytest backend/tests/test_alerts.py -v` -> 6 passed (exit code 0).
- **Frontend Typecheck**: `npx tsc --noEmit` (tại thư mục `frontend/`) -> 0 errors (exit code 0).

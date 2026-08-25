---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T22:47:05+07:00"
task_id: TASK-027
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-027 Backend Telegram Evidence Notification cho Vi phạm Khu vực

- Task ID: TASK-027
- Task type: implementation
- Scope: feature
- Module: alert-dispatcher
- Capability: backend-implementation
- Linked requirements: REQ-002, REQ-003, REQ-004, REQ-009, CR-005
- Dependencies: TASK-017, TASK-026
- Write scope: .delivery/tasks/TASK-027/
- Inputs: .delivery/tasks/TASK-026/API-CONTRACT.md, backend/app/services/event_manager.py, backend/app/services/alert_dispatcher.py, backend/app/services/vision_pipeline.py, backend/app/api/v1/websocket.py
- Expected outputs: backend alert/event implementation updates, backend tests, .delivery/tasks/TASK-027/TASK-RESULT.md
- Completion gate: Khi đối tượng thuộc danh sách cấm đi vào zone khu vực, backend chỉ gửi 1 Telegram cho event đầu tiên đã qua dedup/cooldown, gửi trực tiếp file video clip chứng cứ 10s kèm thời gian vi phạm đúng, camera, zone, loại đối tượng và lý do vi phạm; nếu Telegram lỗi thì event/clip vẫn lưu, UI vẫn cảnh báo và lỗi được ghi nhận.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, thực hiện migration phá hủy dữ liệu, mở rộng phạm vi hoặc ảnh hưởng tới công việc đang triển khai/đã hoàn thành.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Triển khai backend Telegram evidence notification cho tính năng vi phạm an ninh khu vực của CR-005: khi đối tượng thuộc danh sách cấm đi vào zone khu vực, backend chỉ gửi 1 thông báo Telegram cho event đầu tiên đã qua bộ lọc khử trùng lặp (cooldown/deduplication), đính kèm trực tiếp file video clip chứng cứ 10s MP4 cùng tin nhắn HTML chứa đầy đủ 5 trường thông tin chuẩn (thời gian vi phạm đúng từ frame, camera, zone, loại đối tượng, lý do vi phạm). Nếu Telegram API gặp sự cố (sai bot token, chat_id không tồn tại, rate limit, timeout), backend phải ghi nhận trạng thái `telegram_status: "failed"` và mã lỗi tương ứng mà không làm thất bại việc lưu trữ sự kiện/clip hay phát cảnh báo WebSocket tới UI.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-027/TASK-PACKET.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/DOMAIN-MODEL.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/changes/CR-005/CHANGE-IMPACT.md`
- `.delivery/tasks/TASK-026/API-CONTRACT.md`
- `.delivery/tasks/TASK-026/TASK-RESULT.md`
- `.delivery/tasks/TASK-017/TASK-RESULT.md`
- `backend/app/services/event_manager.py`
- `backend/app/services/alert_dispatcher.py`
- `backend/app/services/vision_pipeline.py`
- `backend/app/api/v1/websocket.py`
- `backend/app/api/v1/events.py`
- `backend/database/models.py`
- `backend/database/repository.py`
- `backend/tests/test_alerts.py`
- `backend/tests/test_live_detections_event.py`
- Phần `TASK-027 Backend Telegram Evidence Notification cho Vi phạm Khu vực` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- `backend/app/services/`
- `backend/app/api/v1/`
- `backend/database/`
- `backend/tests/`
- `.delivery/tasks/TASK-027/`

### Phạm vi cấm (Forbidden scope)
- Không chỉnh sửa `.delivery/MASTER-PLAN.md`, `.delivery/REQUIREMENTS.md`, `.delivery/DOMAIN-MODEL.md`, `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-026/`, frontend production code, hoặc các artifact của task khác.
- Không tự ý thay đổi API contract hay WebSocket event contract đã duyệt tại `.delivery/tasks/TASK-026/API-CONTRACT.md`.
- Không gửi tin nhắn Telegram trùng lặp khi vi phạm tiếp diễn trong cùng cửa sổ cooldown.
- Không để sự cố kết nối/gửi Telegram làm gián đoạn luồng lưu event, cắt clip chứng cứ, hoặc phát cảnh báo WebSocket về Web UI.

### Tiêu chí nghiệm thu (Acceptance criteria)
- Tích hợp thành công Telegram Dispatcher trong backend dịch vụ alert/event để gửi thông báo khi phát sinh sự kiện vi phạm khu vực (`ZONE_VIOLATION_EVENT`).
- Đính kèm trực tiếp file video clip chứng cứ 10s MP4 (hoặc clip clamp hợp lệ theo nguồn video) bằng phương thức `sendVideo` của Telegram Bot API.
- Tin nhắn Telegram format HTML gồm đầy đủ 5 thông tin: Mốc thời gian vi phạm (`captured_at`), Camera (`camera_name` / `camera_id`), Zone (`zone_name` / `zone_id`), Loại đối tượng (`object_type_name` / `object_type`), Lý do vi phạm (`violation_reason`).
- Đảm bảo tính nhất quán giữa thời gian vi phạm hiển thị trên Telegram với mốc thời gian vi phạm thực tế từ frame snapshot/video source.
- Cơ chế Cooldown/Deduplication hoạt động chính xác: chỉ 1 tin nhắn Telegram được gửi cho đợt vi phạm đầu tiên; các frame vi phạm liên tục tiếp theo trong cửa sổ cooldown không phát tin nhắn Telegram mới.
- Xử lý lỗi Telegram cô lập (Non-blocking): khi gửi Telegram thất bại (ví dụ: bot token sai, network timeout, rate limit), `telegram_status` được cập nhật thành `failed` cùng `telegram_error` tương ứng; event vi phạm vẫn được lưu DB, clip MP4 vẫn được trích xuất, và WebSocket vẫn phát alert level 3 về UI.
- Viết đầy đủ unit tests và integration tests kiểm thử luồng Telegram alert dispatcher, trích xuất clip, cooldown deduplication và xử lý lỗi Telegram.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- **Mốc thời gian vi phạm**: Phải sử dụng mốc thời gian thực tế `captured_at` của frame phát hiện vi phạm, không dùng thời gian hệ thống tại thời điểm gọi Telegram API.
- **Telegram Bot Token / Chat ID chưa được cấu hình hoặc bị sai**: Backend phải log lỗi rõ ràng, set `telegram_status = "skipped"` hoặc `"failed"` với `telegram_error = "BOT_TOKEN_INVALID"` hoặc `"CHAT_ID_NOT_FOUND"`, không throw unhandled exception.
- **Mạng chập chờn / Telegram API Timeout / Rate Limit**: Bắt lỗi HTTP timeout / HTTP 429 từ Telegram API, cập nhật `telegram_status = "failed"` và `telegram_error = "RATE_LIMITED"` / `"TELEGRAM_API_TIMEOUT"`.
- **Clip MP4 đang được trích xuất async**: Đảm bảo file video clip 10s đã hoàn tất ghi ra đĩa hoặc chờ sẵn trước khi gọi `sendVideo` của Telegram Bot API.
- **Dung lượng clip vượt giới hạn**: Trường hợp clip lớn hơn 50MB (giới hạn Telegram), backend phải fallback sang gửi snapshot JPG kèm link clip hoặc đính kèm clip nén hợp lệ, ghi mã lỗi `PAYLOAD_TOO_LARGE` nếu không gửi được.

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh kiểm tra theo MASTER-PLAN: `python -m pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py -q`.
- Kiểm tra linting và syntax backend: `ruff check backend/app/services/alert_dispatcher.py backend/app/services/event_manager.py backend/tests/test_alerts.py`.
- Chạy script kiểm tra backend implementation task: `python D:\Skill\SKILLs\implement-backend\scripts\validate_backend_implementation.py D:\Hilab\Project34 TASK-027`.

### Điều kiện leo thang (Escalation conditions)
- Dừng lại và báo cáo trong `TASK-RESULT.md` nếu phát hiện mâu thuẫn với `TASK-026/API-CONTRACT.md`, cần sửa đổi DB schema toàn cục mà chưa có ADR, cần thay đổi frontend, hoặc làm vỡ tương thích với các API/WebSocket hiện hữu.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Task ID: TASK-027
- Outcome: completed | blocked
- Inputs used: Danh sách các tệp/artifact đã đọc.
- Outputs produced: Danh sách các tệp backend/test đã tạo hoặc cập nhật, cùng tệp `.delivery/tasks/TASK-027/TASK-RESULT.md`.
- Validation evidence: Lệnh kiểm tra đã chạy và kết quả thực thi (exit code 0, số test passed).
- Deviations: none hoặc mô tả chi tiết sai lệch nếu có.
- Blockers: none hoặc vấn đề cần người sở hữu dự án quyết định.
- Scope change requests: none hoặc yêu cầu thay đổi phạm vi.

### Skill/capability cần chạy (Skill/capability to run)
- Capability: backend-implementation
- Next skill: `$implement-backend`

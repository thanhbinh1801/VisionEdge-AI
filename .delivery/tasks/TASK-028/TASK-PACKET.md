---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T23:12:29+07:00"
task_id: TASK-028
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-028 Verification End-to-End cho CR-005 Telegram Evidence

- Task ID: TASK-028
- Task type: verification
- Scope: feature
- Module: alert-dispatcher
- Capability: verify-feature
- Linked requirements: REQ-002, REQ-003, REQ-004, REQ-008, REQ-009, CR-005
- Dependencies: TASK-026, TASK-027
- Write scope: .delivery/tasks/TASK-028/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/tasks/TASK-026/API-CONTRACT.md, .delivery/tasks/TASK-027/TASK-RESULT.md, backend implementation under backend/app/
- Expected outputs: .delivery/tasks/TASK-028/TEST-REPORT.md, .delivery/tasks/TASK-028/TASK-RESULT.md, bug records if verification fails
- Completion gate: Xác minh end-to-end một vi phạm khu vực do đối tượng cấm đi vào zone tạo đúng 1 event/clip/Telegram trong cooldown; Telegram có đủ nội dung bắt buộc và gửi trực tiếp video 10s; metadata lane không tự kích hoạt Telegram; lỗi Telegram không chặn lưu event/clip hoặc cảnh báo UI.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, thực hiện migration phá hủy dữ liệu, mở rộng phạm vi hoặc ảnh hưởng tới công việc đang triển khai/đã hoàn thành.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Xác minh end-to-end tính năng thông báo bằng chứng vi phạm an ninh khu vực qua Telegram (CR-005) đã được triển khai tại backend: kiểm tra một vi phạm khu vực do đối tượng cấm đi vào zone tạo đúng 1 sự kiện/clip 10s MP4/thông báo Telegram trong cửa sổ Cooldown; tin nhắn Telegram chứa đầy đủ 5 nội dung thông tin bắt buộc (mốc thời gian vi phạm đúng từ frame, camera, zone, loại đối tượng, lý do vi phạm) đính kèm trực tiếp file video clip 10s MP4; phân làn realtime metadata lane không tự kích hoạt Telegram; và các sự cố lỗi Telegram (bot token sai, network timeout, rate limit) được cô lập không làm gián đoạn việc lưu CSDL sự kiện hay phát tín hiệu cảnh báo trên Web UI.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-028/TASK-PACKET.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/DOMAIN-MODEL.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/changes/CR-005/CHANGE-IMPACT.md`
- `.delivery/tasks/TASK-026/API-CONTRACT.md`
- `.delivery/tasks/TASK-026/TASK-RESULT.md`
- `.delivery/tasks/TASK-027/TASK-RESULT.md`
- Code backend đã triển khai tại `backend/app/services/alert_dispatcher.py`, `backend/app/services/event_manager.py`, `backend/app/api/v1/events.py`, `backend/app/api/v1/alerts.py`, `backend/app/api/router.py`, `backend/tests/test_alerts.py`, `backend/tests/test_live_detections_event.py`
- Phần `TASK-028 Verification End-to-End cho CR-005 Telegram Evidence` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- `.delivery/tasks/TASK-028/TEST-REPORT.md`
- `.delivery/tasks/TASK-028/TASK-RESULT.md`
- `.delivery/tasks/TASK-028/BUG-NNN.md` (nếu kiểm tra phát hiện lỗi)

### Phạm vi cấm (Forbidden scope)
- Không chỉnh sửa production code backend/frontend, `.delivery/MASTER-PLAN.md`, requirements, architecture, approved API contracts, database schema/migrations, hoặc tệp của task khác trong quá trình verification.
- Không tự ý sửa code sản phẩm khi phát hiện lỗi; nếu phát hiện lỗi phải ghi vết `BUG-NNN.md` và tạo Scope Change Request / Bug Record.
- Không tự chuyển trạng thái artifact thành `approved` trước khi được project owner review.

### Tiêu chí nghiệm thu (Acceptance criteria)
- Xác minh một vi phạm khu vực (do đối tượng thuộc danh sách cấm đi vào zone) sinh ra đúng 1 sự kiện `ZONE_VIOLATION_EVENT`, cắt đúng clip 10s MP4 chứng cứ, và phát đúng 1 thông báo Telegram trong cửa sổ Cooldown.
- Tin nhắn Telegram format HTML đáp ứng đủ 5 thông tin bắt buộc: Mốc thời gian vi phạm (`captured_at`), Camera (`camera_name` / `camera_id`), Zone (`zone_name` / `zone_id`), Loại đối tượng (`object_type_name` / `object_type`), Lý do vi phạm (`violation_reason`).
- File video clip 10s MP4 được upload đính kèm trực tiếp vào tin nhắn Telegram qua phương thức `sendVideo`.
- Phân làn dữ liệu chuẩn: Phân làn realtime metadata (`AREA_FRAME_METADATA`) chỉ phục vụ UI metadata feed và không tự kích hoạt gửi tin nhắn Telegram.
- Cô lập lỗi Telegram: Khi Telegram API bị lỗi (sai bot token, chat ID không tồn tại, rate limit 429, network timeout), `telegram_status` chuyển thành `failed` cùng `telegram_error` tương ứng; event vi phạm vẫn lưu thành công vào CSDL, video clip vẫn trích xuất, và WebSocket alert vẫn phát về Web UI.
- API `GET /api/v1/events/{event_id}/evidence` trả về payload bằng chứng vi phạm đầy đủ thông tin chuẩn theo hợp đồng `API-CONTRACT.md`.
- API `POST /api/v1/alerts/telegram/test` phản hồi chính xác kết quả kiểm thử kết nối Bot Telegram.
- Chạy thành công toàn bộ test suite `pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py` với exit code 0.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- Cần phân biệt rõ mốc thời gian vi phạm thực tế `captured_at` từ video frame với thời điểm gọi gửi HTTP request tới Telegram API.
- Đảm bảo kiểm thử cả trường hợp Telegram Bot API thành công và trường hợp Telegram API thất bại để xác nhận tính cô lập non-blocking.
- Kiểm tra tính nhất quán Cooldown để khẳng định các frame vi phạm tiếp theo không phát trùng lặp tin nhắn Telegram.
- Nhiệm vụ verification chỉ kiểm chứng và thu thập bằng chứng nghiệm thu, không sửa code production.

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh xác minh theo MASTER-PLAN: `python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-028`.
- Bộ lệnh pytest backend: `.\venv\Scripts\python.exe -m pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py -q`.
- Biên dịch mã nguồn backend: `.\venv\Scripts\python.exe -m compileall -q backend/app/services/alert_dispatcher.py backend/app/api/v1/alerts.py backend/app/api/v1/events.py backend/tests/test_alerts.py`.

### Điều kiện leo thang (Escalation conditions)
- Dừng lại và báo cáo trong `TASK-RESULT.md` nếu việc xác minh yêu cầu sửa đổi backend/frontend production code, thay đổi contract đã duyệt, thay đổi CSDL schema, xóa dữ liệu runtime, hoặc nếu hạ tầng mạng/Telegram test không thể truy cập.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Task ID: TASK-028
- Outcome: completed | blocked
- Inputs used: Danh sách các tệp/artifact đã đọc.
- Outputs produced: `.delivery/tasks/TASK-028/TEST-REPORT.md`, `.delivery/tasks/TASK-028/TASK-RESULT.md` (hoặc `BUG-NNN.md` nếu có lỗi).
- Validation evidence: Exact commands, exit codes và kết quả thực thi.
- Deviations: none hoặc sai lệch phát hiện được.
- Blockers: none hoặc mô tả điểm chặn.
- Scope change requests: none hoặc yêu cầu thay đổi phạm vi.

### Skill/capability cần chạy (Skill/capability to run)
- Capability: verify-feature
- Next skill: `$verify-feature`

---
artifact: TASK-RESULT.md
version: "1.0"
owner: design-api
status: approved
updated_at: "2026-08-24T22:43:00+07:00"
task_id: TASK-026
depends_on: [TASK-PACKET.md, API-CONTRACT.md]
---

# TASK-026 Kết quả — Thiết kế Contract Event/Alert Evidence cho Telegram CR-005

- Task ID: TASK-026
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-026/TASK-PACKET.md`, `.delivery/REQUIREMENTS.md`, `.delivery/DOMAIN-MODEL.md`, `.delivery/changes/CR-005/CHANGE-IMPACT.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`.
- Outputs produced: `.delivery/tasks/TASK-026/API-CONTRACT.md`, `.delivery/tasks/TASK-026/TASK-RESULT.md`, cập nhật hợp đồng toàn cục `.delivery/API-CONTRACT.md`.
- Validation evidence: `python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-026` đã pass với `OK: validated API design task TASK-026`.
- Deviations: none
- Blockers: none
- Scope change requests: none

## Tóm tắt Thiết kế (Design Summary)

1. **Chuẩn hóa Bằng chứng Vi phạm khu vực (Area Violation Evidence Payload)**:
   - Bổ sung mốc thời gian vi phạm phát hiện thực tế từ frame (`captured_at`), thông tin camera (`camera_id`, `camera_name`), thông tin zone (`zone_id`, `zone_name`), loại đối tượng (`object_type`, `object_type_name`), lý do vi phạm (`violation_reason`), cùng đính kèm video clip chứng cứ 10s MP4 (`video_clip_url`, `video_clip_duration_seconds`).
2. **Cấu trúc Tin nhắn Telegram & Quản lý Trạng thái**:
   - Định dạng tin nhắn HTML chuẩn 5 trường thông tin đính kèm trực tiếp file MP4 chứng cứ 10s.
   - Thêm trường `telegram_status` (`pending`, `sent`, `failed`, `skipped`) và `telegram_error` để ghi nhận nhật ký phát cảnh báo mà không gây gián đoạn luồng CSDL/WebSocket khi Telegram gặp sự cố.
3. **Quy tắc Phân làn và Khử trùng lặp (Deduplication)**:
   - Giữ nguyên sự phân tách giữa metadata lane và event/alert lane. Chỉ có sự kiện vi phạm đầu tiên vượt qua Cooldown mới kích hoạt gửi Telegram.
4. **Cập nhật Hợp đồng Toàn cục**:
   - Đã cập nhật `.delivery/API-CONTRACT.md` để ghi nhận các schema và quy tắc của CR-005.

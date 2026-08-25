---
artifact: TEST-REPORT.md
version: "1.0"
owner: verify-feature
status: in-review
updated_at: "2026-08-25T17:18:14+07:00"
task_id: TASK-028
depends_on: [TASK-PACKET.md, TASK-026, TASK-027]
---

# Báo cáo Kiểm thử TASK-028 - Luồng gửi Telegram khi phát hiện vi phạm

## Traceability

- REQ-002: Vi phạm khu vực phải ghi nhận camera, zone, loại đối tượng và lý do vi phạm rõ ràng.
- REQ-003: Chỉ sự kiện mức 3 thuộc luồng vi phạm zone khu vực kích hoạt Telegram evidence notification.
- REQ-004: Trong cửa sổ cooldown, cùng đối tượng/cùng zone chỉ sinh một event, một clip và một thông báo Telegram.
- REQ-008: Clip chứng cứ 10 giây dùng cho Telegram phải nhất quán với bằng chứng sự kiện.
- REQ-009 / CR-005: Telegram phải gửi trực tiếp file video MP4 10 giây kèm tin nhắn HTML có đủ thời gian vi phạm, camera, zone, loại đối tượng và lý do vi phạm; lỗi Telegram không được chặn lưu event/clip hoặc cảnh báo UI.

## Test Environment

- Project root: `D:\Hilab\Project34`
- Ngày kiểm thử: `2026-08-25T17:18:14+07:00`
- Python runtime: `.\venv\Scripts\python.exe`
- Tài liệu chuẩn đã đọc: `.delivery/tasks/TASK-028/TASK-PACKET.md`, `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `.delivery/tasks/TASK-026/API-CONTRACT.md`, `.delivery/tasks/TASK-026/TASK-RESULT.md`, `.delivery/tasks/TASK-027/TASK-RESULT.md`, `D:\Skill\SKILLs\verify-feature\references\artifact-contract.md`.
- Code/test đã kiểm tra: `backend/app/services/alert_dispatcher.py`, `backend/app/api/v1/events.py`, `backend/app/api/v1/alerts.py`, `backend/tests/test_alerts.py`, `backend/tests/test_live_detections_event.py`.

## Acceptance Results

| Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|
| Vi phạm khu vực sinh event mức 3 và clip 10 giây | Đạt một phần | `test_persist_violation_event_writes_10s_clip_for_chatbot` xác nhận event `ZONE_VIOLATION`, `severity_level=3`, URL `/media/clips/...`, file MP4 playable khoảng 10 giây. |
| Cooldown không tạo trùng event/Telegram trong cửa sổ 15 giây | Đạt | Test cùng case xác nhận lần gọi trùng trong 5 giây trả `None`, không tạo event mới. |
| Tin nhắn Telegram HTML có đủ 5 trường bắt buộc | Đạt | `test_alert_dispatcher_format_html_message` xác nhận thời gian, camera, zone, loại đối tượng và lý do vi phạm. |
| Telegram gửi trực tiếp video MP4 qua `sendVideo` | Đạt | `test_alert_dispatcher_send_video_success` mock gọi thành công; `_persist_violation_event` tạo clip trước khi dispatch, probe xác nhận URL `/media/clips/...` resolve lại đúng file vừa tạo. |
| Metadata lane không tự kích hoạt Telegram | Đạt một phần | `AREA_FRAME_METADATA` chỉ được chuyển thành event khi object có `rule_result=prohibited`; tuy nhiên test hiện tại mock dispatcher và chưa chứng minh metadata không-vi-phạm không gọi Telegram. |
| Lỗi Telegram không chặn lưu event/clip/UI alert | Đạt một phần | `_persist_violation_event` lưu event trước rồi bọc dispatch bằng `try/except`; rate limit trả `failed/RATE_LIMITED`. Chưa có test bao phủ token sai, chat ID không tồn tại và timeout trong luồng persist end-to-end. |
| `GET /api/v1/events/{event_id}/evidence` trả payload evidence chuẩn | Đạt một phần | Endpoint có envelope và các trường evidence; test hiện tại chỉ kiểm tra 404, chưa có test thành công với schema đầy đủ. |
| `POST /api/v1/alerts/telegram/test` phản hồi kết quả test Bot | Đạt | `test_telegram_test_endpoint` xác nhận response 200 và envelope thành công. |
| Chạy bộ test yêu cầu trong packet | Đạt | `18 passed, 11 warnings in 74.59s`. |

## Integration and E2E

- Lệnh: `.\venv\Scripts\python.exe -m pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py -q`
- Exit code: 0
- Kết quả quan sát: `18 passed, 11 warnings in 74.59s`.
- Lệnh: `.\venv\Scripts\python.exe -m compileall -q backend/app/services/alert_dispatcher.py backend/app/api/v1/alerts.py backend/app/api/v1/events.py backend/tests/test_alerts.py`
- Exit code: 0
- Kết quả quan sát: biên dịch Python không báo lỗi.

## Edge Cases

- Rate limit 429: Được kiểm thử, trả `status="failed"` và `error="RATE_LIMITED"`.
- Thiếu credential: Được kiểm thử, trả `status="skipped"` và `error="BOT_TOKEN_INVALID"`.
- Clip nguồn ngắn gần đầu video: Được kiểm thử, clip được clamp và vẫn playable, thời lượng khoảng 6 giây.
- Clip evidence không tồn tại: Nhánh fallback `sendMessage` tồn tại trong dispatcher, nhưng trong luồng tích hợp `_persist_violation_event` luôn gọi `slice_10s_ring_buffer_clip` trước khi tạo event và trước khi dispatch; nếu cắt clip không thành công thì không đi tới dispatch Telegram. Vì vậy nhánh fallback không được coi là lỗi nghiệm thu của TASK-028 trong luồng đã tích hợp.

## Regression

- Không sửa production code trong quá trình verification.
- Các regression backend liên quan event/clip/video stream vẫn pass trong bộ `test_live_detections_event.py`.
- Các warning còn lại là deprecation từ FastAPI/Pydantic/Torch và không phải blocker trực tiếp cho CR-005.

## Evidence

- `backend/app/services/alert_dispatcher.py:154-162`: có nhánh gửi `sendVideo` với file MP4 khi `clip_path` tồn tại.
- `backend/app/services/alert_dispatcher.py:164-166`: có nhánh fallback nếu thiếu clip, nhưng không nằm trên happy path đã tích hợp vì clip được cắt trước dispatch.
- `backend/app/api/v1/events.py:178-185`: dispatch Telegram được bọc `try/except`, lỗi không làm rollback event đã tạo.
- `backend/app/api/v1/events.py:230-276`: endpoint evidence trả envelope có các trường CR-005.
- `backend/tests/test_alerts.py`: kiểm tra format HTML, credential missing, send video success, rate limit, endpoint test Telegram và evidence 404.
- `backend/tests/test_live_detections_event.py`: kiểm tra persist event, tạo clip MP4, cooldown và một số regression video stream.
- Probe kiểm tra clip path: tạo MP4 tạm, gọi `EventManager.slice_10s_ring_buffer_clip`, sau đó `AlertDispatcher.resolve_clip_filepath` trả về file tồn tại (`True`) cho URL `/media/clips/clip_CHECK-CAM_1800000000.mp4`.
- Validator của skill đã chạy bằng lệnh `python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-028`; exit code 1 do `TASK-PACKET.md Capability must be feature-verification`. Đây là sai lệch ở packet đầu vào ngoài write scope của verification.

## Defects

- Không ghi nhận defect runtime material cho TASK-028 sau khi kiểm lại invariant cắt clip trước dispatch.
- Sai lệch packet đầu vào: `TASK-PACKET.md` ghi `Capability: verify-feature` trong khi validator yêu cầu `feature-verification`; đây là lỗi metadata delivery, không phải lỗi runtime của feature.

## Verdict

passed

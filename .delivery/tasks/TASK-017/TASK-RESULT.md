---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-017
owner: implement-backend
status: in-review
updated_at: "2026-08-23T15:59:01+07:00"
---

# Kết quả Task: TASK-017 — Backend Area Metadata Lane và Zone Cache

- Mã task: TASK-017
- Kết quả: completed
- Đầu vào đã dùng: `.delivery/tasks/TASK-017/TASK-PACKET.md`, `.delivery/tasks/TASK-017/BUG-001.md`, `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `backend/app/api/v1/events.py`, `backend/app/api/v1/zones.py`, `backend/app/api/v1/websocket.py`, `backend/app/services/video_stream.py`, `backend/app/services/vision_pipeline.py`, `backend/database/repository.py`, existing backend tests.
- Đầu ra đã tạo: BUG-001 fix adds `zone_name` to `GET /api/v1/events` responses by deriving it from the related `Zone` while preserving `zone_id`; prior TASK-017 outputs remain `backend/app/services/zone_cache.py`, `backend/app/services/area_metadata.py`, cache-aware updates cho `backend/app/api/v1/events.py`, `backend/app/api/v1/zones.py`, `backend/app/api/v1/websocket.py`, snapshot latency/source-time enrichment trong `backend/app/services/video_stream.py`, real MP4 evidence clip extraction trong `backend/app/services/event_manager.py`, route composition fix trong `backend/main.py` + `backend/app/api/router.py` để expose public WebSocket contract `/ws/v1/events`, hardening cho WebSocket send lifecycle trong `backend/app/api/v1/websocket.py`, hardening first-frame handshake cho `GET /api/v1/events/video-feed`, và hardening entrypoint `backend/main.py` để `python main.py` không bật reload mặc định.
- Bằng chứng xác minh: BUG-001 scoped checks passed: `.\venv\Scripts\python.exe -m pytest backend\tests\test_live_detections_event.py -q` exit 0 (`12 passed, 11 warnings in 19.02s`); `.\venv\Scripts\python.exe -m compileall -q backend\app\api\v1\events.py backend\tests\test_live_detections_event.py` exit 0; `.\venv\Scripts\python.exe -m pytest backend\tests\test_websocket_route_contract.py backend\tests\test_live_detections_event.py -q` exit 0 (`13 passed, 11 warnings in 19.05s`); `python D:\Skill\SKILLs\implement-backend\scripts\validate_backend_implementation.py D:\Hilab\Project34 TASK-017` exit 0 (`OK: validated backend implementation task TASK-017`). Prior evidence remains: `.\venv\Scripts\python.exe -m compileall -q backend\app backend\tests\test_live_detections_event.py backend\tests\test_ai_engine.py` exit 0; `ruff check backend\app\services\event_manager.py backend\app\api\v1\events.py backend\app\services\video_stream.py backend\tests\test_live_detections_event.py` exit 0 (`All checks passed!`); `.\venv\Scripts\python.exe -m pytest backend\tests\test_live_detections_event.py backend\tests\test_ai_engine.py -q` exit 0 (`21 passed, 9 warnings in 61.49s`).
- Changed files: `backend/app/api/v1/events.py`, `backend/tests/test_live_detections_event.py`, `.delivery/tasks/TASK-017/TASK-RESULT.md`; prior TASK-017 changed files also include `backend/app/api/v1/websocket.py`, `backend/app/services/event_manager.py`, `backend/app/services/video_stream.py`, `backend/main.py`, `backend/tests/test_video_feed_regression.py`, `backend/tests/test_websocket_connection_manager.py`, `backend/tests/test_websocket_route_contract.py`.
- Tests changed: Added API contract regression in `backend/tests/test_live_detections_event.py` that seeds a camera, zone, and `ZONE_VIOLATION` event, calls `GET /api/v1/events`, and asserts the response contains both `zone_id` and matching `zone_name`; prior OpenCV clip evidence tests remain in the same file.
- Commands run: `.\venv\Scripts\python.exe -m pytest backend\tests\test_live_detections_event.py -q` (exit 1 first run due to test fixture collision with seeded `BAI-KIEM`, then fixed); `.\venv\Scripts\python.exe -m pytest backend\tests\test_live_detections_event.py -q` (exit 0, `12 passed, 11 warnings in 19.02s`); `.\venv\Scripts\python.exe -m compileall -q backend\app\api\v1\events.py backend\tests\test_live_detections_event.py` (exit 0); `.\venv\Scripts\python.exe -m pytest backend\tests\test_websocket_route_contract.py backend\tests\test_live_detections_event.py -q` (exit 0, `13 passed, 11 warnings in 19.05s`); `python D:\Skill\SKILLs\framework\scripts\current_timestamp.py` (exit 0); `python D:\Skill\SKILLs\implement-backend\scripts\validate_backend_implementation.py D:\Hilab\Project34 TASK-017` (exit 0, `OK: validated backend implementation task TASK-017`).
- Sai lệch: Không thay đổi schema DB, frontend, hay approved contracts ngoài backend scope và `.delivery/tasks/TASK-017/`. Warning còn lại là deprecation của FastAPI/Pydantic/Torch hiện hữu, không làm fail kiểm tra.
- Điểm chặn: none
- Yêu cầu đổi phạm vi: none

## Follow-up defects

- [BUG-002.md](D:/Hilab/Project34/.delivery/tasks/TASK-017/BUG-002.md) — Đã xử lý: WebSocket metadata publisher nay có watcher riêng để nhận disconnect, không block event loop khi chờ snapshot, cleanup task trong `finally`, và `python main.py` không bật Uvicorn reload mặc định.
- [BUG-003.md](D:/Hilab/Project34/.delivery/tasks/TASK-017/BUG-003.md) — Đã xử lý: route `GET /api/v1/events/video-feed` nay phải lấy và mã hóa được frame đầu tiên trong khoảng khởi động hữu hạn, nếu không sẽ trả `503` tường minh thay vì treo vô hạn trước byte MJPEG đầu tiên.
- [BUG-004.md](D:/Hilab/Project34/.delivery/tasks/TASK-017/BUG-004.md) — Đã xử lý: area event lane tao MP4 evidence that từ source video hiện tại, luu `video_clip_url` vào event `ZONE_VIOLATION`, và test mo clip bang OpenCV để fail nếu quay lai placeholder bytes.

## Implementation summary

- Them `zone_cache_service` để giữ zone runtime theo `camera_id`, version hoa cache và refresh/invalidate ngay sau CRUD zone.
- Them `build_area_metadata_event` để tách metadata lane khỏi event persistence lane và chuan hoa payload `AREA_FRAME_METADATA`.
- Cap nhat `ProcessedFrameSnapshot` để mang `pipeline_latency_ms`, phục vụ metadata publisher và KPI realtime.
- Cap nhat `ProcessedFrameSnapshot` để mang `source_timestamp_seconds`; `GET /api/v1/events/live-detections` truyen `video_time` nếu client gui, nếu không dung source timestamp từ snapshot.
- Thay placeholder `MP4_RING_BUFFER_10S_SAMPLE_DATA` bang OpenCV `VideoCapture`/`VideoWriter` để cat MP4 that quanh thoi diem vi pham. Clip target la 10 giay khi source du dai; nếu event gan dau/cuoi hoặc source ngan hon 10 giay, start/end được clamp vào source bounds và clip có duration hop ly theo phan source có san.
- Chuyen `/api/v1/events/video-feed` và `/api/v1/events/live-detections` sang lấy zone từ cache thay vì query DB trong hot path mỗi frame.
- Tách logic mã hóa MJPEG trong `video_feed()` thành helper cục bộ, prime frame đầu tiên trước khi dựng `StreamingResponse`, và tra `503` rõ rang nếu không lấy được snapshot hoặc không encode được frame đầu tiên trong cửa sổ khởi động.
- Them WebSocket `/ws/v1/events` phục vụ metadata lane mới, đồng thời giữ `/ws/alerts` cho tương thích ngan han.
- Tach `websocket.router` khỏi `api_router` để REST endpoints vẫn tiếp tục nam duoi `/api/v1/...`, con WebSocket gateway được mount trực tiếp ở app-level và public dung contract `/ws/v1/events`.
- Harden `ConnectionManager.send_json()` để disconnect stale client và tra ve trang thai that bai khi `send_text` nem exception, giữp publisher loop dung sach thay vì tiếp tục spam socket loi.
- Cap nhat `websocket_events_endpoint()` để có disconnect watcher riêng, chay `wait_for_snapshot()` qua `asyncio.to_thread()`, `break` khi send thất bại và luôn cleanup connection/task trong `finally`.
- Cap nhat `backend/main.py` để `python main.py` chay mot process không reload mặc định; nếu cần reload khi dev có the bat bang `SENTRIAI_RELOAD=1`.

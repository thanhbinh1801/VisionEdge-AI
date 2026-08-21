---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-017
owner: implement-backend
status: in-review
updated_at: "2026-08-21T10:25:47+07:00"
---

# Task Result: TASK-017 — Backend Area Metadata Lane và Zone Cache

- Task ID: TASK-017
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-017/TASK-PACKET.md`, `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `backend/app/api/v1/events.py`, `backend/app/api/v1/zones.py`, `backend/app/api/v1/websocket.py`, `backend/app/services/video_stream.py`, `backend/app/services/vision_pipeline.py`, `backend/database/repository.py`, existing backend tests.
- Outputs produced: `backend/app/services/zone_cache.py`, `backend/app/services/area_metadata.py`, cache-aware updates cho `backend/app/api/v1/events.py`, `backend/app/api/v1/zones.py`, `backend/app/api/v1/websocket.py`, snapshot latency enrichment trong `backend/app/services/video_stream.py`, route composition fix trong `backend/main.py` + `backend/app/api/router.py` để expose public WebSocket contract `/ws/v1/events`, hardening cho WebSocket send lifecycle trong `backend/app/api/v1/websocket.py`, hardening first-frame handshake cho `GET /api/v1/events/video-feed`, và hardening entrypoint `backend/main.py` để `python main.py` không bật reload mặc định.
- Validation evidence: `.\venv\Scripts\python.exe -m compileall -q backend` exit 0; `ruff check backend/app/api/v1/websocket.py backend/main.py backend/tests/test_websocket_connection_manager.py backend/tests/test_websocket_route_contract.py` exit 0; `.\venv\Scripts\python.exe -m pytest backend/tests/test_websocket_connection_manager.py backend/tests/test_websocket_route_contract.py backend/tests/test_video_feed_regression.py -q` exit 0 (`5 passed`).
- Changed files: `backend/app/api/v1/events.py`, `backend/app/api/v1/websocket.py`, `backend/main.py`, `backend/tests/test_video_feed_regression.py`, `backend/tests/test_websocket_connection_manager.py`, `backend/tests/test_websocket_route_contract.py`, `.delivery/tasks/TASK-017/TASK-RESULT.md`.
- Tests changed: Thêm `backend/tests/test_video_feed_regression.py` cho BUG-003; sửa `backend/tests/test_websocket_connection_manager.py` để chạy bằng `asyncio.run()` trong môi trường pytest hiện có; sửa `backend/tests/test_websocket_route_contract.py` để duyệt route đệ quy qua `_IncludedRouter` và khóa public path `/ws/v1/events`.
- Commands run: `.\venv\Scripts\python.exe -m compileall -q backend` (exit 0); `ruff check backend/app/api/v1/websocket.py backend/main.py backend/tests/test_websocket_connection_manager.py backend/tests/test_websocket_route_contract.py` (exit 0); `.\venv\Scripts\python.exe -m pytest backend/tests/test_websocket_connection_manager.py backend/tests/test_websocket_route_contract.py backend/tests/test_video_feed_regression.py -q` (exit 0, `5 passed, 11 warnings in 50.26s`).
- Deviations: Không thay đổi schema DB, frontend, hay approved contracts ngoài backend scope và `.delivery/tasks/TASK-017/`. Warning còn lại là deprecation của FastAPI/Pydantic/Torch hiện hữu, không làm fail kiểm tra.
- Blockers: none
- Scope change requests: none

## Follow-up defects

- [BUG-002.md](D:/Hilab/Project34/.delivery/tasks/TASK-017/BUG-002.md) — Đã xử lý: WebSocket metadata publisher nay có watcher riêng để nhận disconnect, không block event loop khi chờ snapshot, cleanup task trong `finally`, và `python main.py` không bật Uvicorn reload mặc định.
- [BUG-003.md](D:/Hilab/Project34/.delivery/tasks/TASK-017/BUG-003.md) — Đã xử lý: route `GET /api/v1/events/video-feed` nay phải lấy và mã hóa được frame đầu tiên trong khoảng khởi động hữu hạn, nếu không sẽ trả `503` tường minh thay vì treo vô hạn trước byte MJPEG đầu tiên.

## Implementation summary

- Thêm `zone_cache_service` để giữ zone runtime theo `camera_id`, version hóa cache và refresh/invalidate ngay sau CRUD zone.
- Thêm `build_area_metadata_event` để tách metadata lane khỏi event persistence lane và chuẩn hóa payload `AREA_FRAME_METADATA`.
- Cập nhật `ProcessedFrameSnapshot` để mang `pipeline_latency_ms`, phục vụ metadata publisher và KPI realtime.
- Chuyển `/api/v1/events/video-feed` và `/api/v1/events/live-detections` sang lấy zone từ cache thay vì query DB trong hot path mỗi frame.
- Tách logic mã hóa MJPEG trong `video_feed()` thành helper cục bộ, prime frame đầu tiên trước khi dựng `StreamingResponse`, và trả `503` rõ ràng nếu không lấy được snapshot hoặc không encode được frame đầu tiên trong cửa sổ khởi động.
- Thêm WebSocket `/ws/v1/events` phục vụ metadata lane mới, đồng thời giữ `/ws/alerts` cho tương thích ngắn hạn.
- Tách `websocket.router` khỏi `api_router` để REST endpoints vẫn tiếp tục nằm dưới `/api/v1/...`, còn WebSocket gateway được mount trực tiếp ở app-level và public đúng contract `/ws/v1/events`.
- Harden `ConnectionManager.send_json()` để disconnect stale client và trả về trạng thái thất bại khi `send_text` ném exception, giúp publisher loop dừng sạch thay vì tiếp tục spam socket lỗi.
- Cập nhật `websocket_events_endpoint()` để có disconnect watcher riêng, chạy `wait_for_snapshot()` qua `asyncio.to_thread()`, `break` khi send thất bại và luôn cleanup connection/task trong `finally`.
- Cập nhật `backend/main.py` để `python main.py` chạy một process không reload mặc định; nếu cần reload khi dev có thể bật bằng `SENTRIAI_RELOAD=1`.

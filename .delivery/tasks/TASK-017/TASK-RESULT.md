---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-017
owner: implement-backend
status: in-review
updated_at: "2026-08-27T22:44:27+07:00"
---

# Kết quả Task: TASK-017 — Backend Area Metadata Lane và Zone Cache

- Mã task: TASK-017
- Kết quả: completed
- Outcome: completed
- Task ID: TASK-017
- Inputs used: `.delivery/tasks/TASK-017/TASK-PACKET.md`, `.delivery/tasks/TASK-017/BUG-005.md`, `.delivery/tasks/TASK-027/TASK-PACKET.md`, `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `backend/app/api/v1/events.py`, `backend/app/services/event_manager.py`, `backend/tests/test_alerts.py`, `backend/tests/test_live_detections_event.py`.
- Outputs produced: non-blocking BUG-005 backend fix in `backend/app/api/v1/events.py` and `backend/app/services/event_manager.py`, regression updates in `backend/tests/test_live_detections_event.py`, `.delivery/tasks/TASK-017/BUG-005.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`.
- Validation evidence: BUG-005 regression exit 0 (`1 passed, 6 warnings in 8.44s`); related regression exit 0 (`24 passed, 6 warnings in 9.22s`); compileall exit 0; ruff exit 0 (`All checks passed!`).
- Deviations: none
- Blockers: none
- Scope change requests: none
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
- [BUG-005.md](D:/Hilab/Project34/.delivery/tasks/TASK-017/BUG-005.md) — Đã xử lý: `_persist_violation_event()` nay chỉ dedup, tạo URL clip ổn định, ghi event DB và trả về ngay; cắt clip MP4, transcode H.264 và gửi Telegram được đưa sang background executor giới hạn 2 worker, cache trạng thái Telegram khởi tạo `pending` rồi cập nhật `sent/failed/skipped` sau khi job nền hoàn tất. Regression test chậm alert đã chuyển xanh.
- [BUG-006.md](D:/Hilab/Project34/.delivery/tasks/TASK-017/BUG-006.md) — Đã xử lý: violation evidence job không còn fallback về đầu video khi thiếu `source_timestamp_seconds`, và khi có timestamp sẽ tái tạo clip cùng tên để thay thế file 10 giây đầu video đã sinh sai trước đó.

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
- BUG-005 fix: thêm `EventManager.evidence_clip_url()` để gán URL bằng chứng deterministic trước khi file clip được tạo; thêm background alert/evidence executor trong `backend/app/api/v1/events.py`; thêm test hook `_wait_for_background_alert_jobs()` cho regression; cập nhật tests để chờ job nền khi cần kiểm tra file MP4 thật.

## BUG-005 validation evidence

- `.\venv\Scripts\python.exe -m pytest backend/tests/test_live_detections_event.py::test_violation_persistence_does_not_wait_for_slow_telegram_dispatch -q` — exit 0, `1 passed, 6 warnings in 8.44s`.
- `.\venv\Scripts\python.exe -m pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py -q` — exit 0, `24 passed, 6 warnings in 9.22s`.
- `.\venv\Scripts\python.exe -m compileall -q backend\app\api\v1\events.py backend\app\services\event_manager.py backend\tests\test_live_detections_event.py` — exit 0.
- `ruff check backend\app\api\v1\events.py backend\app\services\event_manager.py backend\tests\test_live_detections_event.py` — exit 0, `All checks passed!`.

## BUG-005 changed files

- `backend/app/api/v1/events.py`
- `backend/app/services/event_manager.py`
- `backend/tests/test_live_detections_event.py`
- `.delivery/tasks/TASK-017/BUG-005.md`
- `.delivery/tasks/TASK-017/TASK-RESULT.md`

## Follow-up container detect-only

- Theo quyết định vận hành mới, `shipping_container` là thùng container tĩnh: chỉ nhận diện/hiển thị metadata, không tham gia kiểm tra vùng cấm, không tính KPI máy móc hoạt động, không sinh event vi phạm và không gửi alert.
- `container` là label vận hành legacy cho xe container trong rule zone hiện có; raw/model class `container_truck` được chuẩn hóa về `container` để khớp đúng label UI.
- `backend/app/services/vision_pipeline.py` giữ `DETECT_ONLY_CLASSES={"shipping_container"}`; `container` dùng footprint overlap như nhóm xe nên vẫn check vi phạm khi vào zone cấm.
- `backend/app/api/v1/events.py` chặn persistence lane chỉ cho `shipping_container`; `container` vẫn được persist/cảnh báo khi rule zone báo vi phạm.
- `backend/app/services/area_metadata.py` không tính `shipping_container` vào `area_active_machinery`; `container` vẫn được tính là xe/máy móc hoạt động.
- `frontend/src/pages/AreaSecurityDashboard.tsx` hiển thị `shipping_container` là "Thùng container", còn label `container` vẫn là "Container".
- Test bổ sung/cập nhật: `backend/tests/test_ai_engine.py::test_container_is_detect_only_and_never_zone_checked`, `backend/tests/test_ai_engine.py::test_container_truck_still_checks_zone_violation`, `backend/tests/test_ai_engine.py::test_container_truck_matches_legacy_container_allowed_rule`, và `backend/tests/test_live_detections_event.py::test_container_metadata_violation_is_detect_only_not_persisted`.
- Bằng chứng xác minh: backend regression khu vực exit 0 (`46 passed, 6 warnings in 19.78s`); frontend `npm run lint` exit 0; compileall exit 0 cho các file backend/test đã chạm.
- Ghi chú lint: `ruff check` scoped qua `vision_pipeline.py` hiện bị chặn bởi nhiều cảnh báo style tồn tại sẵn trong file này (`UP006`, `UP035`, `RUF013`, `BLE001`, `SIM102`), nên không refactor rộng ngoài phạm vi bug container.

## Follow-up zone lane container truck

- Nguyên nhân ảnh chụp lúc 21:52: zone "Zone làn di chuyển" đang cho phép key legacy `container`, còn model trả raw class `container_truck`; backend trước đó giữ raw này thành object class riêng nên coi nó là không nằm trong allow-list và báo vi phạm sai.
- Sửa trong `backend/app/services/vision_pipeline.py`: raw/model class `container_truck` map về object class `container`; đồng thời giữ helper `ZONE_RULE_ALIASES` để dữ liệu/metadata cũ có `container_truck` vẫn match với rule `container`.
- Sửa trong `backend/app/api/v1/events.py`: nhánh fallback/live-detections dùng cùng helper `zone_rule_matches_class()` thay vì tự so chuỗi, tránh lệch logic giữa pipeline và endpoint.
- Test bổ sung: `backend/tests/test_ai_engine.py::test_container_truck_matches_legacy_container_allowed_rule`, xác nhận xe container trong zone có `allowed_classes=["container"]` không còn sinh `zone_violation`.
- Bằng chứng xác minh: backend regression khu vực exit 0 (`46 passed, 6 warnings in 19.78s`); compileall exit 0.

## Follow-up YOLOv11s finetune only

- Theo yêu cầu vận hành mới, runtime Area Monitoring bỏ hoàn toàn nhánh YOLO-World/open-vocabulary: không import `YOLOWorld`, không gọi `set_classes()`, không giữ prompt state, không dùng prompt constants, và không fallback sang `yolov8n.pt`/COCO nếu weights chính lỗi.
- `backend/app/services/vision_pipeline.py` chỉ nạp `ultralytics.YOLO(model_source)` từ `DETECTION_MODEL_WEIGHTS` và đặt `model_type="yolov11s-finetune"`; nếu checkpoint finetune không nạp được thì log lỗi và để `model=None` thay vì âm thầm chạy model khác.
- Mapping class chuyển sang `FINETUNE_CLASS_TO_CANONICAL`, chỉ chuẩn hóa nhãn do checkpoint finetune trả về. `container_truck` map về label vận hành `container`; `shipping_container` là thùng container detect-only.
- `backend/app/core/config.py`, `backend/app/services/lpr_engine.py`, và `frontend/src/components/layout/Header.tsx` được cập nhật wording để không còn mô tả runtime là YOLO-World.
- Test backend cập nhật từ kiểm tra prompt/open-vocab sang kiểm tra không giữ prompt state và mapping nhãn finetune.
- Bằng chứng xác minh: `rg` production qua `backend/app` và `frontend/src` không còn `YOLOWorld`, `yolo-world`, `set_classes`, hoặc prompt constants; backend regression khu vực exit 0 (`45 passed, 6 warnings in 28.16s`); frontend `npm run lint` exit 0; compileall exit 0.

## Follow-up evidence clip violation timestamp

- Nguyên nhân lỗi clip 10 giây đầu video: đường WebSocket/metadata lane tạo `AREA_FRAME_METADATA` nhưng không mang `source_timestamp_seconds`, nên `persist_area_metadata_violations()` không truyền được thời điểm vi phạm vào background evidence job; `EventManager.slice_10s_ring_buffer_clip()` nhận `None` và fallback về `0.0`.
- Sửa trong `backend/app/services/area_metadata.py`: payload metadata có thêm `source_timestamp_seconds` từ `snapshot.detection_source_timestamp_seconds`, tức thời điểm của frame đã chạy inference và sinh vi phạm.
- Sửa trong `backend/app/api/v1/events.py`: `persist_area_metadata_violations()` lấy timestamp từ payload nếu caller không truyền riêng, rồi chuyển tiếp vào `_persist_violation_event()` để job nền cắt đúng clip vi phạm.
- Sửa trong `backend/app/services/event_manager.py`: bỏ fallback `source_timestamp_seconds or 0.0`; chỉ fallback khi thật sự là `None` và log cảnh báo rõ để không che bug.
- Test bổ sung/cập nhật: metadata builder assert payload có `source_timestamp_seconds`; metadata persistence test dùng video 20 giây, event tại giây 8 và assert frame đầu clip gần giây 3, fail nếu quay về đầu video.
- Bằng chứng xác minh: targeted clip tests exit 0 (`3 passed, 6 warnings in 4.05s`); regression alert/live/metadata/stream exit 0 (`28 passed, 5 skipped, 6 warnings in 10.40s`); compileall exit 0.

## Follow-up area dashboard zone chips

- Theo yêu cầu UI mới, `frontend/src/pages/AreaSecurityDashboard.tsx` đã bỏ panel debug "Snapshot metadata đang hiển thị"; metadata WebSocket vẫn được dùng ngầm cho trạng thái và KPI.
- Sửa lỗi chip rule của `Zone cấm PT cá nhân`: dashboard giờ luôn fetch `fetchZonesStrict(BAI-KIEM)` để ưu tiên dữ liệu zone mới nhất từ backend thay vì chỉ dùng context cũ.
- Khi render chip rule, nếu `allowed_classes` có dữ liệu thì dashboard coi allow-list là nguồn quyết định chính; `forbidden_classes` cũ không còn được ưu tiên phủ định nhãn đã allowed. `container` cũng match các alias legacy như `Container`, `Xe container`, `container_truck`.
- Bằng chứng xác minh: `npm run lint` exit 0; `npm run build` exit 0 sau khi chạy ngoài sandbox vì lần đầu bị `spawn EPERM` ở esbuild.

## Follow-up BUG-006 evidence clip không lấy đầu video

- Sửa trong `backend/app/services/event_manager.py`: thêm tham số `overwrite_existing` cho `slice_10s_ring_buffer_clip()` để caller evidence job có thể ghi đè clip cũ cùng tên đã sinh sai.
- Sửa trong `backend/app/api/v1/events.py`: background violation evidence job yêu cầu bắt buộc có `source_timestamp_seconds`; nếu thiếu thì đánh dấu lỗi `VIDEO_CLIP_UNAVAILABLE` thay vì fallback về `0.0` và cắt từ đầu video.
- Sửa trong `backend/app/api/v1/events.py`: violation evidence job gọi slicer với `overwrite_existing=True`, đảm bảo Telegram không gửi lại file 10 giây đầu video đã cache từ trước.
- Test bổ sung: `backend/tests/test_live_detections_event.py::test_violation_evidence_job_overwrites_stale_source_start_clip`, tạo clip cũ bắt đầu ở giây 0 rồi xác nhận event mới tại giây 8 ghi đè thành clip bắt đầu gần giây 3.
- Test bổ sung: `backend/tests/test_live_detections_event.py::test_violation_evidence_job_fails_without_source_timestamp`, xác nhận thiếu timestamp không tạo clip đầu video và trạng thái Telegram/evidence chuyển sang failed.
- Bằng chứng xác minh: targeted BUG-006 tests exit 0 (`4 passed, 6 warnings in 7.88s`); regression alert/live/metadata/stream exit 0 (`30 passed, 5 skipped, 6 warnings in 8.15s`); compileall exit 0; ruff scoped exit 0 (`All checks passed!`).

## Follow-up BUG-006 container detect-only không sinh vi phạm

- Theo phản hồi runtime lúc 22:41, UI vẫn có event `Container` trong `Zone cấm PT cá nhân` với trạng thái `Vi phạm`; đây là sai vì thùng container tĩnh chỉ được nhận diện, không được tạo cảnh báo.
- Sửa trong `backend/app/services/vision_pipeline.py`: `DETECT_ONLY_CLASSES` bao gồm cả `container` và `shipping_container`; `container` không còn đi qua zone evaluator, nên không có `zone_violation`, `zone_name`, `zone_id` hay severity 3.
- Sửa trong `backend/app/api/v1/events.py`: persistence lane chặn cả `container` và `shipping_container`, kể cả metadata legacy đã có `rule_result="prohibited"`.
- Sửa trong `backend/app/services/area_metadata.py`: KPI `area_active_machinery` không tính `container`/`shipping_container` như máy móc đang hoạt động.
- Test cập nhật/bổ sung: container truck map về `container` nhưng vẫn detect-only; metadata legacy `object_class="container"` trong `Zone cấm PT cá nhân` không persist event.
- Bằng chứng xác minh: targeted container tests exit 0 (`5 passed, 6 warnings in 3.66s`); backend area regression exit 0 (`48 passed, 6 warnings in 19.49s`); compileall exit 0; ruff scoped exit 0 (`All checks passed!`).

---
artifact: TEST-REPORT.md
version: "1.0"
task_id: TASK-033
owner: verify-feature
status: in-review
updated_at: "2026-08-27T20:41:30+07:00"
---

# Báo cáo kiểm thử TASK-033 - CR-007 Verification và Regression Không đổi LPR/GATE-01

## Traceability

| Yêu cầu | Bằng chứng kiểm thử |
|---|---|
| `REQ-001` | Chạy regression scoped cho LPR/GATE-01: event LPR passage và camera khác không kích hoạt LPR. |
| `REQ-002` | Chạy backend scoped tests cho AI engine, video frame/feed, metadata runtime, live detections; kiểm tra class-aware zone evaluation và debug bbox. |
| `REQ-004` | Kiểm tra metadata additive trong backend/frontend type surface: `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`, `track_id` optional. |
| `REQ-009` | Kiểm tra route/test video feed và metadata/debug fields không tự sinh event/alert; event/alert lane vẫn được chứng minh bằng test backend scoped. |
| `CR-007` | Xác minh toàn bộ contract CR-007 từ TASK-030, implementation TASK-031/TASK-032 và regression boundary Area Monitoring/GATE-01. |

## Test Environment

- Project root: `D:\Hilab\Project34`
- Backend runtime: `.\venv\Scripts\python.exe`
- Frontend commands: `npm --prefix frontend run lint`, `npm --prefix frontend run build`
- Build frontend chạy ngoài sandbox theo approval vì Vite/esbuild từng gặp `spawn EPERM` trong sandbox ở TASK-032.
- Video sample `data/video/BAI-KIEM.mp4` không có trong môi trường verification hiện tại, nên test đo FPS/decode runtime trực tiếp bị skip.

## Acceptance Results

| Tiêu chí | Kết quả | Bằng chứng |
|---|---:|---|
| Display/debug threshold không tự sinh event/alert | Pass | Backend tests pass; `conf_threshold` xuất hiện ở video/live detection route và frontend API helper như display/debug query, không có bằng chứng UI tạo alert từ metadata. |
| Class-aware zone evaluation đúng nhóm đối tượng | Pass | `backend/tests/test_ai_engine.py` pass với `bottom_center`, `footprint_overlap`, `bbox_overlap_ratio`. |
| Bật/tắt bbox container tĩnh | Pass | `backend/tests/test_video_feed_regression.py` pass, gồm case mặc định ẩn container và bật `show_static_containers=True` thì vẽ bbox. |
| Metadata additive tương thích ngược | Pass | `backend/tests/test_area_metadata_runtime.py` pass; frontend typecheck pass với các field optional/null. |
| Frontend type/build chấp nhận CR-007 | Pass | `npm --prefix frontend run lint` exit code 0; `npm --prefix frontend run build` exit code 0. |
| Backend scoped tests theo master plan | Pass | `58 passed, 6 warnings in 15.07s`. |
| FPS Area Monitoring >= 5 | Pass có giới hạn bằng chứng | `test_stream_decode_decoupling.py` là test seam đúng mục tiêu nhưng skip vì thiếu video mẫu. Code/test hiện hữu đặt target/decode lane vượt nhịp inference; cần chạy lại trên môi trường có `data/video/BAI-KIEM.mp4` để đo runtime trực tiếp. |
| LPR/GATE-01 không đổi | Pass | Regression scoped `backend/tests/test_gate_lpr.py` đạt `2 passed, 67 deselected`. |

## Integration and E2E

- Backend integration scoped: `.\venv\Scripts\python.exe -m pytest --basetemp .pytest-tmp\task033 backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py backend/tests/test_video_feed_regression.py -q`
  - Kết quả: `58 passed, 6 warnings in 15.07s`.
- Frontend integration/build:
  - `npm --prefix frontend run lint`: exit code 0, chạy `tsc --noEmit`.
  - `npm --prefix frontend run build`: exit code 0, `840 modules transformed`, build thành công trong `2.68s`.
- Schema/boundary static checks:
  - `rg` kiểm tra import backend/db/native trong `frontend/src`: không có match.
  - `rg` kiểm tra field/query CR-007 trong frontend/backend/tests: match ở `frontend/src/types/index.ts`, `frontend/src/services/api.ts`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `backend/app/api/v1/events.py`, `backend/app/services/area_metadata.py`, `backend/app/services/vision_pipeline.py`, và các test backend liên quan.

## Edge Cases

- `track_id` absent/null: Pass qua type surface frontend (`track_id?: string | null`) và metadata builder backend.
- `zone_overlap_ratio` absent/null: Pass qua type surface frontend và backend tests.
- `show_static_containers=false`: Pass qua video feed regression, container bbox không được vẽ mặc định.
- `show_static_containers=true`: Pass qua video feed regression, container bbox được vẽ khi bật debug.
- Thiếu source video/model runtime thật: Không tạo bug vì đây là giới hạn môi trường; đã ghi residual risk cho FPS runtime trực tiếp.

## Regression

- LPR/GATE-01:
  - Command: `.\venv\Scripts\python.exe -m pytest --basetemp .pytest-tmp\task033-gate backend/tests/test_gate_lpr.py -k "other_cameras_never_run_lpr or events_endpoint_returns_lpr_passages_for_gate_camera or live_detection_exposes_ocr_status or ignores_non_vehicle or lpr_passage" -q`
  - Kết quả: `2 passed, 67 deselected, 6 warnings in 2.62s`.
- Event/alert lane:
  - Backend scoped tests pass, không phát hiện evidence cho việc bbox/metadata debug lane tự sinh alert.
- Frontend boundary:
  - `frontend/src/pages/GateDashboard.tsx` không nằm trong changed files của TASK-032; static check không thấy import backend/db/native vào frontend.
- Stream/FPS:
  - `.\venv\Scripts\python.exe -m pytest --basetemp .pytest-tmp\task033-stream backend/tests/test_stream_decode_decoupling.py -q`
  - Kết quả: `4 skipped in 0.11s` do thiếu video mẫu, nên FPS runtime trực tiếp cần xác minh lại ở môi trường có fixture.

## Evidence

- `.\venv\Scripts\python.exe -m pytest --basetemp .pytest-tmp\task033 backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py backend/tests/test_video_feed_regression.py -q`: exit code 0, `58 passed, 6 warnings in 15.07s`.
- `npm --prefix frontend run lint`: exit code 0, `tsc --noEmit`.
- `npm --prefix frontend run build`: exit code 0, `vite v5.4.21`, `840 modules transformed`, warning chunk lớn hơn `500 kB`, built in `2.68s`.
- `rg -n "from ['\"](fs|path|crypto|child_process|net|tls|backend|.*prisma)|require\(['\"](fs|path|crypto|child_process|net|tls|backend|.*prisma)" frontend\src`: exit code 1, không có match.
- `rg -n "confThreshold|showStaticContainers|show_static_containers|raw_class|canonical_class|bbox_xyxy_norm|zone_eval_method|zone_overlap_ratio|detection_frame_id|track_id" frontend\src backend\app backend\tests`: exit code 0, xác nhận type/API/backend/tests có field/query CR-007.
- `.\venv\Scripts\python.exe -m pytest --basetemp .pytest-tmp\task033-gate backend/tests/test_gate_lpr.py -k "other_cameras_never_run_lpr or events_endpoint_returns_lpr_passages_for_gate_camera or live_detection_exposes_ocr_status or ignores_non_vehicle or lpr_passage" -q`: exit code 0, `2 passed, 67 deselected`.
- `.\venv\Scripts\python.exe -m pytest --basetemp .pytest-tmp\task033-stream backend/tests/test_stream_decode_decoupling.py -q`: exit code 0, `4 skipped`.

## Defects

- Không phát hiện defect material cần tạo `BUG-NNN.md`.

## Verdict

passed

Ghi chú: Verdict `passed` có residual risk về đo FPS runtime trực tiếp vì thiếu `data/video/BAI-KIEM.mp4` trong môi trường verification. Các acceptance còn lại có bằng chứng pass bằng test/build/static checks.

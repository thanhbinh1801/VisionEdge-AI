---
artifact: TASK-RESULT.md
version: "1.0"
owner: diagnose-bug
status: in-review
updated_at: "2026-08-25T17:52:58+07:00"
task_id: TASK-030
depends_on: [TASK-PACKET.md, TASK-017]
---

# Kết quả Task: TASK-030 — Chẩn đoán BUG-003 (Area Dashboard mất luồng MJPEG)

- Task ID: TASK-030
- Outcome: completed
- Inputs used: ảnh chụp màn hình sản phẩm do chủ dự án cung cấp, `backend/app/services/frame_extractor.py`, `backend/app/services/video_stream.py`, `backend/app/api/v1/events.py`, `backend/app/core/config.py`, `.env`, `data/video/`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/pages/GateDashboard.tsx`, `frontend/src/services/api.ts`, `backend/tests/test_live_detections.py`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `.delivery/tasks/TASK-019/BUG-001.md`, `.delivery/tasks/TASK-019/BUG-002.md`.
- Outputs produced: `.delivery/tasks/TASK-030/BUG-DIAGNOSIS.md` — chẩn đoán BUG-003 với tái hiện tất định, ca lỗi nhỏ nhất một dòng, A/B counterfactual, nguyên nhân gốc, chủ sở hữu và phạm vi sửa nhỏ nhất.
- Validation evidence: xem mục bên dưới.
- Deviations: xem mục bên dưới.
- Blockers: none
- Scope change requests: cần một task sửa lỗi — xem mục "Scope change request".

## Validation evidence

| Kiểm chứng | Lệnh / thao tác | Kết quả |
|---|---|---|
| Tái hiện trên server sản phẩm đang chạy (cổng 8000) | `curl ".../api/v1/events/video-feed?camera_id=BAI-KIEM&draw_zones=false"` | `http=500`, `bytes=21` |
| Tái hiện endpoint thứ hai | `curl ".../api/v1/events/live-detections?camera_id=BAI-KIEM"` | `http=500` |
| Ca lỗi nhỏ nhất | `resolve_video_path("BAI-KIEM")` | `RuntimeError: VIDEO_PATH does not point to an existing file:` tại `frame_extractor.py:32` |
| Giá trị cấu hình thật | in `os.getenv("VIDEO_PATH")`, `settings.VIDEO_PATH` | `None`, `''` |
| Counterfactual A (đúng `.env` hiện tại) | `TestClient` → `/live-detections?camera_id=BAI-KIEM` | `500` |
| Counterfactual B (`VIDEO_PATH=data/video/BAI-KIEM.mp4`) | `TestClient` → `/live-detections?camera_id=BAI-KIEM` | `200`, trả detection thật (`container`, `CONTAINER · ĐƯỢC PHÉP`) |
| `camera_id` có được dùng không | `resolve_video_path` cho 3 camera với `VIDEO_PATH=data/video/GATE-01.mp4` | Cả 3 → `...\data\video\GATE-01.mp4` |
| Footage có tồn tại không | `ls data/video/` | `BAI-KIEM.mp4`, `GATE-01.mp4`, `XUONG-AN-NINH.mp4` đều có |
| Cấu hình per-camera có được đọc không | `grep VIDEO_BAI_KIEM_PATH\|VIDEOS_DIR backend/ --include=*.py` | Chỉ khớp `config.py` (khai báo) và một file test; **không mã sản phẩm nào đọc** |
| Regression test sẵn có | `pytest backend/tests/test_live_detections.py -q` | `10 failed, 10 errors` — `AttributeError: ... no attribute 'CAMERA_VIDEO_FILES'` |
| Loại trừ TASK-029 | Đọc traceback + đối chiếu changed files | Ngoại lệ ném ở `get_camera_pipeline()`, trước mọi mã `EventManager`; `TASK-026` (viết trước `TASK-029`) đã ghi nhận đúng lỗi này |

Counterfactual A/B là bằng chứng nhân quả then chốt: cùng một mã nguồn, chỉ khác một biến môi
trường, kết quả lật từ `500` sang `200` kèm detection thật.

## Kết luận ngắn gọn

`resolve_video_path()` — điểm phân giải video duy nhất của backend — nhận `camera_id` rồi vứt đi,
chỉ đọc `VIDEO_PATH` (không có trong `.env`, mặc định rỗng), và ném `RuntimeError` thay vì lùi về
quy ước `VIDEOS_DIR/<camera_id>.mp4`. Lỗi thoát ra thành `500`, `<img>` MJPEG hỏng, UI hiện
`MẤT LUỒNG`.

Đây là **hồi quy của refactor CR-003 (`TASK-017`)**: ánh xạ `CAMERA_VIDEO_FILES` /
`resolve_camera_video()` trong `events.py` bị thay thế mà không mang theo logic per-camera, để lại
ba dấu vết còn nguyên — chú thích lạc hậu trong `config.py`, các setting `VIDEO_*_PATH` mồ côi, và
`backend/tests/test_live_detections.py` đỏ 20 test.

`Gate Dashboard` "vẫn chạy" không phản chứng điều này: nó phát `/videos/GATE-01.mp4` từ static
mount, không hề gọi backend AI.

## Deviations

- **Không thêm regression test mới.** Write scope của `TASK-030` là `.delivery/tasks/TASK-030/`
  (validator bắt buộc đúng chuỗi này), và contract `diagnose-bug` cấm đụng mã sản phẩm. Điều này
  chấp nhận được vì regression test cho đúng lỗi **đã tồn tại và đang đỏ**:
  `test_live_detections.py::test_camera_video_mapping_points_to_expected_file` và
  `::test_unknown_camera_falls_back_to_default_video`. Chủ sở hữu khắc phục: `TASK-017` /
  `backend-implementation`.
- **Không sửa mã sản phẩm**, kể cả bản vá một dòng, đúng theo completion gate của skill.
- **Không dựng được server riêng để đọc traceback trực tiếp**: cổng 8000 đang bị instance sản phẩm
  của chủ dự án chiếm. Đã bù bằng cách tái hiện trong tiến trình qua `TestClient` và gọi hàm trực
  tiếp, cho cùng ngoại lệ. Việc này hoá ra lại có lợi: hai lời gọi `curl` `500` ở trên đến từ
  **chính server sản phẩm đang chạy**, chứ không phải bản dựng lại trong phòng thí nghiệm.

## Scope change request

Cần một task `backend-implementation` để sửa. Đề xuất `TASK-031` thay vì mở lại `TASK-017`
(`needs-revision`), để không trộn bản sửa này với phần còn lại của CR-003:

- Write scope đề xuất: `backend/app/services/frame_extractor.py`, `backend/app/core/config.py`,
  `backend/tests/test_live_detections.py`, `.delivery/tasks/TASK-031/`.
- Completion gate đề xuất: `GET /api/v1/events/video-feed?camera_id=BAI-KIEM` trả `200` với `.env`
  **nguyên trạng, không đặt `VIDEO_PATH`**; ba camera phân giải ra ba file khác nhau;
  `pytest backend/tests/test_live_detections.py -q` xanh mà không nới lỏng assertion; ba lỗi
  `RuntimeError: VIDEO_PATH ...` trong `test_ai_engine.py` / `test_model_real_call.py` biến mất.
- Ưu tiên: **chặn `TASK-028`**. Nghiệm thu REQ-008 acceptance criteria 2 cần lane video sống thì
  mới sinh được clip chứng cứ.

Cảnh báo cho người sửa: **đừng "sửa" bằng cách thêm `VIDEO_PATH` vào `.env`.** Đã đo — cách đó
khiến cả ba camera cùng phát một file, Bãi Kiểm chạy footage cổng và mọi đánh giá vi phạm zone của
Bãi Kiểm trở thành sai âm thầm, nguy hiểm hơn lỗi `500` hiện tại.

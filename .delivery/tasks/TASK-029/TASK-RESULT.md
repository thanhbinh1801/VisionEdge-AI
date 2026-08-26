---
artifact: TASK-RESULT.md
version: "1.0"
owner: implement-backend
status: in-review
updated_at: "2026-08-25T15:10:00+07:00"
task_id: TASK-029
depends_on: [TASK-PACKET.md, TASK-026]
---

# Kết quả Task: TASK-029 — Nối dây `events.py` với `vision_pipeline` và Trạng thái Clip Pending

- Task ID: TASK-029
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-029/TASK-PACKET.md`, `.delivery/tasks/TASK-026/TASK-RESULT.md`, `.delivery/REQUIREMENTS.md` (REQ-008 acceptance criteria 2), `backend/app/api/v1/events.py`, `backend/app/services/event_manager.py`.
- Outputs produced: clip chứng cứ trong sản phẩm thật sự mang bbox, sinh ở thread nền không chạm hot path, kèm trạng thái `clip_status` cho client và 9 test mới.
- Changed files: `backend/app/api/v1/events.py`, `backend/app/services/event_manager.py`, `backend/tests/test_event_clip_wiring.py` (mới), `backend/tests/test_live_detections_event.py` (2 test cũ chỉnh theo hợp đồng bất đồng bộ), `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-026/*` (duyệt), `.delivery/tasks/TASK-029/*`.
- Tests changed: thêm mới `backend/tests/test_event_clip_wiring.py` (9 test); sửa 2 test trong `backend/tests/test_live_detections_event.py`.
- Blockers: none
- Scope change requests: none

## Commands run

| Lệnh | Kết quả |
|---|---|
| `.venv/Scripts/python.exe -m pytest backend/tests/test_event_clip_wiring.py -q` | `9 passed in 40.60s`, exit 0 |
| `.venv/Scripts/python.exe -m pytest backend/tests/test_event_clip_bbox.py backend/tests/test_live_detections_event.py -q` | `24 passed in 41.27s`, exit 0 — đúng lệnh bắt buộc trong constraint 4 |
| `.venv/Scripts/python.exe -m pytest backend/tests -q --ignore=backend/tests/test_live_detections.py --ignore=backend/tests/test_zone_geometry.py` | `3 failed, 100 passed in 178.34s` |

Ba lỗi còn lại là **lỗi có sẵn từ trước, không phải regression**: `test_slice_10s_ring_buffer_clip`,
`test_video_stream_service_init` và `test_model_and_video_paths_exist` đều chết ở
`RuntimeError: VIDEO_PATH does not point to an existing file:` — `VIDEO_PATH` trong `.env` để
rỗng, đúng ba lỗi mà TASK-026 đã ghi nhận. Số pass tăng đúng `91 → 100`, khớp 9 test mới.

## Đo hiệu năng (ràng buộc 1: hot path < 0.05s)

Đo thật trên `data/video/BAI-KIEM.mp4` (25 fps, clip 10s = 250 frame) với YOLO thật:

```
event_manager.slice_10s_ring_buffer_clip(..., background=True) : 0.0012s
clip_status ngay sau khi gọi                                    : processing
clip ghi xong sau                                               : 15.67s
clip_status sau khi ghi xong                                    : ready
kích thước file                                                 : 3.607.161 byte
```

`0.0012s` so với ngân sách `0.05s` — dư 40 lần. Đối chiếu với TASK-026: trước khi có Phase 5,
`_persist_violation_event` cắt clip **đồng bộ** mất `3.96s` ngay trong request `/live-detections`;
nay hot path còn `0.0012s`, tức vừa có bbox vừa nhanh hơn `~3300` lần so với trạng thái gốc.

Kiểm chứng bbox thật sự nằm trong pixel của file clip (không phải chỉ gọi hàm):

```
clip_BENCH_*.mp4: 250 frame, 250/250 frame có pixel màu bbox thuần (đỏ vi phạm / xanh hợp lệ)
```

Ngưỡng `0.05s` cũng được khoá lại bằng test tự động
(`test_persist_violation_event_keeps_hot_path_under_budget`): pipeline giả trong test cố tình
`sleep(0.05)` mỗi frame, nên ai đổi về `background=False` là test đỏ ngay thay vì để hot path âm
thầm chậm lại.

## Chi tiết thay đổi

### `backend/app/api/v1/events.py`

- `EventManager` module-level nay nhận `vision_pipeline=vision_pipeline` — dùng chung đúng
  instance với luồng stream, không nạp YOLO lần hai.
- `_persist_violation_event` gọi `slice_10s_ring_buffer_clip(..., background=True)`.
- Endpoint mới `GET /api/v1/events/{event_id}/clip-status` trả
  `{event_id, clip_status, video_clip_url}`, `404` nếu không có sự kiện.
- `EventResponse` thêm trường `clip_status`, để bảng sự kiện không phải gọi thêm một vòng
  cho từng dòng. Trường có mặc định nên không phá client cũ.

### `backend/app/services/event_manager.py`

- Hằng `CLIP_STATUS_READY / CLIP_STATUS_PROCESSING / CLIP_STATUS_MISSING`.
- `resolve_clip_path(url)` đổi `/media/clips/<file>` thành đường dẫn thật, **chỉ lấy basename**
  nên `/media/clips/../../../etc/passwd` không thoát khỏi `clips_dir` (có test chốt).
- `get_clip_status(url)` quyết định theo sổ thread nền `_pending_clips` **rồi mới** tới file:
  `cv2.VideoWriter` tạo file ngay lúc mở, nên chỉ `os.path.exists` sẽ báo `ready` cho một clip
  mới ghi được 3 frame. File tồn tại nhưng rỗng cũng bị coi là `missing`.

### Vì sao ba trạng thái chứ không hai

Packet gợi ý `ready | processing`. Đã thêm `missing` vì sự kiện cũ trong CSDL trỏ tới clip không
còn tồn tại (hoặc `video_clip_url` rỗng): trả `processing` cho những bản ghi đó nghĩa là client
quay vòng poll vĩnh viễn một file sẽ không bao giờ xuất hiện.

## Sai lệch

- **Sửa 2 test trong `test_live_detections_event.py`.** `test_persist_violation_event_writes_10s_clip_for_chatbot`
  và `test_area_metadata_violation_persistence_writes_chatbot_clip` khẳng định file clip tồn tại
  **ngay** sau khi `_persist_violation_event` trả về — điều đó đúng với hợp đồng đồng bộ cũ và
  không thể đúng với `background=True`. Đã chèn `wait_for_pending_clips(timeout=60)` trước phần
  kiểm tra file; toàn bộ assertion về nội dung clip (độ dài 10s, playable, URL) giữ nguyên. Đây là
  cập nhật test theo hợp đồng đã đổi có chủ đích, không phải nới lỏng để né lỗi, và
  `test_live_detections_event.py` nằm trong write scope của task.
- **Nhãn tiếng Việt vẫn không dấu** trên clip (`cv2.putText` + `FONT_HERSHEY_SIMPLEX`). Giữ nguyên
  theo TASK-026 Deviations và ràng buộc 2 (không thêm PIL/FreeType).

## Quan sát ngoài scope (không sửa)

`backend/app/api/v1/events.py` đang được nạp **hai lần dưới hai tên module**: `backend/main.py`
import router qua `app.api.v1.events`, còn test import `backend.app.api.v1.events`. Python coi đó
là hai module object riêng biệt, nên tồn tại **hai `AIVisionPipeline` và hai `EventManager`** —
YOLO bị nạp hai lần vào RAM/VRAM. Đây là chuyện có sẵn từ trước (cả `vision_pipeline` lẫn
`event_manager` vốn đã là biến module-level), TASK-029 không tạo ra và cũng không sửa vì nằm
ngoài write scope — chỉnh cho đúng phải đụng `backend/main.py` và `backend/app/api/router.py`.

Hệ quả thực tế: trong sản phẩm, mọi request đều đi qua `app.api.v1.events` nên vẫn nhất quán với
chính nó — clip vẫn có bbox, `clip_status` vẫn đúng. Nhưng test đi qua HTTP phải thay
`event_manager` ở **đúng bản module được mount**, nếu không route sẽ chạy manager cũ. Test
`test_event_clip_wiring.py` xử lý bằng helper `_install_event_manager()` có ghi rõ lý do, và
`test_module_event_manager_uses_the_shared_vision_pipeline` khẳng định cả hai bản module đều được
nối dây. **Đề xuất mở một task dọn dẹp riêng** để thống nhất một đường import duy nhất.

## Bao phủ test (9 test mới)

| Test | Chốt điều gì |
|---|---|
| `test_module_event_manager_uses_the_shared_vision_pipeline` | `event_manager.vision_pipeline is vision_pipeline` ở cả hai bản module — mất dòng này là clip lặng lẽ hết bbox |
| `test_persist_violation_event_slices_clip_in_background` | Vi phạm zone gọi `slice_10s_ring_buffer_clip` đúng một lần, `background=True`, đúng `source_video_path` / `source_timestamp_seconds` |
| `test_persist_violation_event_keeps_hot_path_under_budget` | Hot path `< 0.05s` với pipeline chậm 0.05s/frame; sau đó file vẫn được ghi ra thật |
| `test_get_clip_status_transitions_from_processing_to_ready` | `processing` khi thread nền đang giữ file, `ready` sau khi đóng |
| `test_get_clip_status_missing_for_unknown_or_empty_url` | `None`, chuỗi rỗng, file không tồn tại, file 0 byte → `missing` |
| `test_resolve_clip_path_does_not_escape_clips_dir` | Path traversal bị chặn |
| `test_clip_status_endpoint_reports_processing_then_ready` | Qua HTTP thật: endpoint và cả `GET /api/v1/events` cùng báo `processing`, rồi `ready` |
| `test_clip_status_endpoint_returns_404_for_unknown_event` | Sự kiện không tồn tại → 404 |
| `test_clip_status_endpoint_reports_missing_when_file_never_written` | Bản ghi có URL nhưng file chưa từng được ghi → `missing` |

## Bàn giao cho TASK-027 (frontend, Wave 3)

- `GET /api/v1/events/{event_id}/clip-status` → `{event_id, clip_status, video_clip_url}`.
- `GET /api/v1/events` mỗi phần tử nay có `clip_status`.
- Quy tắc UI: chỉ bật nút mở/tải clip khi `clip_status === "ready"`; `"processing"` thì hiện
  "Đang dựng clip…" và poll lại (~2s, clip xong sau ~15s); `"missing"` thì ẩn nút.

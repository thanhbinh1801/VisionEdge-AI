---
artifact: BUG-DIAGNOSIS.md
version: "1.0"
owner: diagnose-bug
status: in-review
updated_at: "2026-08-25T17:52:58+07:00"
task_id: TASK-030
depends_on: [TASK-PACKET.md, TASK-017]
---

# BUG-003 — `resolve_video_path()` bỏ qua `camera_id` và phụ thuộc `VIDEO_PATH` không được cấu hình, làm sập mọi endpoint video của Area Dashboard

- Severity: critical
- Affected requirements: `REQ-002`, `REQ-004`, `REQ-009`
- Affected tasks: `TASK-017` (chủ sở hữu), `TASK-018`, `TASK-019`

## Traceability

- `REQ-002` — Giám sát Khu vực & Kiểm tra Quy tắc Zone: không có frame nào tới được `AIVisionPipeline`, nên toàn bộ việc phát hiện vi phạm zone của `BAI-KIEM` và `XUONG-AN-NINH` ngừng hoạt động.
- `REQ-004` — Khử trùng lặp sự kiện & Cooldown: `_persist_violation_event` không bao giờ được gọi vì request chết trước đó, nên lane sự kiện không sinh dữ liệu mới để khử trùng lặp.
- `REQ-009` — Cảnh báo tức thì đa kênh: không có sự kiện mới thì không có cảnh báo realtime; feed "Sự kiện khu vực" trên UI chỉ còn hiển thị dữ liệu lịch sử trong CSDL.
- Nguồn hồi quy: `TASK-017` (CR-003 Area Metadata Lane) — task duy nhất viết lại `video_feed()`, `video_stream.py` và phần phân giải video trong `events.py`. `MASTER-PLAN.md` hiện để `TASK-017` ở `Status: needs-revision`.

## Reproduction

Tất định, 100% số lần. Chạy từ thư mục gốc `VisionEdge-AI/`.

**Bước 1 — trên chính server sản phẩm mà chủ dự án đang chạy (cổng 8000):**

```
$ curl -s -o /dev/null -w "http=%{http_code}\n" \
    "http://127.0.0.1:8000/api/v1/events/video-feed?camera_id=BAI-KIEM&draw_zones=false"
http=500

$ curl -s -o /dev/null -w "http=%{http_code}\n" \
    "http://127.0.0.1:8000/api/v1/events/live-detections?camera_id=BAI-KIEM"
http=500
```

Đây đúng là URL mà `AreaSecurityDashboard.tsx:170` gán vào `<img>` qua `getVideoFeedUrl()`.
`<img>` nhận `500` → phát sự kiện `onError` → `streamStatus = 'error'` → UI hiện
`MẤT LUỒNG` và `Không thể tải luồng MJPEG`. Khớp chính xác ảnh chụp màn hình.

**Bước 2 — A/B tất định trong tiến trình:**

```
### A. Không có VIDEO_PATH (đúng .env hiện tại)
live-detections -> 500

### B. VIDEO_PATH=data/video/BAI-KIEM.mp4
live-detections -> 200 [{'id': 'BAI-KIEM-1-1', 'object_class': 'container',
                         'vietnamese_name': 'Container', 'label': 'CONTAINER · ĐƯỢC PHÉP', ...
```

Expected: `200` kèm luồng `multipart/x-mixed-replace` (MJPEG) / danh sách detection.
Observed: `500 Internal Server Error`, không có byte frame nào.

## Minimal Failing Case

Không cần HTTP, không cần server, không cần YOLO — chỉ một lời gọi hàm:

```python
import sys; sys.path.insert(0, "backend")
from app.services.frame_extractor import resolve_video_path
resolve_video_path("BAI-KIEM")
```

```
RuntimeError: VIDEO_PATH does not point to an existing file:
  File "backend/app/services/frame_extractor.py", line 32, in resolve_video_path
```

Chuỗi lan lên endpoint:

```
File "backend/app/services/video_stream.py", line 164, in get_camera_pipeline
    resolved_path = os.path.abspath(video_path or resolve_video_path(camera_id))
File "backend/app/services/frame_extractor.py", line 32, in resolve_video_path
    raise RuntimeError(f"VIDEO_PATH does not point to an existing file: {env_video_path}")
```

## Evidence

**1. Resolver bỏ qua tham số `camera_id` của chính nó.** `backend/app/services/frame_extractor.py:24-32`:

```python
def resolve_video_path(camera_id: Optional[str] = None) -> str:
    env_video_path = os.getenv("VIDEO_PATH") or settings.VIDEO_PATH
    if env_video_path:
        ...
    raise RuntimeError(f"VIDEO_PATH does not point to an existing file: {env_video_path}")
```

`camera_id` được nhận rồi **không bao giờ được đọc**. Toàn bộ thân hàm chỉ phụ thuộc một biến
môi trường duy nhất.

**2. Biến đó không được cấu hình, và không có đường lùi.** Giá trị đo được:

```
os.getenv("VIDEO_PATH") = None
settings.VIDEO_PATH     = ''
```

`.env` **không** khai báo `VIDEO_PATH`; nó khai báo `VIDEOS_DIR=./data/video` và để các dòng
`VIDEO_BAI_KIEM_PATH` / `VIDEO_GATE_01_PATH` / `VIDEO_XUONG_AN_NINH_PATH` ở dạng chú thích.

**3. Footage vẫn nằm sẵn ở đúng chỗ, đúng tên camera.** `data/video/`:

```
BAI-KIEM.mp4        12.444.406 byte
GATE-01.mp4         20.483.140 byte
XUONG-AN-NINH.mp4   17.873.348 byte
```

Nghĩa là hệ thống có đủ thông tin để tự tìm ra file (`camera_id` + `VIDEOS_DIR`) nhưng resolver
không dùng gì trong số đó.

**4. Cả bề mặt cấu hình per-camera là mã chết.** `grep` toàn bộ `backend/` cho
`VIDEO_BAI_KIEM_PATH|VIDEO_GATE_01_PATH|VIDEO_XUONG_AN_NINH_PATH|VIDEOS_DIR`: chỉ khớp trong
`config.py` (nơi khai báo) và `test_live_detections.py`. **Không một dòng mã sản phẩm nào đọc
chúng.** Chú thích tại `config.py:93-94` còn viết:

> `# Ghi đè video cho từng camera; để trống thì dùng ánh xạ mặc định trong`
> `# backend/app/api/v1/events.py.`

Ánh xạ mặc định đó **không còn tồn tại** trong `events.py`.

**5. Tombstone: bộ test của ánh xạ cũ vẫn còn và vẫn đỏ.**
`backend/tests/test_live_detections.py` kiểm thử `events.CAMERA_VIDEO_FILES`,
`events.resolve_camera_video()`, `events.is_frame_usable()`, `events.SequentialFrameSource` —
những API đã bị xóa khỏi `events.py`:

```
$ .venv/Scripts/python.exe -m pytest backend/tests/test_live_detections.py -q
10 failed, 24 warnings, 10 errors in 17.01s

AttributeError: module 'backend.app.api.v1.events' has no attribute 'CAMERA_VIDEO_FILES'
  backend/tests/test_live_detections.py:142
```

Docstring của chính test đó ghi lại ý định thiết kế đã mất:
*"Mỗi camera phải trỏ vào đúng clip của nó. Đây là cái bẫy đã sập một lần…"*

**6. Lỗi này đã âm thầm hiện diện trong mọi lần chạy test gần đây.** Ba lỗi "có sẵn" mà
`TASK-026` và `TASK-029` đều ghi nhận —
`test_ai_engine.py::test_slice_10s_ring_buffer_clip`,
`test_ai_engine.py::test_video_stream_service_init`,
`test_model_real_call.py::test_model_and_video_paths_exist` — **đều chết ở đúng
`RuntimeError` này**. Chúng bị phân loại nhầm là "lỗi môi trường thiếu file" nên bị bỏ qua nhiều
task liên tiếp.

**7. Vì sao Gate Dashboard "vẫn chạy" — đây là so sánh gây hiểu nhầm.**
`frontend/src/pages/GateDashboard.tsx:20`:

```typescript
const VIDEO_SRC = '/videos/GATE-01.mp4';
```

Gate phát video từ **static mount** `/videos` của `main.py`, hoàn toàn không gọi backend AI.
Các polygon Làn IN 1 / IN 2 trong ảnh chụp được vẽ ở client. Vì vậy Gate trông "khỏe mạnh" kể cả
khi lane video của backend đã chết hoàn toàn. Chỉ `AreaSecurityDashboard` dùng
`GET /api/v1/events/video-feed`, nên chỉ nó lộ lỗi.

## Root Cause

`resolve_video_path()` trong `backend/app/services/frame_extractor.py` là **điểm phân giải video
duy nhất** của toàn bộ backend (được gọi từ `events.py` ×3, `zones.py`, `video_stream.py` ×2,
`event_manager.py`), nhưng nó bị viết thành **single-video, camera-blind, no-fallback**:

1. Nó nhận `camera_id` rồi vứt đi — mọi camera dùng chung một file.
2. Nó chỉ đọc `VIDEO_PATH`, một biến không có trong `.env` và không có giá trị mặc định
   (`config.py:110: VIDEO_PATH: str = ""`).
3. Khi biến rỗng nó **ném `RuntimeError`** thay vì lùi về quy ước `VIDEOS_DIR/<camera_id>.mp4`.

`RuntimeError` này thoát ra ngoài handler của FastAPI → `500` → `<img>` MJPEG lỗi → `MẤT LUỒNG`.

Nguyên nhân gốc là **hồi quy do refactor CR-003 (`TASK-017`)**: `events.py` trước đây có ánh xạ
`CAMERA_VIDEO_FILES` + `resolve_camera_video()` biết phân giải theo từng camera có đường lùi.
Refactor đã thay nó bằng `frame_extractor.resolve_video_path()` mà không mang theo logic ánh xạ,
lại không xóa bộ test cũ cũng không xóa cấu hình per-camera. Bằng chứng còn nguyên ở ba nơi:
chú thích lạc hậu trong `config.py`, các setting mồ côi, và `test_live_detections.py` đỏ.

**Phân biệt nguyên nhân gốc với triệu chứng:**

| Hiện tượng | Phân loại |
|---|---|
| `resolve_video_path()` mù `camera_id`, không đường lùi, ném lỗi | **Nguyên nhân gốc** |
| `500` ở `/video-feed` và `/live-detections` | Triệu chứng trực tiếp |
| `MẤT LUỒNG` / `Không thể tải luồng MJPEG` | Triệu chứng UI |
| `Metadata: CONNECTING`, `Chưa có object trong frame metadata` | Triệu chứng phụ — không có frame thì không có metadata |
| Feed "Sự kiện khu vực" chỉ có bản ghi cũ (16:07, 03:40…) | Triệu chứng phụ — lane sự kiện ngừng sinh dữ liệu mới |
| 3 test "lỗi môi trường có sẵn" trong `test_ai_engine.py` / `test_model_real_call.py` | Triệu chứng bị phân loại nhầm |
| 20 test đỏ trong `test_live_detections.py` | Triệu chứng — đồng thời là regression test sẵn có |

**Lỗi này KHÔNG do `TASK-029` gây ra.** Ngoại lệ được ném trong `get_camera_pipeline()`, xảy ra
*trước* mọi mã của `EventManager`; `_persist_violation_event` không bao giờ được chạy tới.
`TASK-029` chỉ sửa `events.py` (dòng khởi tạo + endpoint clip-status), `event_manager.py` và
tests — không chạm `frame_extractor.py` hay `video_stream.py`. `TASK-026`, viết **trước**
`TASK-029`, đã ghi nhận đúng `RuntimeError` này trong TASK-RESULT của nó.

## Ownership

- **Capability sở hữu:** `backend-implementation`.
- **Task sở hữu:** `TASK-017` — Backend Area Metadata Lane và Zone Cache (CR-003). Write scope
  `backend/app/`, `backend/tests/` đã bao trọn các file cần sửa; `MASTER-PLAN.md` đang để task
  này ở `Status: needs-revision`, nên đây là nơi tự nhiên để tiếp nhận bản sửa.
- **Task bị ảnh hưởng:** `TASK-018` (Area Dashboard tiêu thụ lane metadata — không hiển thị được),
  `TASK-019` (verification CR-003 — đã bỏ lọt lỗi này), `TASK-028` (nghiệm thu REQ-008 sắp tới sẽ
  không lấy được clip nếu lane video còn chết).

## Regression Test

**Không viết test mới trong task này** — write scope của `TASK-030` là `.delivery/tasks/TASK-030/`,
mã nguồn `backend/tests/` nằm ngoài phạm vi, và contract của `diagnose-bug` cấm sửa mã sản phẩm.

**Không cần seam mới:** regression test cho đúng lỗi này **đã tồn tại và đang đỏ**:
`backend/tests/test_live_detections.py::test_camera_video_mapping_points_to_expected_file` và
`::test_unknown_camera_falls_back_to_default_video` khẳng định chính xác hành vi đã mất (ánh xạ
per-camera + đường lùi mặc định). Hiện chúng thất bại với
`AttributeError: ... has no attribute 'CAMERA_VIDEO_FILES'`.

- Trạng thái: **đã có, đang thất bại (20 test đỏ trong `test_live_detections.py`)**.
- Chủ sở hữu khắc phục: `TASK-017` / capability `backend-implementation`.
- Điều kiện nghiệm thu bản sửa: `.venv/Scripts/python.exe -m pytest backend/tests/test_live_detections.py -q`
  chuyển sang xanh **mà không nới lỏng assertion**, và ba test trong `test_ai_engine.py` /
  `test_model_real_call.py` cũng phải hết `RuntimeError: VIDEO_PATH ...`.
- Khuyến nghị bổ sung một test cấp API chốt `GET /api/v1/events/video-feed?camera_id=BAI-KIEM`
  trả `200` khi `VIDEO_PATH` **không** được đặt — vì đó chính là cấu hình sản phẩm đang chạy và
  hiện không có test nào phủ.

## Recommended Fix Scope

Nhỏ nhất, tập trung vào một hàm:

1. **`backend/app/services/frame_extractor.py::resolve_video_path()`** — cho hàm này thực sự dùng
   `camera_id`, theo thứ tự ưu tiên:
   1. `VIDEO_PATH` (giữ nguyên, để không phá test/kịch bản ghi đè hiện có),
   2. setting per-camera `VIDEO_<CAMERA_ID>_PATH` đã khai báo sẵn trong `config.py`,
   3. quy ước `VIDEOS_DIR/<camera_id>.mp4` — đường lùi khiến cấu hình mặc định chạy được ngay,
   4. chỉ ném `RuntimeError` khi đã thử hết mà không thấy file, và thông điệp phải nêu các đường
      dẫn đã thử (thông điệp hiện tại kết thúc bằng chuỗi rỗng nên vô dụng khi truy lỗi).
2. **`backend/app/core/config.py:93-94`** — sửa chú thích đang trỏ tới ánh xạ không còn tồn tại
   trong `events.py`.
3. **`backend/tests/test_live_detections.py`** — cập nhật theo API mới của resolver; giữ nguyên ý
   định của hai test ánh xạ per-camera thay vì xóa chúng.
4. Cân nhắc trả `503` kèm thông điệp tiếng Việt thay vì `500` trần khi thật sự không tìm được
   footage, để UI phân biệt được "chưa cấu hình video" với "backend sập" — `video_feed()` đã có
   tiền lệ `503` cho trường hợp không lấy được frame đầu tiên.

**Không** nên sửa bằng cách thêm `VIDEO_PATH=data/video/BAI-KIEM.mp4` vào `.env`. Cách đó làm UI
hết báo lỗi nhưng khiến **cả ba camera cùng phát một file**: đã đo, với
`VIDEO_PATH=data/video/GATE-01.mp4` thì `BAI-KIEM`, `GATE-01`, `XUONG-AN-NINH` đều trả về
`...\data\video\GATE-01.mp4`. Bãi Kiểm sẽ chạy footage cổng, và mọi đánh giá vi phạm zone của
Bãi Kiểm sẽ áp polygon của bãi lên hình ảnh cổng — sai âm thầm, nguy hiểm hơn lỗi 500 hiện tại.

## Open Questions

1. `VIDEO_PATH` có còn là bề mặt cấu hình được mong muốn không, hay nên bỏ hẳn để chỉ còn
   `VIDEOS_DIR` + `VIDEO_<CAMERA>_PATH`? Câu trả lời quyết định bước 1 giữ 4 tầng ưu tiên hay
   rút còn 3.
2. `resolve_video_path()` nên xử lý thế nào với `camera_id` lạ? Test cũ
   (`test_unknown_camera_falls_back_to_default_video`) mong đợi lùi về `DEFAULT_VIDEO_FILE`; cần
   chủ dự án xác nhận hành vi đó còn đúng, hay nên báo lỗi rõ ràng.
3. Bản sửa nên nằm trong `TASK-017` (đang `needs-revision`) hay tách một task mới ở Phase 5? Đề
   xuất: tách task mới, vì `TASK-017` đã đóng phần lớn phạm vi CR-003 và việc mở lại sẽ trộn hai
   nhóm thay đổi không liên quan.
4. Vì sao `TASK-019` (verification CR-003) không bắt được lỗi này? Đáng rà lại completion gate của
   nó — hiện có vẻ không có bước nào thực sự tải luồng MJPEG và kiểm tra mã trạng thái.

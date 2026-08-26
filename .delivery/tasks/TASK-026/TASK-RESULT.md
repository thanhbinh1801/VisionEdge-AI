---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-026
owner: implement-backend
status: approved
updated_at: "2026-08-25T15:10:00+07:00"
---

# Kết quả Task: TASK-026 - BBox Bám Frame trong Clip Chứng cứ 10s

- Task ID: TASK-026
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-026/TASK-PACKET.md`, `.delivery/REQUIREMENTS.md` (REQ-008 acceptance criteria 2), `backend/app/services/event_manager.py`, `backend/app/services/vision_pipeline.py`, `backend/app/api/v1/events.py` (chỉ đọc để xác định caller).
- Outputs produced: `EventManager` vẽ bbox bám đối tượng vào clip chứng cứ với tần suất suy luận giãn theo `detect_stride`, kèm chế độ sinh clip bất đồng bộ để không chặn hot path, và 12 test bao phủ.
- Changed files: `backend/app/services/event_manager.py`, `backend/tests/test_event_clip_bbox.py`.
- Tests changed: thêm mới `backend/tests/test_event_clip_bbox.py` với 12 test.
- Commands run: `.venv/Scripts/python.exe -m pytest backend/tests/test_event_clip_bbox.py -q` (`12 passed in 2.77s`, exit 0, đạt ngay lượt đầu); `.venv/Scripts/python.exe -m pytest backend/tests -q --ignore=backend/tests/test_live_detections.py --ignore=backend/tests/test_zone_geometry.py` (`3 failed, 91 passed in 178.15s`, exit 1 — đúng 3 lỗi có sẵn từ trước, số pass tăng 79 → 91 khớp 12 test mới).
- Validation evidence: xem mục "Đo hiệu năng" bên dưới. Kiểm chứng bbox nằm trong pixel của file clip bằng cách so sánh frame giữa clip có và không có pipeline (`test_pipeline_draws_bbox_into_clip_pixels`), nên clip tải về mang sẵn hộp đúng như acceptance criteria 2 đòi hỏi.
- Deviations: xem mục "Sai lệch" bên dưới.
- Blockers: none
- Scope change requests: cần một task nối dây `events.py` — xem mục "Scope change request".

## Đo hiệu năng (bắt buộc theo completion gate)

Đo thật trên `data/video/BAI-KIEM.mp4` (25 fps, clip 10s = 250 frame), YOLO thật:

```
TRƯỚC (không bbox, đồng bộ)          :  3.96s
SAU   (bbox stride=5, đồng bộ)       : 15.18s
SAU   (bbox stride=5, nền)           : request trả về sau 0.002s | clip xong sau 14.31s
inference/frame                      : 0.219s (min 0.189 / max 0.275)
```

Phương án ban đầu — suy luận mỗi frame — đã được đo và **loại bỏ trước khi viết code**: 250 suy luận cho `+49.6s`, tổng `53.7s` mỗi clip. Vì `slice_10s_ring_buffer_clip` chạy đồng bộ trong `_persist_violation_event` ([events.py:110](../../../backend/app/api/v1/events.py)) tức nằm trong request `/live-detections` mà client poll mỗi 2s, một vi phạm đầu tiên sẽ khoá request ~54 giây. Cooldown 15s không cứu được vì nó chỉ chặn sự kiện trùng lặp. Theo đúng completion gate, đã dừng và báo cáo phương án thay vì âm thầm làm chậm hot path; chủ dự án chọn hướng bất đồng bộ + `stride=5`.

Kết quả đáng chú ý: ở chế độ nền, hot path giảm từ `3.96s` xuống `0.002s`, tức **nhanh hơn cả trạng thái trước khi có bbox**, vì bản gốc vốn đã chặn request gần 4 giây để cắt clip.

## Chi tiết thay đổi

- `EventManager.__init__` nhận thêm `vision_pipeline` và `detect_stride` (mặc định 5, kẹp tối thiểu 1). Không truyền `vision_pipeline` thì hành vi giữ nguyên hoàn toàn: không suy luận, không bbox.
- `_write_mp4_clip` suy luận mỗi `detect_stride` frame và giữ nguyên hộp giữa hai lần, vẽ `cv2.rectangle` cùng nhãn tiếng Việt và độ tin cậy. Màu đỏ cho vi phạm zone, xanh cho hợp lệ.
- `slice_10s_ring_buffer_clip(..., background=True)` sinh clip trong thread nền và trả URL ngay; `_spawn_clip_writer` bảo đảm mỗi file chỉ một thread.
- `wait_for_pending_clips(timeout)` để test và tiến trình tắt máy chờ clip nền ghi xong.
- Lỗi suy luận một frame bị nuốt có ghi log thay vì ném lên: thà clip không có hộp còn hơn mất luôn bằng chứng.

## Sai lệch

- **`vision_pipeline` mặc định là `None`, nên clip trong sản phẩm hiện vẫn chưa có bbox.** Đây là lựa chọn có chủ đích chứ không phải bỏ sót: bật mặc định sẽ (a) làm hỏng `test_slice_10s_ring_buffer_clip` và `test_slice_10s_ring_buffer_clip_clamps_near_source_start` của đồng đội — hai file test đó nằm ngoài write scope nên tôi không được sửa, và (b) đẩy hot path đồng bộ lên 15.18s. Việc nối dây thuộc scope change request bên dưới.
- Nhãn tiếng Việt vẽ bằng `cv2.putText` với `FONT_HERSHEY_SIMPLEX`, font này **không có glyph tiếng Việt có dấu** nên "Xe tải" sẽ hiện thiếu dấu trên clip. Sửa đúng cần vẽ bằng PIL/FreeType, tức thêm dependency — vượt write scope và cần CR riêng. Hộp bbox và màu sắc không bị ảnh hưởng.

## Scope change request

**Cần một task nối dây `backend/app/api/v1/events.py`** để clip trong sản phẩm thực sự có bbox:

- Truyền `vision_pipeline` vào `EventManager(...)` tại chỗ khởi tạo module-level.
- Gọi `slice_10s_ring_buffer_clip(..., background=True)` trong `_persist_violation_event`.
- Xử lý khoảng trống ~14s giữa lúc bản ghi sự kiện có `video_clip_url` và lúc file tồn tại: hiện `video_clip_url` được ghi thẳng vào CSDL, nên nếu người dùng mở clip sớm sẽ gặp 404. Cần trạng thái "clip đang xử lý" ở API và UI.

`events.py` nằm ngoài write scope của TASK-026 (`backend/app/services/event_manager.py`, `backend/tests/test_event_clip_bbox.py`). Phase 5 hiện cũng **chưa có task nào** phủ việc này: TASK-027 chỉ ghi `frontend/src/...`, TASK-028 là verification. Nếu không bổ sung, TASK-028 sẽ trượt vì clip sản phẩm không có bbox.

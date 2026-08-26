---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: approved
updated_at: "2026-08-25T15:10:00+07:00"
task_id: TASK-029
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md, TASK-026]
---

# TASK-029 Nối dây `events.py` với `vision_pipeline` và Trạng thái Clip Pending

- Task ID: TASK-029
- Task type: implementation
- Scope: feature
- Module: event-clip-manager
- Capability: backend-implementation
- Linked requirements: REQ-008 (acceptance criteria 2), CR-002
- Dependencies: TASK-026
- Phase / Wave: Phase 5 / Wave 2
- Inputs: `.delivery/tasks/TASK-026/TASK-RESULT.md` (mục "Scope change request"), `.delivery/REQUIREMENTS.md` (REQ-008 acceptance criteria 2), `backend/app/api/v1/events.py`, `backend/app/services/event_manager.py`
- Expected outputs: `backend/app/api/v1/events.py`, `backend/app/services/event_manager.py`, `backend/tests/test_event_clip_wiring.py`, `.delivery/tasks/TASK-029/TASK-RESULT.md`
- Write scope: `backend/app/api/v1/events.py`, `backend/app/services/event_manager.py`, `backend/tests/test_event_clip_wiring.py`, `backend/tests/test_live_detections_event.py`, `.delivery/tasks/TASK-029/`
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

## Bối cảnh

`TASK-026` đã dạy `EventManager` vẽ bbox bám đối tượng vào clip chứng cứ 10s (`stride=5`,
`background=True`, hot path 0.002s, 12 test pass). Nhưng `events.py` vẫn khởi tạo
`EventManager` với `vision_pipeline=None` mặc định và vẫn cắt clip đồng bộ, nên **trong sản
phẩm thật clip vẫn không có bbox** — đúng sai lệch mà TASK-026 tự ghi nhận và xin task nối dây.
Không có task này thì `TASK-028` chắc chắn trượt acceptance criteria 2.

Nối dây xong lại lộ ra vấn đề thứ hai: bản ghi sự kiện có `video_clip_url` ngay lúc phát hiện
vi phạm, nhưng file chỉ ghi xong sau ~14s. Client mở clip trong khoảng trống đó sẽ vấp 404 hoặc
file rỗng, nên API phải nói rõ clip đang render.

## Việc phải làm

1. **Nối dây `events.py`**
   - Truyền `vision_pipeline` (instance module-level đang dùng chung cho stream) vào
     `EventManager` lúc khởi tạo module-level.
   - `_persist_violation_event` gọi `slice_10s_ring_buffer_clip(..., background=True)`.
2. **Trạng thái clip pending**
   - Bổ sung cơ chế cho client biết clip đã ghi xong chưa: endpoint
     `GET /api/v1/events/{event_id}/clip-status` và/hoặc trường `clip_status`
     (`ready` | `processing` | `missing`) trong response sự kiện.
   - Helper kiểm tra trạng thái file đặt ở `EventManager` (nơi giữ sổ thread nền), không đặt ở
     router.
3. **Test bao phủ** trong `backend/tests/test_event_clip_wiring.py`
   - Vi phạm zone → `slice_10s_ring_buffer_clip` được gọi với `background=True` và
     `vision_pipeline` thật sự được gắn vào `event_manager`.
   - Endpoint trả `processing` khi file chưa xong và `ready` khi đã ghi xong.

## Ràng buộc

1. **Hiệu năng — không chặn hot path.** Cấm gọi `slice_10s_ring_buffer_clip` với
   `background=False` hoặc `stride=1` trong request cycle của `events.py`. Phần ghi sự kiện của
   `/live-detections` phải giữ dưới `0.05s`, và phải chứng minh bằng số đo.
2. **Không thêm dependency.** Nhãn tiếng Việt không dấu qua `cv2.putText` đã được chấp nhận ở
   TASK-026 Deviations; không cài PIL/FreeType hay thư viện nặng ngoài `requirements.txt`.
3. **Write scope.** Chỉ backend + artifacts như liệt kê trên. **Không** sửa `frontend/src/...`
   (thuộc TASK-027, Wave 3).
4. **Chạy test từ gốc `VisionEdge-AI/`:**
   `.venv/Scripts/python.exe -m pytest backend/tests/test_event_clip_bbox.py backend/tests/test_live_detections_event.py -q`
   Không được làm regression `test_slice_10s_ring_buffer_clip` và
   `test_live_detections_event.py`.
5. **Artifact.** `TASK-PACKET.md` + `TASK-RESULT.md` đầy đủ bằng chứng đo đạc và kiểm thử trước
   khi báo hoàn thành.

## Completion gate

`EventManager` module-level trong `events.py` nhận `vision_pipeline` và `_persist_violation_event`
gọi `slice_10s_ring_buffer_clip(..., background=True)`, chứng minh bằng đo đạc rằng phần ghi sự
kiện của `/live-detections` giữ dưới 0.05s. API cho client biết clip đang render qua `clip_status`
(`ready` / `processing` / `missing`) để không tải sớm gặp file rỗng. Không thêm dependency mới và
không sửa `frontend/src/`.

## Verification method

```
.venv/Scripts/python.exe -m pytest backend/tests/test_event_clip_wiring.py backend/tests/test_event_clip_bbox.py backend/tests/test_live_detections_event.py -q
```

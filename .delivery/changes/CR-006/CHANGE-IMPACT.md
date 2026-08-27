---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: in-review
updated_at: "2026-08-27T11:02:50+07:00"
change_id: CR-006
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, API-CONTRACT.md, MASTER-PLAN.md]
---

# Đánh giá Ảnh hưởng Thay đổi cho CR-006

## Change Summary

- Business delta: Luồng video của cả giám sát cổng (`GATE-01`) và giám sát khu vực (`BAI-KIEM`, `XUONG-AN-NINH`) phải hiển thị gần thời gian thực. Suy luận AI không được nằm trên đường tới hạn của việc hiển thị khung hình. Cổng chuyển sang dùng chung lane MJPEG với khu vực để bounding box và pixel luôn thuộc cùng một frame.
- Affected requirements: `REQ-001`, `REQ-002`, `REQ-004`, `REQ-009`, Global Acceptance Criteria #1
- Baseline note: Theo tiền lệ CR-005, CR-006 hiện chỉ được ghi nhận trong artifact impact này; chưa cập nhật `.delivery/REQUIREMENTS.md`. Cần Product Owner duyệt trước khi sửa baseline.
- Script execution note: `assess_change_impact.py` chưa được chạy vì script yêu cầu CR phải tồn tại sẵn trong `REQUIREMENTS.md`, mà baseline chưa được phép sửa ở bước này. Closure dưới đây được lập thủ công từ MASTER-PLAN v2.3.0 và trạng thái thực tế của `TASK-RESULT.md`.

## Đo lường baseline (bằng chứng khởi phát)

Đo trên máy phát triển hiện tại, model `sentri-yolo11s.pt`, frame `1274x720` từ `data/video/BAI-KIEM.mp4`:

```
torch 2.13.0+cpu   ·   CUDA available: False   ·   device count: 0
imgsz=640 -> 291 ms/frame -> 3.4 FPS
imgsz=480 -> 212 ms/frame -> 4.7 FPS
imgsz=384 -> 183 ms/frame -> 5.5 FPS
```

Vì `CameraFramePipeline._run()` gọi `vision_pipeline.process_frame()` đồng bộ ngay trong vòng decode
(`backend/app/services/video_stream.py:128`), toàn bộ stream khu vực bị khóa ở nhịp suy luận là **3.4 FPS**.
Đây là mức **dưới** Global Acceptance Criteria #1 (`FPS >= 5`) trong `.delivery/REQUIREMENTS.md`.

## Direct Impact

- `REQ-001` — affected — Gate Dashboard đổi cơ chế hiển thị từ `<video>` phát file cục bộ cộng polling REST sang lane MJPEG dùng chung. Acceptance #3 (`< 1 giây`) lần đầu tiên có cách đo được xác định.
- `REQ-002` — affected — `video stream lane` của giám sát khu vực phải chạy độc lập nhịp với `realtime metadata lane`; metadata snapshot bổ sung ngữ nghĩa "tuổi của detection".
- `REQ-004` — uncertain — dedup/cooldown giữ nguyên ngữ nghĩa, nhưng khi OCR và persist chuyển xuống luồng nền, nguồn gọi `_persist_violation_event` và `persist_gate_lpr_events` thay đổi. Cần xác nhận cooldown vẫn tính trên đúng một nguồn duy nhất.
- `REQ-009` — uncertain — alert lane không đổi ngữ nghĩa, nhưng `TASK-014` chưa triển khai và cũng ghi vào `backend/app/api/v1/websocket.py`. Hai luồng công việc không được chạy song song.
- Global Acceptance Criteria #1 — affected — mốc `FPS >= 5` hiện đang fail; CR-006 là công việc đưa nó về đạt.
- `.delivery/ARCHITECTURE.md` — affected — ranh giới `ai-vision-pipeline` cần thể hiện decode và inference là hai nhịp tách rời, không còn là một vòng lặp tuần tự.
- `.delivery/API-CONTRACT.md`, `docs/contracts/api/websocket-events.json` — affected — payload metadata bổ sung trường tuổi detection; `GET /events/live-detections` bị khai tử cho `GATE-01`.

## Khoảng trống NFR phải lấp trước khi có completion gate

Hiện `.delivery/REQUIREMENTS.md` **không có bất kỳ NFR độ trễ nào** cho luồng khu vực. Đây chính là lý do
không task nào trong MASTER-PLAN sở hữu việc tối ưu này: không có điều kiện quan sát được để làm
`Completion gate`. CR-006 phải chốt số đo trước, nếu không sẽ không nghiệm thu được.

Đề xuất để Product Owner duyệt:

- Video khu vực và cổng: `>= 15 FPS` hiển thị với 2 client đồng thời.
- Metadata lane: p95 độ trễ publish `<= 200 ms`.
- Suy luận: `>= 4.5 FPS` (đạt được với `imgsz=480` theo đo lường trên).
- Tuổi detection hiển thị trên UI: `<= 500 ms` ở điều kiện bình thường.

## Transitive Task Impact

- `TASK-001` — module `none` — status `ready` — impact `affected` — benchmark gốc chọn stack theo mốc `FPS >= 5` nhưng số đo hiện tại là 3.4 FPS; `docs/reports/ai-model-benchmark.md` cũng không tồn tại trên đĩa. Packet action `owner-decision-required`.
- `TASK-002` — module `none` — status `ready` — impact `affected` — API foundation phải phản ánh việc bỏ `live-detections` cho cổng và bổ sung trường tuổi detection. Packet action `invalidate-automatically`.
- `TASK-003` — module `none` — status `ready` — impact `unaffected` — không đổi schema CSDL.
- `TASK-004` — module `none` — status `ready` — impact `unaffected` — UI/UX foundation không đổi.
- `TASK-005` — module `none` — status `ready` — impact `unaffected` — scaffolding không đổi.
- `TASK-006` — module `database-storage` — status `ready` — impact `uncertain` — luồng nền cần Session CSDL riêng để chạy OCR/persist; cần xác nhận `SessionLocal` an toàn khi dùng từ thread nền. Packet action `owner-decision-required`.
- `TASK-007` — module `ai-vision-pipeline` — status `ready` — impact `affected` — `process_frame()` nhận thêm tham số `imgsz`; `BUG-001` (nhận nhầm cột điện thành `Xe cẩu`) vẫn `open` và việc hạ `imgsz` có thể làm đổi biểu hiện của nó. Packet action `invalidate-automatically`.
- `TASK-008` — module `web-ui` — status `ready` — impact `unaffected` — shared components không đổi.
- `TASK-009` — module `web-ui` — status `ready` — impact `affected` — Gate Dashboard bỏ `<video>` và polling, chuyển sang MJPEG. Sở hữu `BUG-001` lệch đồng bộ bounding box. Packet action `invalidate-automatically`.
- `TASK-010` — module `web-ui` — status `blocked` — impact `uncertain` — Area Dashboard giữ MJPEG làm nguồn bbox duy nhất nên không đổi hợp đồng, nhưng task đang blocked vì thiếu packet. Packet action `owner-decision-required`.
- `TASK-012` — module `web-ui` — status `blocked` — impact `affected` — ghi cùng `backend/app/api/v1/events.py` (tham số `draw_zones`) với CR-006. Packet action `owner-decision-required`.
- `TASK-013` — module `llm-qa-agent` — status `ready` — impact `unaffected` — chatbot không đụng stream lane.
- `TASK-014` — module `alert-dispatcher` — status `ready` — impact `affected` — chưa triển khai, và ghi cùng `backend/app/api/v1/websocket.py`. **Không được chạy song song với CR-006.** Packet action `invalidate-automatically`.
- `TASK-015` — module `none` — status `ready` — impact `affected` — E2E chưa từng chạy; phải bổ sung case đo FPS/độ trễ. Packet action `invalidate-automatically`.
- `TASK-016` — module `api-gateway` — status `approved` — impact `affected` — contract metadata lane cần bổ sung trường tuổi detection. Packet action `owner-decision-required`.
- `TASK-017` — module `ai-vision-pipeline` — status `approved` — impact `affected` — sở hữu `video_stream.py` và zone cache; CR-006 sửa trực tiếp vòng decode mà task này đã nghiệm thu. Packet action `owner-decision-required`.
- `TASK-018` — module `web-ui` — status `in-review` — impact `uncertain` — Area Dashboard cần xử lý trường tuổi detection nếu UI phải làm mờ bbox quá hạn. Packet action `owner-decision-required`.
- `TASK-019` — module `none` — status `approved` — impact `affected` — verification CR-003 khẳng định hot path không đọc DB mỗi frame; CR-006 đổi cấu trúc hot path nên phải chạy lại. Packet action `owner-decision-required`.
- `TASK-020` đến `TASK-025` — module `database-storage` / `api-gateway` / `web-ui` — status `approved` hoặc `in-review` — impact `unaffected` — CR-004 object labeling không liên quan stream lane.
- `TASK-026`, `TASK-027`, `TASK-028` — module `api-gateway` / `alert-dispatcher` — status `approved` hoặc `in-review` — impact `uncertain` — Telegram evidence lấy input từ event lane; nếu persist chuyển xuống nền thì đường gọi tới `send_telegram_notification_sync` đổi. Packet action `owner-decision-required`.
- `TASK-029` — module `llm-qa-agent` — status `in-review` — impact `unaffected` — Gemini Text-to-SQL không liên quan.

## Unaffected Evidence

- `REQ-005`, `REQ-006`, `REQ-007` không đổi: cấu hình zone, nhãn xe quen/lạ và dataset labeling không nằm trên đường tới hạn hiển thị.
- `REQ-008` không đổi: AI Assistant truy vấn dữ liệu đã lưu, không đọc stream.
- Toàn bộ dải CR-004 (`TASK-020` đến `TASK-025`) không cần khóa.
- Schema CSDL không đổi; CR-006 không sinh migration.

## Selective Lock

- Lock artifacts: `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/websocket-events.json`, `docs/contracts/api/api-schema.json`.
- Lock modules: `ai-vision-pipeline` (`video_stream.py`, `vision_pipeline.py`), `api-gateway` phần `events.py` và `websocket.py`, `web-ui` phần `GateDashboard.tsx` và `AreaSecurityDashboard.tsx`.
- Do not lock: `database-storage` schema, `llm-qa-agent`, toàn bộ dataset/object-labeling của CR-004, `alert_dispatcher.py`.

## Packet Actions

- `invalidate-automatically`: `TASK-002`, `TASK-007`, `TASK-009`, `TASK-014`, `TASK-015` vì đang `ready`/chưa triển khai và bị ảnh hưởng trực tiếp.
- `owner-decision-required`: `TASK-001`, `TASK-006`, `TASK-010`, `TASK-012`, `TASK-016`, `TASK-017`, `TASK-018`, `TASK-019`, `TASK-026`, `TASK-027`, `TASK-028` vì đã approved, blocked hoặc in-review; không được tự đánh dấu stale.
- `no-action`: mọi task được phân loại `unaffected` ở trên.

## Owner Decisions Required

- Chốt bộ số NFR độ trễ/FPS ở mục "Khoảng trống NFR" để CR-006 có completion gate đo được.
- Xác nhận việc mất khả năng tua/pause video ở tab cổng là chấp nhận được khi chuyển sang MJPEG. *(Đã chốt: chấp nhận.)*
- Xác nhận `imgsz=480` là mức đánh đổi độ chính xác được duyệt. *(Đã chốt: 640 → 480, giữ `yolo11s`.)*
- Quyết định `TASK-017` và `TASK-019` (đã approved) được reopen, hay CR-006 sinh task mới kế thừa.
- Quyết định thứ tự giữa CR-006 và `TASK-014`, vì cả hai ghi vào `backend/app/api/v1/websocket.py`.
- Xác nhận `TASK-007/BUG-001` (`open`, nhận nhầm cột điện thành `Xe cẩu`) được xử lý trước hay sau khi hạ `imgsz`, vì thay đổi độ phân giải suy luận sẽ làm đổi biểu hiện của bug đó.

## Update Order

1. Product Owner duyệt hoặc chỉnh `.delivery/changes/CR-006/CHANGE-IMPACT.md`, đặc biệt là bộ số NFR.
2. Cập nhật `.delivery/REQUIREMENTS.md`: thêm audit trail CR-006 và NFR độ trễ cho `REQ-001`, `REQ-002`.
3. Cập nhật `.delivery/ARCHITECTURE.md` cho ranh giới decode/inference tách nhịp.
4. Cập nhật `.delivery/API-CONTRACT.md` và schema cho trường tuổi detection, và cho việc khai tử `live-detections` ở cổng.
5. Áp dụng packet actions và các quyết định chủ dự án.
6. Chỉ sau khi duyệt mới cập nhật `MASTER-PLAN.md` và triển khai.

## Validation Plan

- Traceability: CR-006 ánh xạ tới `REQ-001`, `REQ-002`, `REQ-004`, `REQ-009` và Global AC #1.
- Baseline verification: chạy lại script đo trước/sau; số liệu "trước" đã ghi ở mục đo lường trên.
- Backend verification: `python -m pytest backend/tests -q` giữ nguyên 156 passed; bổ sung test khẳng định vòng decode publish frame mà không chờ inference.
- Regression verification: `test_area_metadata_runtime.py`, `test_video_feed_regression.py`, `test_gate_lpr.py`, `test_live_detections_event.py` phải pass.
- Sync verification: với `GATE-01`, bounding box và pixel phải thuộc cùng `frame_id` — kiểm bằng header `X-Frame-Id` của MJPEG.
- Frontend verification: `npx tsc --noEmit` và `npm run build` pass.

## Liên quan

- `.delivery/tasks/TASK-009/BUG-001.md` — lệch đồng bộ bounding box ở tab cổng, là bằng chứng khởi phát cho quyết định chuyển cổng sang MJPEG.
- `.delivery/tasks/TASK-007/BUG-001.md` — `open`, chịu ảnh hưởng khi hạ `imgsz`.
- `.delivery/tasks/TASK-007/BUG-002.md` — `fixed`, quyết định đặt OCR trong `live-detections` của bug này bị CR-006 đảo ngược.

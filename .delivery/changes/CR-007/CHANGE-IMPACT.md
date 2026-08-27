---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: approved
updated_at: "2026-08-27T00:00:00+07:00"
change_id: CR-007
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, API-CONTRACT.md, MASTER-PLAN.md]
---

# Đánh giá Ảnh hưởng Thay đổi cho CR-007

## Change Summary

- Business delta: Area Monitoring phải dùng đúng mô hình chính YOLOv11s finetune cho `BAI-KIEM`, đồng bộ ngưỡng nhận diện giữa inference/metadata/MJPEG, lọc detection theo class rõ ràng, đánh giá zone theo hình học phù hợp từng loại đối tượng thay vì chỉ dùng tâm bbox, và cho phép bật bbox container để debug mà không thay đổi luồng LPR/cổng.
- Affected requirements: `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`, Global Acceptance Criteria #1.
- Scope in: detection filtering, per-class confidence thresholds, metadata debug additive fields, zone evaluation geometry, MJPEG bbox renderer, `show_static_containers` query param, and tracking readiness fields.
- Scope out: LPR/biển số/cổng business flow, YOLO-World prompt engineering, thay model chính khỏi YOLOv11s finetune, triển khai tracking ByteTrack/BoT-SORT đầy đủ trong CR này.
- Baseline note: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, và `MASTER-PLAN.md` vẫn còn nhiều chỗ ghi YOLOv26/YOLO-World/point-in-polygon center. CR-007 cần Product Owner duyệt trước khi cập nhật baseline để phản ánh trạng thái mới YOLOv11s finetune.
- Script execution note: `assess_change_impact.py` đã được chạy và dừng với lỗi `ERROR: CR-007 is not declared in REQUIREMENTS.md`, vì script yêu cầu CR tồn tại trong baseline requirements trong khi artifact này đang là bước đề xuất/in-review và chưa được phép sửa `.delivery/REQUIREMENTS.md`. Closure dưới đây được lập thủ công từ artifact hiện có và kiểm tra codebase ngày 2026-08-27.

## Current Code Findings

- `backend/app/core/config.py` đã có `DETECTION_MODEL_WEIGHTS = "sentri-yolo11s.pt"` và `DETECTION_CONFIDENCE_THRESHOLD = 0.30`, nhưng `/api/v1/events/video-feed` trong `backend/app/api/v1/events.py` vẫn mặc định `conf_threshold=0.50`.
- `CameraFramePipeline` trong `backend/app/services/video_stream.py` đã tách decode/inference thread và mặc định `inference_threshold=0.35`, nên video lane gần realtime là baseline cần bảo vệ.
- `AIVisionPipeline.process_frame()` trong `backend/app/services/vision_pipeline.py` truyền thẳng `conf_threshold` xuống `model.predict()` rồi lọc lại cùng ngưỡng; chưa có tầng inference thấp hơn cộng application per-class thresholds.
- `evaluate_bbox_center_in_zone()` trong `backend/app/services/vision_pipeline.py` đang dùng tâm bbox cho mọi class; nhược điểm lớn với container/xe tải/xe cẩu/xe dài đã được xác nhận trong phạm vi CR.
- `backend/app/api/v1/events.py` hard-code `_MJPEG_HIDDEN_BBOX_CLASSES = {"container"}` và không có query param để bật bbox container khi debug model.
- `backend/app/services/area_metadata.py` đang giữ contract `bbox` normalized xyxy cho metadata, nhưng chưa có `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, hoặc `detection_frame_id` trong object metadata.
- `frontend/src/pages/AreaSecurityDashboard.tsx` lấy MJPEG từ `getVideoFeedUrl(activeCam, { drawZones: false })`; frontend overlay polygon bằng SVG riêng và hiện chưa truyền `conf_threshold` hay `show_static_containers`.

## Direct Impact

- `REQ-002` — affected — Area Zone Violations phải chuyển từ "bbox center nằm trong polygon" sang zone evaluation theo class: bottom-center cho người/xe máy/xe đạp; footprint hoặc bbox overlap cho xe tải/container truck/xe nâng/xe cẩu/xe con; container/static container dùng overlap ratio có threshold riêng.
- `REQ-004` — affected — event dedupe hiện theo `camera_id + zone_id + object_class`; CR-007 chưa triển khai tracking nhưng phải chuẩn bị `track_id`/fallback semantics để không khóa thiết kế vào object_class khi thêm ByteTrack sau.
- `REQ-005` — affected — zone cache/runtime polygon vẫn là nguồn hình học, nhưng contract đánh giá zone cần thêm method/ratio để UI/backend hiểu vì sao một object được tính trong zone.
- `REQ-009` — affected — alert lane vẫn dẫn xuất từ event đã dedup, nhưng false positive/false negative trong zone evaluation thay đổi trực tiếp số lượng cảnh báo Mức 3.
- Global Acceptance Criteria #1 — affected — hạ threshold và thêm lọc application không được làm giảm realtime stream; P0 phải đo lại backend tests và stream cadence.
- `.delivery/ARCHITECTURE.md` — affected — `ai-vision-pipeline` boundary cần thay YOLOv26/YOLO-World/center-PIP bằng YOLOv11s finetune, class normalization, per-class filter và geometry evaluator.
- `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json` — affected — metadata fields được bổ sung additive; field cũ `bbox` phải giữ nguyên để không phá frontend.
- `ADR-002-point-in-polygon-zone-evaluation.md` — affected — quyết định kiến trúc center point đã lỗi thời cho đối tượng dài; cần ADR mới hoặc supersede ADR-002 sau khi CR được duyệt.

## Compatibility Risks

- API backward compatibility: giữ nguyên `bbox` cũ trong detection REST/MJPEG metadata theo dạng `[left, top, width, height]` phần trăm ở legacy lane và `bbox` xyxy normalized trong `AREA_FRAME_METADATA`; các trường debug mới phải additive/optional.
- Frontend compatibility: `AreaSecurityDashboard` hiện không tự vẽ bbox từ metadata, MJPEG là nguồn bbox chính; thay đổi renderer backend không cần sửa layout lớn nhưng URL helper cần nhận query param mới nếu muốn debug container từ UI.
- Event compatibility: nếu đổi zone evaluation trước khi có `track_id`, số event/dedupe có thể thay đổi; cooldown hiện theo class có thể gộp nhầm nhiều đối tượng cùng class hoặc bỏ qua object mới cùng class trong cùng zone.
- Model compatibility: YOLOv11s finetune có thể trả class như `shipping_container`/`container_truck`; canonical mapping phải giữ raw class để debug và không ép sai vào 8 class nếu model.names khác kỳ vọng.
- Performance compatibility: overlap polygon/bbox mỗi detection mỗi zone phải dùng NumPy/OpenCV nhẹ hoặc helper tự viết; Shapely chỉ nên dùng nếu owner chấp nhận thêm dependency và đã đo overhead.
- UI noise compatibility: mặc định vẫn có thể ẩn container tĩnh để giảm rối, nhưng không được hard-code mất khả năng debug container/shipping_container.

## Transitive Task Impact

- `TASK-001` — module `none` — status `ready` — impact `affected` — benchmark/model selection baseline còn ghi YOLOv26 và cần ghi nhận YOLOv11s finetune, threshold inference thấp/application filtering, và số đo realtime sau CR-006. Packet action `owner-decision-required`.
- `TASK-002` — module `none` — status `ready` — impact `affected` — API foundation phải bổ sung query param `show_static_containers`, threshold semantics và debug metadata fields. Packet action `invalidate-automatically`.
- `TASK-003` — module `none` — status `ready` — impact `unaffected` — không yêu cầu schema DB mới trong P0/P1 nếu `track_id` chỉ là runtime metadata chuẩn bị cho bước sau.
- `TASK-004` — module `none` — status `ready` — impact `unaffected` — UI/UX foundation không đổi đáng kể; debug toggle có thể nằm trong feature UI sau.
- `TASK-005` — module `none` — status `ready` — impact `unaffected` — scaffold không đổi.
- `TASK-006` — module `database-storage` — status `ready` — impact `uncertain` — nếu P2 tracking yêu cầu lưu `track_id` vào event thì schema/event model bị ảnh hưởng; P0/P1 chưa cần migration. Packet action `owner-decision-required`.
- `TASK-007` — module `ai-vision-pipeline` — status `ready` — impact `affected` — sở hữu core detection, class mapping, threshold filtering và zone evaluator. Packet action `invalidate-automatically`.
- `TASK-008` — module `web-ui` — status `ready` — impact `unaffected` — shared components không đổi.
- `TASK-009` — module `web-ui` — status `ready` — impact `unaffected` — Gate Dashboard/LPR ngoài phạm vi, chỉ cần regression để bảo đảm không đổi luồng cổng.
- `TASK-010` — module `web-ui` — status `blocked` — impact `affected` — Area Dashboard cần biết metadata additive/debug fields và có thể thêm control truyền `show_static_containers`/threshold khi debug. Packet action `owner-decision-required`.
- `TASK-012` — module `web-ui` — status `blocked` — impact `uncertain` — zone editor không đổi shape, nhưng zone semantics hiển thị có thể cần ghi chú method/ratio sau CR. Packet action `owner-decision-required`.
- `TASK-013` — module `llm-qa-agent` — status `ready` — impact `unaffected` — chatbot chỉ đọc event đã lưu, không chạm detection runtime.
- `TASK-014` — module `alert-dispatcher` — status `ready` — impact `uncertain` — alert lane nhận số lượng violation thay đổi do zone evaluator chính xác hơn; không đổi dispatcher contract. Packet action `owner-decision-required`.
- `TASK-015` — module `none` — status `ready` — impact `affected` — E2E phải bổ sung/điều chỉnh case bbox render threshold, zone violation geometry và realtime stream regression. Packet action `invalidate-automatically`.
- `TASK-016` — module `api-gateway` — status `complete` — impact `affected` — completed metadata contract thiếu debug fields và vẫn mô tả center semantics. Packet action `owner-decision-required`.
- `TASK-017` — module `ai-vision-pipeline` — status `needs-revision` — impact `affected` — code thực tế trong `vision_pipeline.py`, `video_stream.py`, `events.py`, `area_metadata.py` là lõi CR-007. Packet action `owner-decision-required`.
- `TASK-018` — module `web-ui` — status `complete` — impact `affected` — frontend consume metadata lane có thể giữ tương thích, nhưng type definitions cần nhận additive debug/track fields nếu hiển thị. Packet action `owner-decision-required`.
- `TASK-019` — module `none` — status `needs-revision` — impact `affected` — verification CR-003 phải chạy lại vì metadata/event lane và hot path detection semantics thay đổi. Packet action `owner-decision-required`.
- `TASK-020` đến `TASK-025` — module `database-storage` / `api-gateway` / `web-ui` — status `planned` hoặc `complete/in-review` theo CR-004 — impact `unaffected` — object labeling import/dataset flow không thuộc phạm vi CR-007, miễn không thay đổi nhãn dataset/storage.
- `TASK-026` — module `api-gateway` — status `planned` — impact `uncertain` — Telegram evidence contract dùng object type/violation reason; nếu canonical class/zone method mới thay đổi reason text thì contract cần tham chiếu. Packet action `owner-decision-required`.
- `TASK-027` — module `alert-dispatcher` — status `planned` — impact `uncertain` — số event hợp lệ thay đổi và sau này dedupe theo `track_id` có thể đổi input alert. Packet action `owner-decision-required`.
- `TASK-028` — module `alert-dispatcher` — status `planned` — impact `affected` — verification Telegram evidence phải đảm bảo CR-007 không tạo alert giả/lặp từ container tĩnh. Packet action `owner-decision-required`.
- `TASK-029` — module `llm-qa-agent` — status `in-review` — impact `unaffected` — Gemini Text-to-SQL không liên quan detection runtime.

## Unaffected Evidence

- `REQ-001` Gate LPR không nằm trong phạm vi business của CR-007; chỉ chạy regression vì dùng chung một số helper detection/renderer.
- `REQ-003` severity levels không đổi; CR-007 chỉ làm input zone violation chính xác hơn.
- `REQ-006` vehicle whitelist/blacklist không đổi.
- `REQ-007` dataset object labeling không đổi trong CR này; không yêu cầu thêm nhãn custom hoặc huấn luyện model mới.
- CR-004 import/source/sample/label CRUD không cần khóa.
- Không có migration bắt buộc cho P0/P1; tracking persistence thuộc P2/CR sau nếu Product Owner duyệt.

## Selective Lock

- Lock artifacts: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `.delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`.
- Lock modules: `ai-vision-pipeline` (`backend/app/services/vision_pipeline.py` và helper geometry mới), `video-stream-service` threshold handoff trong `backend/app/services/video_stream.py`, `api-gateway` phần `backend/app/api/v1/events.py`, `area-metadata-publisher` (`backend/app/services/area_metadata.py`), frontend area URL/type surface (`frontend/src/services/api.ts`, `frontend/src/types/`, `frontend/src/pages/AreaSecurityDashboard.tsx` nếu thêm debug control).
- Do not lock: `database-storage` schema ở P0/P1, `llm-qa-agent`, CR-004 dataset/object-labeling flow, Gate LPR business logic ngoài regression.

## Packet Actions

- `invalidate-automatically`: `TASK-002`, `TASK-007`, `TASK-015` vì đang ready/unstarted và bị ảnh hưởng trực tiếp bởi API/detection/verification contract.
- `owner-decision-required`: `TASK-001`, `TASK-006`, `TASK-010`, `TASK-012`, `TASK-014`, `TASK-016`, `TASK-017`, `TASK-018`, `TASK-019`, `TASK-026`, `TASK-027`, `TASK-028` vì đã complete/needs-revision/blocked/planned có phụ thuộc hoặc cần quyết định phạm vi.
- `no-action`: mọi task được phân loại `unaffected` ở trên.

## Implementation Priority Plan

### P0 — Correctness and Debuggability Without API Breakage

- Đồng bộ default threshold: `/api/v1/events/video-feed` dùng `settings.DETECTION_CONFIDENCE_THRESHOLD` hoặc default `0.35`, không giữ `0.50`.
- Tách inference threshold thấp hơn (`0.25-0.30`) khỏi application filtering; model predict lấy ngưỡng thấp, filtering dùng global/per-class threshold.
- Thêm per-class threshold config cho `person`, `container`, `shipping_container`, `truck`, `container_truck`, `forklift`, `crane`, `car`, `motorbike`, `bicycle` và canonical equivalents.
- Thêm helper geometry nhẹ cho normalized bbox, clamp bbox, bottom-center, footprint/bbox polygon overlap ratio.
- Thay zone evaluation trong production detections bằng method theo class; giữ `evaluate_bbox_center_in_zone()` tạm thời cho backward tests hoặc deprecate có test mới.
- Thêm `show_static_containers=false` cho `/events/video-feed`; mặc định có thể ẩn container nhưng debug bật được.
- Cải thiện renderer bbox: clamp trong frame, label class + confidence + zone status, màu violation/non-violation/debug, label không vượt khung.
- Bổ sung metadata additive fields ở object: `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id` khi có.

### P1 — Contract and UI Debug Surface

- Cập nhật API contract/schema cho query params và metadata debug optional fields.
- Cập nhật frontend `getVideoFeedUrl()` nhận `confThreshold` và `showStaticContainers`; nếu cần thêm debug-only UI control trong `AreaSecurityDashboard`.
- Chuẩn hóa class mapping YOLOv11s finetune từ `model.names`, giữ raw class để debug `shipping_container`/`container_truck`.
- Tài liệu hóa threshold defaults theo hai tầng: inference threshold và application/per-class threshold.
- Cập nhật ADR bằng cách supersede ADR-002 hoặc tạo ADR mới cho class-aware zone evaluation.

### P2 — Tracking Readiness and Follow-up CR

- Thiết kế tích hợp `model.track(..., tracker="bytetrack.yaml", persist=True)` sau khi P0 ổn định.
- Trả `track_id` trong detection metadata khi có, fallback `None`/synthetic id khi không có.
- Đổi event dedupe sang `camera_id + zone_id + track_id` khi có track, fallback logic cũ khi không có.
- Đánh giá migration DB/event schema nếu cần lưu `track_id` lâu dài cho AI Assistant/Telegram evidence.

## Owner Decisions Required

- Chốt default MJPEG `conf_threshold`: đề xuất lấy `settings.DETECTION_CONFIDENCE_THRESHOLD` nếu không truyền, với `.env` hiện 0.30; nếu muốn UI ổn định hơn thì đặt route default 0.35.
- Chốt inference threshold thấp hơn: đề xuất `0.25` hoặc `0.30`; application per-class threshold mới là ngưỡng nghiệp vụ.
- Chốt dependency geometry: ưu tiên OpenCV/NumPy hiện có; chỉ dùng Shapely nếu owner chấp nhận thêm dependency và overhead.
- Chốt container behavior mặc định: đề xuất `show_static_containers=false`, nhưng param debug có thể bật bbox container/shipping_container.
- Chốt whether `shipping_container` và `container_truck` là canonical class riêng trong API hay raw class được map về `container`/`truck` nhưng giữ `raw_class` trong debug metadata.
- Chốt P2 tracking là task tiếp theo trong cùng CR hay CR mới; đề xuất CR mới sau khi P0/P1 đủ test.

## Update Order

1. Product Owner duyệt hoặc chỉnh `.delivery/changes/CR-007/CHANGE-IMPACT.md`.
2. Cập nhật `.delivery/REQUIREMENTS.md`: thêm audit trail CR-007, sửa `REQ-002` khỏi center-only, ghi YOLOv11s finetune thay YOLOv26 cho Area Monitoring nếu được duyệt.
3. Cập nhật `.delivery/ARCHITECTURE.md` và ADR-002/superseding ADR cho class-aware zone evaluation và threshold layering.
4. Cập nhật `.delivery/API-CONTRACT.md` và schema cho query params/debug metadata additive fields.
5. Áp dụng packet actions, đặc biệt invalidate `TASK-002`, `TASK-007`, `TASK-015`; owner quyết định reopen/supersede `TASK-016/017/018/019`.
6. Triển khai P0 backend + tests, sau đó P1 frontend/contract, rồi mới quyết định P2 tracking.

## Validation Plan

- Traceability: CR-007 ánh xạ tới `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009` và Global AC #1.
- Unit tests: per-class threshold filtering; bottom-center zone evaluation; footprint/bbox overlap ratio evaluation; video-feed default threshold; `show_static_containers` behavior.
- Contract tests: `/api/v1/events/live-detections` và websocket `AREA_FRAME_METADATA` vẫn giữ field cũ, có field debug additive khi có dữ liệu.
- Renderer tests: bbox được clamp trong frame; label không vượt biên; container bbox bị ẩn/mở theo query param.
- Regression tests: `python -m pytest backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py -q`.
- Frontend verification: `npx --prefix frontend tsc --noEmit` và `npm --prefix frontend run build`.
- Performance verification: đo lại stream sau P0 để xác nhận không làm giảm realtime lane đã ổn sau CR-006.

## Liên quan

- `backend/app/api/v1/events.py` — `/video-feed`, hidden container, renderer bbox, `/live-detections` synthetic center-zone fallback.
- `backend/app/services/vision_pipeline.py` — YOLOv11s model loading, class mapping, threshold filtering, zone evaluation.
- `backend/app/services/video_stream.py` — `CameraFramePipeline` inference threshold và snapshot fields.
- `backend/app/services/area_metadata.py` — metadata object serialization.
- `frontend/src/pages/AreaSecurityDashboard.tsx` và `frontend/src/services/api.ts` — MJPEG URL và optional debug controls.
- `.delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md` — decision cần được supersede sau CR-007.

---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: in-review
updated_at: "2026-08-24T21:58:15+07:00"
change_id: CR-005
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, API-CONTRACT.md, MASTER-PLAN.md]
---

# Đánh giá Ảnh hưởng Thay đổi cho CR-005

## Change Summary
- Business delta: Khi có vi phạm ở giám sát khu vực, hệ thống phải gửi thông báo Telegram kèm thời gian vi phạm đúng, camera, zone, loại đối tượng, lí do vi phạm và video clip chứng cứ 10s.
- Affected requirements: `REQ-002`, `REQ-003`, `REQ-004`, `REQ-008`, `REQ-009`
- Baseline note: Theo yêu cầu Product Owner, CR-005 chỉ được ghi nhận trong artifact impact này; chưa cập nhật `.delivery/REQUIREMENTS.md`.
- Script execution note: `assess_change_impact.py` đã được chạy trên bản sao tạm của `.delivery` có chèn CR-005 để lấy candidate closure, vì script yêu cầu CR phải tồn tại trong `REQUIREMENTS.md` nhưng baseline file này chưa được phép sửa trong bước hiện tại.

## Direct Impact
- `REQ-002` — affected — Area Zone Violation là nguồn nghiệp vụ trực tiếp của Telegram evidence notification; event khu vực phải có đủ camera, zone, object type, violation reason và clip 10s.
- `REQ-003` — affected — severity Mức 3 cần tiếp tục là điều kiện kích hoạt notification, nhưng payload phải phân biệt rõ lý do vi phạm và loại đối tượng.
- `REQ-004` — affected — notification phải lấy từ event đã qua cooldown/dedup để tránh gửi lặp Telegram và để bảo đảm chỉ một clip chứng cứ 10s đại diện cho cùng đối tượng/zone trong cửa sổ cooldown.
- `REQ-008` — affected — AI Assistant đang dùng event evidence clip 10s; contract event/clip evidence cần nhất quán để Telegram và chatbot cùng truy xuất đúng clip/thời gian.
- `REQ-009` — affected — acceptance hiện yêu cầu Telegram có thời gian, camera, zone và ảnh crop; CR-005 thay đổi/bổ sung thành thời gian đúng, camera, zone, object type, violation reason và video clip 10s.
- `.delivery/API-CONTRACT.md` — affected — cần cập nhật `ZONE_VIOLATION_EVENT`/`ALERT_LEVEL_3_NOTIFICATION` payload hoặc REST evidence fields gồm `violation_time`, `camera_id`, `zone_id/name`, `object_type`, `violation_reason`, `clip_url`, `clip_duration_seconds`.
- `.delivery/ARCHITECTURE.md` — affected — `event-clip-manager` và `alert-dispatcher` boundary cần thể hiện Telegram gửi video evidence 10s, không chỉ ảnh crop.
- `docs/contracts/api/websocket-events.json` và `docs/contracts/api/api-schema.json` — affected — cần schema hóa payload alert/evidence sau khi CR được duyệt.

## Transitive Task Impact
- `TASK-001` — module `none` — status `ready` — impact `unaffected` — AI benchmark/model selection không đổi vì CR-005 chỉ thay đổi notification payload và evidence delivery.
- `TASK-002` — module `none` — status `ready` — impact `affected` — API foundation phải bổ sung contract notification/evidence fields; packet action `invalidate-automatically`.
- `TASK-003` — module `none` — status `ready` — impact `uncertain` — DB design cần kiểm tra event schema đã lưu đủ `violation_reason`, `object_type`, đúng event/capture time và clip URL chưa; packet action `owner-decision-required`.
- `TASK-004` — module `none` — status `ready` — impact `unaffected` — UI/UX foundation không đổi trực tiếp; Telegram payload là backend/external notification.
- `TASK-005` — module `none` — status `ready` — impact `unaffected` — scaffolding không đổi.
- `TASK-006` — module `database-storage` — status `ready` — impact `uncertain` — có thể cần bổ sung hoặc xác nhận event record fields cho thời gian đúng, lý do vi phạm, object type và clip evidence; packet action `owner-decision-required`.
- `TASK-007` — module `ai-vision-pipeline` — status `ready` — impact `affected` — pipeline/event manager phải sinh lý do vi phạm chuẩn và gắn đúng event/capture time trước khi slice clip; packet action `invalidate-automatically`.
- `TASK-008` — module `web-ui` — status `ready` — impact `unaffected` — shared UI components không bắt buộc đổi để gửi Telegram video.
- `TASK-009` — module `web-ui` — status `ready` — impact `unaffected` — Gate Dashboard LPR không thuộc giám sát khu vực.
- `TASK-010` — module `web-ui` — status `ready` — impact `unaffected` — Area Dashboard display không bắt buộc đổi nếu event feed đã có dữ liệu; Telegram delivery thuộc backend alert lane.
- `TASK-012` — module `web-ui` — status `ready` — impact `unaffected` — Zone & Tag Settings không đổi.
- `TASK-013` — module `llm-qa-agent` — status `ready` — impact `uncertain` — chatbot evidence contract cần giữ nhất quán với event clip/time fields nhưng không nhất thiết đổi UI; packet action `owner-decision-required`.
- `TASK-014` — module `alert-dispatcher` — status `ready` — impact `affected` — Telegram Bot phải gửi payload mới và đính kèm video clip 10s; packet action `invalidate-automatically`.
- `TASK-015` — module `none` — status `ready` — impact `affected` — E2E verification phải kiểm tra nội dung Telegram và video clip evidence 10s; packet action `invalidate-automatically`.
- `TASK-016` — module `api-gateway` — status `complete` — impact `affected` — completed metadata/alert contract cần owner quyết định có reopen/supersede để bổ sung alert evidence semantics; packet action `owner-decision-required`.
- `TASK-017` — module `ai-vision-pipeline` — status `needs-revision` — impact `affected` — backend area metadata/event lane đang liên quan trực tiếp tới event time, reason, clip slicing và alert dispatch input; packet action `owner-decision-required`.
- `TASK-018` — module `web-ui` — status `complete` — impact `unaffected` — frontend consume metadata lane không cần đổi trực tiếp cho Telegram video.
- `TASK-019` — module `none` — status `needs-revision` — impact `affected` — verification CR-003 cần mở rộng hoặc bổ sung case đảm bảo alert lane vẫn dedup và có evidence payload đúng; packet action `owner-decision-required`.
- `TASK-020` — module `database-storage` — status `planned` — impact `unaffected` — CR-004 object-labeling storage không liên quan trực tiếp.
- `TASK-021` — module `api-gateway` — status `planned` — impact `unaffected` — CR-004 dataset API không liên quan trực tiếp.
- `TASK-022` — module `web-ui` — status `planned` — impact `unaffected` — CR-004 object-labeling UX không liên quan trực tiếp.
- `TASK-023` — module `api-gateway` — status `planned` — impact `unaffected` — CR-004 dataset backend không liên quan trực tiếp.
- `TASK-024` — module `web-ui` — status `planned` — impact `unaffected` — CR-004 dataset frontend không liên quan trực tiếp.
- `TASK-025` — module `web-ui` — status `planned` — impact `unaffected` — CR-004 E2E object-labeling không liên quan trực tiếp.

## Unaffected Evidence
- `REQ-001` Gate LPR không đổi vì CR-005 chỉ nói "vi phạm ở giám sát khu vực", không phải xe qua cổng.
- `REQ-005`, `REQ-006`, `REQ-007` không đổi trực tiếp; zone configuration, vehicle tags và object-labeling dataset chỉ là nguồn dữ liệu nền nếu object type/zone rules đã tồn tại.
- CR-004 task range `TASK-020` đến `TASK-025` không cần khóa vì CR-005 không thay đổi media import/dataset labeling flow.
- UI area dashboard có thể vẫn hiển thị event feed như cũ; yêu cầu mới nằm ở Telegram external notification và evidence payload.

## Selective Lock
- Lock artifacts: `.delivery/REQUIREMENTS.md`, `.delivery/API-CONTRACT.md`, `.delivery/ARCHITECTURE.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`.
- Lock modules: `alert-dispatcher`, `event-clip-manager`, `ai-vision-pipeline`, `api-gateway` alert/event schemas, and `database-storage` event record only if owner confirms schema gap.
- Do not lock: `web-ui` broadly, Gate LPR, Zone & Tag Settings, CR-004 dataset/object-labeling tasks.

## Packet Actions
- `invalidate-automatically`: `TASK-002`, `TASK-007`, `TASK-014`, `TASK-015` because they are unstarted/ready and directly affected.
- `owner-decision-required`: `TASK-003`, `TASK-006`, `TASK-013` because impact depends on whether existing event schema already stores required evidence fields.
- `owner-decision-required`: `TASK-016`, `TASK-017`, `TASK-019` because they are complete, needs-revision, or verification work tied to CR-003 lanes and must not be marked stale automatically.
- `no-action`: all tasks classified `unaffected` above.

## Owner Decisions Required
- Decide whether Telegram must send the MP4 video file itself, a public/downloadable `clip_url`, or both.
- Decide whether Telegram still includes ảnh crop in addition to the required 10s video clip evidence.
- Confirm definition of "thời gian đúng": event `captured_at` at violation detection, clip start/end midpoint, or persisted event `created_at`; recommended is violation `captured_at` from the frame/event that passed dedup.
- Confirm whether `violation_reason` is a structured code such as `object_forbidden_in_zone` plus human-readable Vietnamese text, or only display text.
- Decide whether completed `TASK-016` should be reopened, superseded by a CR-005 API design task, or handled as a patch to global API contract after approval.

## Update Order
1. Project owner approves or revises `.delivery/changes/CR-005/CHANGE-IMPACT.md`.
2. Update `.delivery/REQUIREMENTS.md` audit trail for CR-005 and refine `REQ-002`, `REQ-003`, `REQ-004`, `REQ-008`, `REQ-009`.
3. Update `.delivery/API-CONTRACT.md` and API schema files for event/alert/evidence payload.
4. Update `.delivery/ARCHITECTURE.md` for `event-clip-manager` to `alert-dispatcher` video evidence flow.
5. Apply packet actions and owner decisions before implementation changes.
6. Only after approval, implement alert dispatcher/event manager changes and verification.

## Validation Plan
- Traceability: CR-005 maps to `REQ-002`, `REQ-003`, `REQ-004`, `REQ-008`, `REQ-009` and affected tasks above.
- Contract validation: `ALERT_LEVEL_3_NOTIFICATION` or Telegram notification contract contains exact violation time, camera, zone, object type, reason and 10s clip URL/file reference.
- Backend verification: simulate a zone violation and assert one deduped Telegram dispatch includes the correct event time and clip evidence.
- Evidence verification: confirm generated clip duration is 10s and references the same event/camera/zone/object as the notification.
- Regression verification: metadata lane alone must not trigger Telegram; only event/alert lane after severity classification and cooldown can dispatch.

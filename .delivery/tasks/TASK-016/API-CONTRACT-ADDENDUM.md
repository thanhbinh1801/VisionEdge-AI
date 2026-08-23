---
artifact: API-CONTRACT-ADDENDUM.md
version: "1.0"
task_id: TASK-016
owner: design-api
status: proposed
updated_at: "2026-08-20T18:10:00+07:00"
change_id: CR-003
---

# API Contract Addendum cho TASK-016

Tài liệu này bổ sung contract cho `CR-003` mà không thay thế các contract đã được phát hành cho CR-001 và CR-002.

## Pham vi
- Thêm lane `AREA_FRAME_METADATA` cho `Area Security Dashboard`.
- Làm rõ semantics `zone_version` và `zone cache invalidation`.
- Giữ event lane và alert lane hiện hữu theo hướng backward-compatible.

## Contract Decisions
- Transport: sử dụng additive event type mới `AREA_FRAME_METADATA` trên gateway WebSocket hiện tại `/ws/v1/events`.
- Overlay strategy: UI area dashboard uu tien consume metadata stream để render overlay/KPI; annotated video nếu có chỉ la lane bo tro.
- Event feed strategy: `ZONE_VIOLATION_EVENT` và `ALERT_LEVEL_3_NOTIFICATION` tiếp tục phục vụ lịch sử sự kiện, severity, và notification.

## Payload tối thiểu của AREA_FRAME_METADATA
- `camera_id`
- `frame_id`
- `captured_at`
- `zone_version`
- `stream_status`
- `pipeline_latency_ms`
- `objects[]`
- `kpi_delta`

## Runtime Guarantees
- Frame loop area monitoring không đọc DB mỗi frame.
- Sau CRUD zone thành công, runtime cache theo `camera_id` phải được refresh/invalidate trước khi xác nhận hoàn tất request.
- `AREA_FRAME_METADATA` không được kich hoat am thành cảnh báo hay notification trực tiếp.

## Traceability
- Yêu cầu liên kết: `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`
- Upstream change artifact: `.delivery/changes/CR-003/CHANGE-IMPACT.md`
- Downstream consumers: `TASK-017`, `TASK-018`, `TASK-019`

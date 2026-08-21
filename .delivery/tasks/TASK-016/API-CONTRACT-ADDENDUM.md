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

Tai lieu nay bo sung contract cho `CR-003` ma khong thay the cac contract da duoc phat hanh cho CR-001 va CR-002.

## Pham vi
- Them lane `AREA_FRAME_METADATA` cho `Area Security Dashboard`.
- Lam ro semantics `zone_version` va `zone cache invalidation`.
- Giu event lane va alert lane hien huu theo huong backward-compatible.

## Contract Decisions
- Transport: su dung additive event type moi `AREA_FRAME_METADATA` tren gateway WebSocket hien tai `/ws/v1/events`.
- Overlay strategy: UI area dashboard uu tien consume metadata stream de render overlay/KPI; annotated video neu co chi la lane bo tro.
- Event feed strategy: `ZONE_VIOLATION_EVENT` va `ALERT_LEVEL_3_NOTIFICATION` tiep tuc phuc vu lich su su kien, severity, va notification.

## Payload toi thieu cua AREA_FRAME_METADATA
- `camera_id`
- `frame_id`
- `captured_at`
- `zone_version`
- `stream_status`
- `pipeline_latency_ms`
- `objects[]`
- `kpi_delta`

## Runtime Guarantees
- Frame loop area monitoring khong doc DB moi frame.
- Sau CRUD zone thanh cong, runtime cache theo `camera_id` phai duoc refresh/invalidate truoc khi xac nhan hoan tat request.
- `AREA_FRAME_METADATA` khong duoc kich hoat am thanh canh bao hay notification truc tiep.

## Traceability
- Linked requirements: `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`
- Upstream change artifact: `.delivery/changes/CR-003/CHANGE-IMPACT.md`
- Downstream consumers: `TASK-017`, `TASK-018`, `TASK-019`

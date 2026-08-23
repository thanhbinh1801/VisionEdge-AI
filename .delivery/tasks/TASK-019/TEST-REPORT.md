---
artifact: TEST-REPORT.md
version: "1.0"
task_id: TASK-019
owner: verify-feature
status: in-review
updated_at: "2026-08-21T11:17:39+07:00"
---

# Test Report: TASK-019 — Verification cho CR-003 Realtime Area Metadata

## Traceability

| Requirement | Verification focus | Result |
|---|---|---|
| `REQ-002` | Metadata lane cập nhật realtime riêng cho Area Dashboard, event feed vẫn hiển thị được context sự kiện khu vực. | Failed |
| `REQ-004` | Hot path area monitoring không dựa vào DB read mỗi frame và metadata lane tách khỏi cooldown/event lane. | Passed |
| `REQ-005` | Zone cache theo `camera_id` được refresh và phản ánh `zone_version`/cache semantics đúng. | Passed |
| `REQ-009` | Event/alert lane vẫn tồn tại tách biệt với metadata lane và giữ được context phục vụ cảnh báo. | Failed |
| `CR-003` | Tách `video stream lane`, `realtime metadata lane`, `event/alert lane` mà không phá compatibility quan trọng cho UI. | Failed |

## Test Environment

- Đãte verified: August 20, 2026
- Workspace: `D:\Hilab\Project34`
- Backend runtime evidence from Python compile, Ruff, and scoped pytest
- Frontend runtime evidence from TypeScript, lint, and production Vite build
- Sandbox note: frontend production build inside sandbox failed with `spawn EPERM`; the same command succeeded outside sandbox and was used as final build evidence

## Acceptance Results

1. Metadata lane exists and frontend consumes `/ws/v1/events` instead of polling `live-detections` for per-frame overlay/KPI updates.
Result: Passed
Evidence: [AreaSecurityDashboard.tsx](D:/Hilab/Project34/frontend/src/pages/AreaSecurityDashboard.tsx), [websocket.py](D:/Hilab/Project34/backend/app/api/v1/websocket.py)

2. Area hot path no longer reads zones from DB each frame.
Result: Passed
Evidence: scoped backend tests `14 passed in 0.43s`; [events.py](D:/Hilab/Project34/backend/app/api/v1/events.py) now seeds `video-feed` and `live-detections` from `zone_cache_service`

3. Event lane remains compatible for operator-facing area event context after the metadata split.
Result: Failed
Evidence: frontend expects `evt.zone_name`, but backend `EventResponse` omits `zone_name`; recorded as [BUG-001.md](D:/Hilab/Project34/.delivery/tasks/TASK-019/BUG-001.md)

4. Violation events are persisted to SQLite and new violations create a 10s clip handoff for the future chatbot lane.
Result: Passed for the current code path; historical DB row is not backfilled.
Evidence: runtime DB inspection found one existing `ZONE_VIOLATION` severity-3 event. Static trace and regression tests confirm new live-detections and WebSocket metadata violations call the shared persistence helper, write `bbox`, and create `/media/clips/clip_<camera>_<timestamp>.mp4` via `EventManager.slice_10s_ring_buffer_clip`.

## Integration and E2E

- Backend integration checks:
  - `python -m pytest backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py backend/tests/test_gate_zones.py -q`
  - Result: pass (`14 passed in 0.43s`)
- Frontend integration checks:
  - `npm run lint`
  - `npx tsc --noEmit`
  - `npm run build`
  - Result: lint + typecheck passed; production build passed outside sandbox
- Contract compatibility review:
  - `AreaSecurityDashboard` now consumes `AREA_FRAME_METADATA` via WebSocket
  - `zones` API envelope is correctly handled by frontend client
  - `events` API response remains incompatible with frontend zone-name expectation
- Event persistence and chatbot clip handoff checks:
  - `python -c "import sqlite3,json; ..."` against `sentri_ai.db`
  - Result: pass; `violation_count=1`; latest event `evt-live-70ccffae`, camera `BAI-KIEM`, event type `ZONE_VIOLATION`, severity `3`, object `Xe tai`, clip `/videos/KiemHoa-Hik (1).mp4`
  - `rg -n "persist_area_metadata_violations|_persist_violation_event|slice_10s_ring_buffer_clip|video_clip_url|EventModel|event_manager" backend/app/api/v1/events.py backend/app/api/v1/websocket.py backend/app/services/event_manager.py -S`
  - Result: pass; WebSocket metadata path calls `persist_area_metadata_violations`; live-detections path calls `_persist_violation_event`; persistence helper calls `slice_10s_ring_buffer_clip` and writes `video_clip_url`

## Edge Cases

- Metadata empty state:
  - `AreaSecurityDashboard` renders fallback text when metadata snapshot has zero objects
  - Result: Passed by code inspection
- Metadata stream health:
  - frontend exposes `Metadata: CONNECTING/ONLINE/DEGRADED/OFFLINE`
  - Result: Passed by code inspection
- Zone cache versioning:
  - backend test confirms cache version increments on refresh
  - Result: Passed
- Violation duplicate cooldown:
  - regression test confirms a second same-camera/same-zone/same-object violation within cooldown returns no new event
  - Result: Passed
- Chatbot clip availability:
  - regression test confirms a prohibited metadata object creates one `ZONE_VIOLATION` event with `/media/clips/clip_WS-CAM_...mp4`
  - Result: Passed

## Regression

- Existing backend regression commands still pass after CR-003 implementation:
  - compileall
  - Ruff scoped checks
  - scoped pytest suite
- Event persistence scoped regression commands passed on August 21, 2026:
  - `.\venv\Scripts\python.exe -m py_compile backend/app/api/v1/events.py backend/app/api/v1/websocket.py backend/app/services/event_manager.py backend/tests/test_live_detections_event.py` -> exit 0
  - `.\venv\Scripts\python.exe -m pytest backend/tests/test_live_detections_event.py backend/tests/test_websocket_route_contract.py` -> `11 passed, 10 warnings in 25.61s`
  - `python -m ruff check backend/app/api/v1/events.py backend/app/api/v1/websocket.py backend/tests/test_live_detections_event.py` -> exit 0
- Existing frontend strict compilation/build flow still passes after CR-003 implementation:
  - `npm run lint`
  - `npx tsc --noEmit`
  - Vite production build outside sandbox
- Material regression found:
  - area event feed loses zone-name context due to schema mismatch

## Evidence

- Backend tests: `python -m pytest backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py backend/tests/test_gate_zones.py -q` -> `14 passed in 0.43s`
- Zone settings refresh probe, run on August 23, 2026:
  - `.\venv\Scripts\python.exe -m pytest backend/tests/test_zone_settings_dashboard_refresh.py backend/tests/test_area_metadata_runtime.py backend/tests/test_video_feed_regression.py backend/tests/test_live_detections_event.py -q` -> `19 passed, 13 warnings in 38.61s`
  - The probe changed a `BAI-KIEM` zone's vertices, `allowed_classes`, and `forbidden_classes`, then called the same `events.video_feed(camera_id="BAI-KIEM", draw_zones=False, db=...)` path used by `Giám sát khu vực`.
  - Observed result: `PUT /zones/{zone_id}` refreshed the camera cache and called `pipeline.update_zones`; opening area monitoring reused the refreshed cache with the updated vertices/classes and matching `zone_version`.
- DB inspection: `{"violation_count": 1, "latest": [["evt-live-70ccffae", "2026-08-20 08:37:38.226220", "BAI-KIEM", null, "ZONE_VIOLATION", 3, "Xe tai", null, "/videos/KiemHoa-Hik (1).mp4"]]}`
- Event/clip code trace:
  - `backend/app/api/v1/events.py:75` defines `_persist_violation_event`
  - `backend/app/api/v1/events.py:88` calls `event_manager.slice_10s_ring_buffer_clip`
  - `backend/app/api/v1/events.py:104` writes `video_clip_url`
  - `backend/app/api/v1/events.py:109` defines `persist_area_metadata_violations`
  - `backend/app/api/v1/websocket.py:98` calls `persist_area_metadata_violations`
  - `backend/app/api/v1/events.py:387` calls `_persist_violation_event` from `live-detections`
- Frontend lint: `npm run lint` -> exit 0
- Frontend typecheck: `npx tsc --noEmit` -> exit 0
- Frontend build outside sandbox: `vite v5.4.21`, `40 modules transformed`, `dist/assets/index-Cx70p4KT.js 219.12 kB`
- Schema mismatch evidence:
  - `frontend/src/pages/AreaSecurityDashboard.tsx:111: zone: evt.zone_name || 'Ngoài zone',`
  - `backend/app/api/v1/events.py` `EventResponse` fields omit `zone_name`

## Defects

- [BUG-001.md](D:/Hilab/Project34/.delivery/tasks/TASK-019/BUG-001.md) — Area event feed loses zone name in integrated UI
- No new defect for event persistence or chatbot clip handoff. Observation: existing historical event rows are not backfilled to the new `/media/clips/...` format. Observation: current `EventManager` clip writer creates a placeholder file, not a real decoded 10-second video slice.
- No new defect for the setting-change-to-area-monitoring refresh behavior. The August 23, 2026 probe passed for updated zone position and updated allowed/prohibited vehicle classes.

## Verdict

Feature verification verdict: failed

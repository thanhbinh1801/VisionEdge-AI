---
artifact: TEST-REPORT.md
version: "1.0"
task_id: TASK-019
owner: verify-feature
status: in-review
updated_at: "2026-08-20T20:00:59+07:00"
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

- Date verified: August 20, 2026
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

## Regression

- Existing backend regression commands still pass after CR-003 implementation:
  - compileall
  - Ruff scoped checks
  - scoped pytest suite
- Existing frontend strict compilation/build flow still passes after CR-003 implementation:
  - `npm run lint`
  - `npx tsc --noEmit`
  - Vite production build outside sandbox
- Material regression found:
  - area event feed loses zone-name context due to schema mismatch

## Evidence

- Backend tests: `python -m pytest backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py backend/tests/test_gate_zones.py -q` -> `14 passed in 0.43s`
- Frontend lint: `npm run lint` -> exit 0
- Frontend typecheck: `npx tsc --noEmit` -> exit 0
- Frontend build outside sandbox: `vite v5.4.21`, `40 modules transformed`, `dist/assets/index-Cx70p4KT.js 219.12 kB`
- Schema mismatch evidence:
  - `frontend/src/pages/AreaSecurityDashboard.tsx:111: zone: evt.zone_name || 'Ngoài zone',`
  - `backend/app/api/v1/events.py` `EventResponse` fields omit `zone_name`

## Defects

- [BUG-001.md](D:/Hilab/Project34/.delivery/tasks/TASK-019/BUG-001.md) — Area event feed loses zone name in integrated UI

## Verdict

Feature verification verdict: failed

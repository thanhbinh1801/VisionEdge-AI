---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T19:37:31+07:00"
task_id: TASK-018
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Gói Task: TASK-018 — Frontend Area Dashboard consume Realtime Metadata Riêng

- Mã task: TASK-018
- Loại task: implementation
- Phạm vi: feature
- Module: web-ui
- Năng lực: frontend-implementation
- Yêu cầu liên kết: REQ-002, REQ-005, REQ-009, CR-003
- Phụ thuộc: TASK-016
- Phạm vi ghi: .delivery/tasks/TASK-018/
- Đầu vào: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/services/api.ts`, `frontend/src/services/websocket.ts`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/types/index.ts`, `frontend/src/context/AppContext.tsx`
- Đầu ra dự kiến: frontend metadata-lane integration updates under `frontend/src/`, production verification evidence, `.delivery/tasks/TASK-018/TASK-RESULT.md`
- Điều kiện hoàn thành: UI area monitoring không cần polling detections/events để cập nhật metadata mỗi frame; video stream renderer vẫn là lane tách biệt.
- Chính sách phê duyệt: Project owner review required before promoting `TASK-RESULT.md` from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if implementation requires backend changes, approved contract changes, or edits outside frontend scope plus `.delivery/tasks/TASK-018/`.

## Execution Brief

### Objective
Update the Area Security Dashboard to consume the realtime metadata lane separately from the MJPEG video stream lane, preserving event-feed behavior.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-018/TASK-PACKET.md`
- `.delivery/tasks/TASK-018/TASK-RESULT.md`
- `.delivery/tasks/TASK-018/BUG-001.md` if present
- `.delivery/tasks/TASK-016/API-CONTRACT.md`
- `.delivery/tasks/TASK-017/TASK-RESULT.md`
- `frontend/src/pages/AreaSecurityDashboard.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/services/websocket.ts`
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/types/index.ts`
- `frontend/src/context/AppContext.tsx`
- `.delivery/MASTER-PLAN.md` section `TASK-018 Frontend Area Dashboard consume Realtime Metadata Riêng`

### Allowed write scope
- Historical task scope: `frontend/src/`, `.delivery/tasks/TASK-018/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-018/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-018/TASK-RESULT.md`, `BUG-*.md`, backend code, approved contracts, unrelated frontend features, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-018`, capability `frontend-implementation`, historical dependency `TASK-016`, linked requirements, expected outputs, and completion gate.
- Preserve the historical TASK-RESULT decision: MJPEG stream lane renders visual bboxes; realtime metadata lane drives KPI/status/latency/version/snapshot chips.
- UI does not poll detections/events for per-frame metadata updates.

### Edge cases / risks
- MASTER-PLAN now lists dependencies `TASK-016`, `TASK-017`; the packet's historical dependency list only names `TASK-016`.
- Reintroducing client-side bbox SVG rendering would duplicate MJPEG annotations.
- Frontend test runner was not available historically, so lint/typecheck/static assertions carried verification.
- Not specified in source artifacts: visual screenshot baseline, WebSocket reconnect UX acceptance, and browser-specific stream fallback behavior.

### Verification commands or validation method
- Historical verification: `npx tsc --noEmit`, `npm run lint`, and static `rg` assertions passed per TASK-RESULT.
- Planned verification command from MASTER-PLAN: `npm --prefix frontend run lint && npx --prefix frontend tsc --noEmit`.
- Preserve exact command outputs in TASK-RESULT when rerun.

### Escalation conditions
- Escalate before requiring backend changes, approved contract changes, event-feed behavior changes, or edits outside frontend scope plus `.delivery/tasks/TASK-018/`.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Implementation summary.
- Verification evidence.
- Source-of-truth lane decisions.
- Preserved behavior.
- Deviations and test gaps.
- Blockers and scope-change requests.

### Skill/capability to run
- `frontend-implementation`.

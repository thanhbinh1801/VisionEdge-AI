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

# Task Packet: TASK-018 — Frontend Area Dashboard consume Realtime Metadata Riêng

- Task ID: TASK-018
- Task type: implementation
- Scope: feature
- Module: web-ui
- Capability: frontend-implementation
- Linked requirements: REQ-002, REQ-005, REQ-009, CR-003
- Dependencies: TASK-016
- Write scope: .delivery/tasks/TASK-018/
- Inputs: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/services/api.ts`, `frontend/src/services/websocket.ts`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/types/index.ts`, `frontend/src/context/AppContext.tsx`
- Expected outputs: frontend metadata-lane integration updates under `frontend/src/`, production verification evidence, `.delivery/tasks/TASK-018/TASK-RESULT.md`
- Completion gate: UI area monitoring không cần polling detections/events để cập nhật metadata mỗi frame; video stream renderer vẫn là lane tách biệt.
- Approval policy: Project owner review required before promoting `TASK-RESULT.md` from `in-review` to `approved`.
- Escalation policy: Escalate only if implementation requires backend changes, approved contract changes, or edits outside frontend scope plus `.delivery/tasks/TASK-018/`.

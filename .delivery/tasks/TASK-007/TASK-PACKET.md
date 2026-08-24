---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-007
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-001, TASK-006]
---

# Gói Task: TASK-007 - Core AI Engine and React Custom Hooks

- Mã task: TASK-007
- Loại task: implementation
- Phạm vi: feature
- Module: ai-vision-pipeline
- Năng lực: backend-implementation
- Yêu cầu liên kết: REQ-004, REQ-007, CR-001, CR-002
- Phụ thuộc: TASK-001, TASK-006
- Phạm vi ghi: .delivery/tasks/TASK-007/
- Đầu vào: .delivery/ARCHITECTURE.md, docs/contracts/API-FOUNDATION.md
- Đầu ra dự kiến: backend/ai/ evaluator and slicer, frontend/src/hooks/ WebSocket and sound hooks
- Điều kiện hoàn thành: Implement 8 object classes, point-in-polygon evaluation, 15s cooldown deduplication, and React hooks for WebSocket/audio alert behavior.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate for approved contract changes, DB schema changes, or edits outside AI pipeline and hook scope.

## Execution Brief

### Objective
Implement the core AI vision pipeline and React hooks needed for object classification, zone evaluation, cooldown deduplication, WebSocket updates, and browser audio alerts.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-007/TASK-PACKET.md`
- `.delivery/tasks/TASK-007/TASK-RESULT.md`
- `.delivery/tasks/TASK-007/BUG-001.md` if present
- `.delivery/tasks/TASK-001/TASK-RESULT.md`
- `.delivery/tasks/TASK-006/TASK-RESULT.md`
- `.delivery/ARCHITECTURE.md`
- `docs/contracts/API-FOUNDATION.md` or `.delivery/API-CONTRACT.md`
- `.delivery/MASTER-PLAN.md` section `TASK-007 Triển khai Core AI Engine & React Custom Hooks`

### Allowed write scope
- Historical task scope: `backend/ai/`, `frontend/src/hooks/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-007/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-007/TASK-RESULT.md`, `BUG-*.md`, database schema, unrelated frontend pages/components, unrelated backend APIs, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-007`, capability `backend-implementation`, dependencies `TASK-001`, `TASK-006`, linked requirements, expected outputs, and completion gate.
- Implementation supports 8 object groups, point-in-polygon evaluation, 15s cooldown deduplication, `useWebSocket`, and `useAudioAlert`.
- Hook behavior must align with API/WebSocket foundation and alert UI requirements.

### Edge cases / risks
- Model output labels may not map cleanly to the approved 8 object groups.
- Cooldown state can incorrectly suppress legitimate repeated violations if camera/rule keys are too broad.
- Browser autoplay policies can affect audio alert behavior.
- Not specified in source artifacts: exact model confidence thresholds, frame sampling rate, hook retry policy, and audio asset file.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python -m pytest backend/tests/test_engine.py`.
- For hook-only changes, also use the repo's frontend typecheck/build command if available and document exact evidence.

### Escalation conditions
- Escalate before changing approved contracts, DB schema, model family, frontend page behavior outside hooks, or writing outside AI pipeline/hook scope.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Implementation summary.
- Verification evidence.
- Deviations and known limitations.
- Blockers and scope-change requests.

### Skill/capability to run
- `backend-implementation`.

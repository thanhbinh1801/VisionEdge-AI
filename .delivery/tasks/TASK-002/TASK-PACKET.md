---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-002
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-001]
---

# Gói Task: TASK-002 - Global API Foundation Contract

- Mã task: TASK-002
- Loại task: foundation-design
- Phạm vi: global
- Module: none
- Năng lực: api-foundation-design
- Yêu cầu liên kết: REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-009, CR-001, CR-002
- Phụ thuộc: TASK-001
- Phạm vi ghi: .delivery/tasks/TASK-002/
- Đầu vào: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Đầu ra dự kiến: .delivery/tasks/TASK-002/API-FOUNDATION.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Điều kiện hoàn thành: Publish REST API foundation covering 8 object classes, known/unknown vehicle labels, zone rules, and BBox dataset samples.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate if API design changes approved requirement semantics or breaks existing consumers.

## Execution Brief

### Objective
Design the global API foundation contract for SentriAI Mini, covering REST/WebSocket semantics needed by vehicle labels, zone rules, object classes, dataset samples, alerts, and chatbot evidence flows.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-002/TASK-PACKET.md`
- `.delivery/tasks/TASK-002/TASK-RESULT.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/API-CONTRACT.md` if already present
- `docs/contracts/api/api-schema.json` if already present
- `docs/contracts/api/websocket-events.json` if already present
- `.delivery/MASTER-PLAN.md` section `TASK-002 Thiết kế Hợp đồng Global API Foundation`

### Allowed write scope
- Historical task scope: `.delivery/tasks/TASK-002/API-FOUNDATION.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-002/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-002/TASK-RESULT.md`, production backend/frontend code, database schema, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-002`, capability `api-foundation-design`, dependency `TASK-001`, linked requirements, expected outputs, and completion gate.
- API foundation must specify 8 object classes, known/unknown vehicle labels, polygon zone rules, BBox dataset samples, WebSocket event expectations, and compatibility assumptions for downstream implementation.
- Contract artifacts must be detailed enough for TASK-003, TASK-006, TASK-007, TASK-008, and later feature tasks to consume.

### Edge cases / risks
- Existing consumers may already depend on field names or event shapes.
- Requirement semantics may be ambiguous between CR-001 and CR-002.
- Not specified in source artifacts: exact versioning scheme for every endpoint, auth model details, pagination limits, and complete error taxonomy.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python -m json.tool docs/contracts/api/api-schema.json`.
- Also validate that WebSocket event JSON remains parseable when present.
- Record missing files or skipped validation explicitly in TASK-RESULT.

### Escalation conditions
- Escalate before changing approved requirement semantics, removing/breaking existing consumers, adding production code changes, or expanding API scope beyond the listed outputs.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Contract summary.
- Verification evidence with exact commands/results.
- Deviations and compatibility notes.
- Blockers and scope-change requests.

### Skill/capability to run
- `api-foundation-design`.

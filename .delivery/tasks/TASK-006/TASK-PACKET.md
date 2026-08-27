---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-006
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-003, TASK-005]
---

# Gói Task: TASK-006 - SQLite and Data Access Layer

- Mã task: TASK-006
- Loại task: implementation
- Phạm vi: feature
- Module: database-storage
- Năng lực: backend-implementation
- Yêu cầu liên kết: REQ-001, REQ-006, CR-001, CR-002
- Phụ thuộc: TASK-003, TASK-005
- Phạm vi ghi: .delivery/tasks/TASK-006/
- Đầu vào: docs/contracts/DATABASE-DESIGN.md, docs/contracts/db/schema.sql
- Đầu ra dự kiến: backend/database/ SQLite engine and ORM models
- Điều kiện hoàn thành: ORM/data access layer stores cameras, zones, vehicle labels, dataset BBox samples, and violation events.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate for destructive migration, schema incompatibility, or changes outside database-storage scope.

## Execution Brief

### Objective
Implement the SQLite data access layer for cameras, zones, vehicle labels, dataset BBox samples, and violation events according to the approved database design.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-006/TASK-PACKET.md`
- `.delivery/tasks/TASK-006/TASK-RESULT.md`
- `.delivery/tasks/TASK-006/BUG-001.md` if present
- `.delivery/tasks/TASK-003/TASK-RESULT.md`
- `docs/contracts/db/schema.sql`
- `.delivery/MASTER-PLAN.md` section `TASK-006 Triển khai CSDL SQLite & Data Access Layer`

### Allowed write scope
- Historical task scope: `backend/database/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-006/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-006/TASK-RESULT.md`, `BUG-*.md`, runtime database files, frontend code, unrelated backend modules, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-006`, capability `backend-implementation`, dependencies `TASK-003`, `TASK-005`, linked requirements, expected output, and completion gate.
- Data layer stores cameras, zones, known/unknown vehicle labels, dataset BBox samples, and violation records.
- Implementation follows the approved schema and preserves downstream repository/API expectations.

### Edge cases / risks
- Runtime database files may contain local state and must not be treated as source artifacts for packet normalization.
- Later CR-004 schema changes may supersede parts of the original BBox sample design.
- Not specified in source artifacts: exact ORM library constraints, migration tool choice, transaction isolation policy, and seed-data strategy.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python -m pytest backend/tests/test_database.py`.
- Validate any historical bug notes from `.delivery/tasks/TASK-006/BUG-001.md` remain represented in TASK-RESULT when applicable.

### Escalation conditions
- Escalate before destructive migration, schema incompatibility, production data deletion, runtime DB edits, or writing outside database-storage scope.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Implementation summary.
- Verification evidence.
- Deviations/bug follow-up notes.
- Blockers and scope-change requests.

### Skill/capability to run
- `backend-implementation`.

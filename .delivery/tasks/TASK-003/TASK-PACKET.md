---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-23T15:34:21+07:00"
task_id: TASK-003
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-002]
---

# Gói Task: TASK-003 - Đãtabase Schema Foundation

- Mã task: TASK-003
- Loại task: foundation-design
- Phạm vi: global
- Module: none
- Năng lực: database-design
- Yêu cầu liên kết: REQ-001, REQ-002, REQ-006, CR-002
- Phụ thuộc: TASK-002
- Phạm vi ghi: .delivery/tasks/TASK-003/
- Đầu vào: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Đầu ra dự kiến: .delivery/tasks/TASK-003/DATABASE-DESIGN.md, docs/contracts/db/schema.sql
- Điều kiện hoàn thành: Publish database design for Camera, Zone, Event, known/unknown vehicles, and BBox dataset samples.
- Chính sách phê duyệt: Project owner review required before promoting TASK-RESULT.md to approved.
- Chính sách leo thang: Escalate for schema changes that require migration or break current data access code.

## Execution Brief

### Objective
Design the database/schema foundation for cameras, zones, events, known/unknown vehicles, and BBox dataset samples without altering historical TASK-003 results.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-003/TASK-PACKET.md`
- `.delivery/tasks/TASK-003/TASK-RESULT.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/API-CONTRACT.md`
- `docs/contracts/db/schema.sql` if already present
- `.delivery/MASTER-PLAN.md` section `TASK-003 Thiết kế CSDL & Database Schema Foundation`

### Allowed write scope
- Historical task scope: `.delivery/tasks/TASK-003/DATABASE-DESIGN.md`, `docs/contracts/db/schema.sql`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-003/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-003/TASK-RESULT.md`, production database code, migrations, runtime databases, bug/test-report artifacts, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-003`, capability `database-design`, dependency `TASK-002`, linked requirements, expected outputs, and completion gate.
- Database design covers Camera, Zone, Event, known/unknown vehicles, and BBox dataset samples.
- Schema design must align with global API foundation and support downstream SQLite/data access implementation.

### Edge cases / risks
- Migration direction may be under-specified for existing local SQLite data.
- Dataset sample storage can conflict with later CR-004 object-labeling requirements if over-constrained.
- Not specified in source artifacts: retention policy, backup/restore procedure, exact indexing benchmark thresholds, and full migration rollback script.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python -m pytest backend/tests/test_database_schema.py`.
- If tests are unavailable, validate SQL syntax with available local SQLite tooling and document the limitation.

### Escalation conditions
- Escalate before destructive migration, schema incompatibility, production DB modification, or changes outside database-design outputs.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Entity/schema summary.
- Verification evidence.
- Deviations/migration notes.
- Blockers and scope-change requests.

### Skill/capability to run
- `database-design`.

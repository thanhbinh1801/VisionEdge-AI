---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T19:31:48+07:00"
task_id: TASK-020
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-020 Thiết kế DB/Storage cho Object Labeling Thật

- Task ID: TASK-020
- Task type: feature-design
- Scope: feature
- Module: database-storage
- Capability: database-design
- Linked requirements: REQ-005, REQ-007, CR-004
- Dependencies: TASK-019
- Write scope: .delivery/tasks/TASK-020/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/changes/CR-004/CHANGE-IMPACT.md, docs/contracts/db/schema.sql, backend/database/models.py, backend/database/repository.py
- Expected outputs: .delivery/tasks/TASK-020/DATABASE-DESIGN.md, .delivery/tasks/TASK-020/TASK-RESULT.md
- Completion gate: Xác định contract dữ liệu và storage business-level cho media import thật, metadata source/frame, bbox samples, nhãn hệ thống, nhãn custom, soft delete/restore, uniqueness tên nhãn và sample_count mà chưa sửa schema production.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

## Execution Brief

### Objective
Design the CR-004 database and storage contract for real object labeling media imports, frames, BBox samples, system/custom labels, soft delete/restore, uniqueness, and sample counts without changing production schema.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-020/TASK-PACKET.md`
- `.delivery/tasks/TASK-020/TASK-RESULT.md` if present
- `.delivery/tasks/TASK-020/DATABASE-DESIGN.md` if present
- `.delivery/REQUIREMENTS.md`
- `.delivery/DOMAIN-MODEL.md`
- `.delivery/changes/CR-004/CHANGE-IMPACT.md`
- `docs/contracts/db/schema.sql`
- `backend/database/models.py`
- `backend/database/repository.py`
- `.delivery/MASTER-PLAN.md` section `TASK-020 Thiết kế DB/Storage cho Object Labeling Thật`

### Allowed write scope
- Historical/planned task scope: `.delivery/tasks/TASK-020/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-020/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, production schema/code, runtime database files, `.delivery/tasks/TASK-020/TASK-RESULT.md`, `DATABASE-DESIGN.md`, bug/test-report artifacts, or unrelated delivery artifacts during packet normalization.

### Acceptance criteria
- Packet remains consistent with task id `TASK-020`, capability `database-design`, dependency `TASK-019`, linked requirements, expected outputs, and completion gate.
- Design is business-level and does not modify production schema.
- Contract covers media source import, frame metadata, bbox samples, system/custom labels, soft delete/restore, uniqueness by label name, sample_count semantics, and migration direction.

### Edge cases / risks
- Must distinguish system labels from user-created custom labels.
- Soft-deleted labels may still be referenced by historical samples.
- Large video/image imports can create storage and cleanup concerns.
- Not specified in source artifacts: exact filesystem/object-storage provider, max upload size, media retention policy, thumbnail strategy, and final migration SQL.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python D:\Skill\SKILLs\design-database\scripts\validate_database_design.py D:\Hilab\Project34 TASK-020`.
- Also review that no production schema/code files changed as part of the design task.

### Escalation conditions
- Escalate for breaking compatibility, security posture changes, material cost, destructive or hard-to-rollback migration, scope expansion, or impact to in-progress/completed work.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- Design summary.
- Validation evidence.
- Explicit note that production schema/code was not changed.
- Open risks/Not specified items.
- Blockers and scope-change requests.

### Skill/capability to run
- `database-design`.

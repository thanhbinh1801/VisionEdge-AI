---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T19:38:57+07:00"
task_id: TASK-021
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-021 Thiết kế API Upload/Source/Label/Sample/Frame/Sync

- Task ID: TASK-021
- Task type: feature-design
- Scope: feature
- Module: api-gateway
- Capability: api-design
- Linked requirements: REQ-005, REQ-007, CR-004
- Dependencies: TASK-020
- Write scope: .delivery/tasks/TASK-021/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/tasks/TASK-020/DATABASE-DESIGN.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, backend/app/api/v1/dataset.py, frontend/src/services/api.ts
- Expected outputs: .delivery/tasks/TASK-021/API-CONTRACT.md, .delivery/tasks/TASK-021/TASK-RESULT.md
- Completion gate: Thiết kế xong API feature contract cho upload/import media, dataset sources, custom label CRUD/soft delete/restore, bbox sample CRUD, video frame retrieval và sync zone rules, gồm schema request/response đủ để backend/frontend triển khai sau.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

## Execution Brief

### Objective
Design the CR-004 feature API contract for media upload/import, dataset sources, custom labels, BBox samples, video frame retrieval, and zone-rule synchronization.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-021/TASK-PACKET.md`
- `.delivery/tasks/TASK-021/TASK-RESULT.md` if present
- `.delivery/tasks/TASK-021/API-CONTRACT.md` if present
- `.delivery/REQUIREMENTS.md`
- `.delivery/tasks/TASK-020/DATABASE-DESIGN.md`
- `.delivery/API-CONTRACT.md`
- `docs/contracts/api/api-schema.json`
- `backend/app/api/v1/dataset.py`
- `frontend/src/services/api.ts`
- `.delivery/MASTER-PLAN.md` section `TASK-021 Thiết kế API Upload/Source/Label/Sample/Frame/Sync`

### Allowed write scope
- Historical/planned task scope: `.delivery/tasks/TASK-021/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-021/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/*`, production backend/frontend code, `.delivery/tasks/TASK-021/TASK-RESULT.md`, `.delivery/tasks/TASK-021/API-CONTRACT.md`, bug/test-report artifacts, or unrelated delivery artifacts during packet normalization.

### Acceptance criteria
- Packet remains consistent with task id `TASK-021`, capability `api-design`, dependency `TASK-020`, linked requirements, expected outputs, and completion gate.
- API contract includes request/response schemas for upload/import media, dataset source listing/detail, custom label CRUD/soft delete/restore, bbox sample CRUD, video frame retrieval, and sync zone rules.
- Design remains scoped to task artifacts and does not promote changes into global contracts during this step.

### Edge cases / risks
- Upload endpoints need validation for unsupported media types, partial batch failure, and duplicate label names.
- Sync zone rules must avoid accidentally enabling custom labels in AI realtime recognition.
- Not specified in source artifacts: authentication/authorization policy, exact multipart upload limits, resumable upload behavior, and CDN/static media serving strategy.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-021 --scope feature`.
- Validate local API draft/schema snippets for parseability when present.

### Escalation conditions
- Escalate for breaking compatibility, security posture changes, material cost, destructive migration implications, scope expansion, or impact to in-progress/completed work.

### Expected TASK-RESULT format
- Status/outcome.
- Inputs used.
- Outputs created.
- API design summary.
- Validation evidence.
- Compatibility and non-promotion notes.
- Open risks/Not specified items.
- Blockers and scope-change requests.

### Skill/capability to run
- `api-design`.

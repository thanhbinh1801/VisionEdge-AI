---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T20:00:59+07:00"
task_id: TASK-019
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Gói Task: TASK-019 — Verification cho CR-003 Realtime Area Metadata

- Mã task: TASK-019
- Loại task: verification
- Phạm vi: feature
- Module: none
- Năng lực: feature-verification
- Yêu cầu liên kết: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Phụ thuộc: TASK-017
- Phạm vi ghi: .delivery/tasks/TASK-019/
- Đầu vào: `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `.delivery/tasks/TASK-018/TASK-RESULT.md`, backend/frontend implementation under `backend/app/` and `frontend/src/`
- Đầu ra dự kiến: `.delivery/tasks/TASK-019/TEST-REPORT.md`, `.delivery/tasks/TASK-019/TASK-RESULT.md`, bug records if verification fails
- Điều kiện hoàn thành:
  - Xác minh không có DB read trong hot path mỗi frame.
  - Xác minh area metadata stream cập nhật realtime mà không phụ thuộc polling detections/events.
  - Xác minh event/alert lane vẫn đúng cho severity và notification.
- Chính sách phê duyệt: Project owner review required before promoting verification artifacts from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if verification requires repairing production code, changing approved contracts, or running unavailable external infrastructure.

## Execution Brief

### Objective
Verify CR-003 realtime area metadata end to end, including metadata stream freshness, hot-path DB avoidance, and compatibility with event/alert flows.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-019/TASK-PACKET.md`
- `.delivery/tasks/TASK-019/TASK-RESULT.md`
- `.delivery/tasks/TASK-019/TEST-REPORT.md`
- `.delivery/tasks/TASK-019/BUG-001.md` and `.delivery/tasks/TASK-019/BUG-002.md` if present
- `.delivery/tasks/TASK-016/API-CONTRACT.md`
- `.delivery/tasks/TASK-016/TASK-RESULT.md`
- `.delivery/tasks/TASK-017/TASK-RESULT.md`
- `.delivery/tasks/TASK-018/TASK-RESULT.md`
- Backend/frontend implementation under `backend/app/` and `frontend/src/`
- `.delivery/MASTER-PLAN.md` section `TASK-019 Verification cho CR-003 Realtime Area Metadata`

### Allowed write scope
- Historical task scope: `.delivery/tasks/TASK-019/`.
- Current packet-normalization scope: only `.delivery/tasks/TASK-019/TASK-PACKET.md`.

### Forbidden scope
- Do not edit `.delivery/MASTER-PLAN.md`, `.delivery/tasks/TASK-019/TASK-RESULT.md`, `TEST-REPORT.md`, `BUG-*.md`, production backend/frontend code, contracts, runtime DB files, or unrelated delivery artifacts.

### Acceptance criteria
- Packet remains consistent with task id `TASK-019`, verification task type, expected outputs, and completion gate.
- Verification covers realtime metadata stream updates, no per-frame DB reads in area-monitoring hot path, event/alert compatibility, and zone settings refresh before monitoring.
- Preserve historical facts: TASK-RESULT recorded completed outcome but also `Verdict: failed`; do not rewrite that contradiction during packet normalization.

### Edge cases / risks
- MASTER-PLAN status is `needs-revision`; existing bug records and failed verdict must be preserved.
- Historical DB rows were not backfilled and clip slicing was placeholder-based per TASK-RESULT addendum.
- Verification may need production fixes, which are outside verification task scope.
- Not specified in source artifacts: manual browser QA script, exact latency threshold, and real 10-second decoded clip validation criteria.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-019`.
- Historical evidence includes backend scoped pytest, frontend lint/typecheck/build, schema trace review, DB inspection, and zone refresh probe; preserve exact results from TASK-RESULT/TEST-REPORT.

### Escalation conditions
- Escalate if verification requires repairing production code, changing approved contracts, running unavailable external infrastructure, or resolving contradictory verdict/status semantics.

### Expected TASK-RESULT format
- Status/outcome and verdict.
- Inputs used.
- Outputs created.
- Verification matrix with command evidence.
- Bugs filed or revalidated.
- Deviations and caveats.
- Blockers and scope-change requests.

### Skill/capability to run
- `verify-feature`.

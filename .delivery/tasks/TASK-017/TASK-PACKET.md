---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-20T19:32:23+07:00"
task_id: TASK-017
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md]
---

# Task Packet: TASK-017 — Backend Area Metadata Lane và Zone Cache

- Task ID: TASK-017
- Task type: implementation
- Scope: feature
- Module: ai-vision-pipeline
- Capability: backend-implementation
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Dependencies: TASK-016
- Write scope: .delivery/tasks/TASK-017/
- Inputs: `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `backend/app/api/v1/events.py`, `backend/app/api/v1/zones.py`, `backend/app/api/v1/websocket.py`, `backend/app/services/video_stream.py`, `backend/app/services/vision_pipeline.py`, `backend/database/repository.py`
- Expected outputs: `backend/app/services/zone_cache.py`, `backend/app/services/area_metadata.py`, backend runtime updates under `backend/app/api/v1/` and `backend/app/services/`, backend tests, `.delivery/tasks/TASK-017/TASK-RESULT.md`
- Completion gate: Frame loop area monitoring không đọc DB mỗi frame; zone rules được lấy từ in-memory cache theo `camera_id`; metadata realtime và event persistence được tách lane rõ ràng.
- Approval policy: Project owner review required before promoting `TASK-RESULT.md` from `in-review` to `approved`.
- Escalation policy: Escalate only if implementation requires changing approved contracts, database schema, frontend code, or files outside backend scope plus `.delivery/tasks/TASK-017/`.

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

# Gói Task: TASK-017 — Backend Area Metadata Lane và Zone Cache

- Mã task: TASK-017
- Loại task: implementation
- Phạm vi: feature
- Module: ai-vision-pipeline
- Năng lực: backend-implementation
- Yêu cầu liên kết: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Phụ thuộc: TASK-016
- Phạm vi ghi: .delivery/tasks/TASK-017/
- Đầu vào: `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `backend/app/api/v1/events.py`, `backend/app/api/v1/zones.py`, `backend/app/api/v1/websocket.py`, `backend/app/services/video_stream.py`, `backend/app/services/vision_pipeline.py`, `backend/database/repository.py`
- Đầu ra dự kiến: `backend/app/services/zone_cache.py`, `backend/app/services/area_metadata.py`, backend runtime updates under `backend/app/api/v1/` and `backend/app/services/`, backend tests, `.delivery/tasks/TASK-017/TASK-RESULT.md`
- Điều kiện hoàn thành: Frame loop area monitoring không đọc DB mỗi frame; zone rules được lấy từ in-memory cache theo `camera_id`; metadata realtime và event persistence được tách lane rõ ràng.
- Chính sách phê duyệt: Project owner review required before promoting `TASK-RESULT.md` from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if implementation requires changing approved contracts, database schema, frontend code, or files outside backend scope plus `.delivery/tasks/TASK-017/`.

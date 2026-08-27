---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-030
owner: design-api
status: approved
updated_at: "2026-08-27T20:13:59+07:00"
---

# Kết quả Task: TASK-030 — CR-007 Area Detection, BBox Debug và Zone Evaluation

- Task ID: TASK-030
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-030/TASK-PACKET.md`, `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `.delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md`, `.delivery/changes/CR-007/CHANGE-IMPACT.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`, `backend/app/api/v1/events.py`, `backend/app/services/vision_pipeline.py`, `backend/app/services/video_stream.py`, `backend/app/services/area_metadata.py`, `frontend/src/services/api.ts`, `frontend/src/pages/AreaSecurityDashboard.tsx`.
- Outputs produced: `.delivery/tasks/TASK-030/API-CONTRACT.md`, `.delivery/tasks/TASK-030/TASK-RESULT.md`.
- Validation evidence: `python -m json.tool docs/contracts/api/api-schema.json` exit code 0; `python -m json.tool docs/contracts/api/websocket-events.json` exit code 0; `python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-030` exit code 0 sau khi tạo artifact.
- Deviations: Không sửa `.delivery/API-CONTRACT.md`, `docs/contracts/api/*.json`, requirements, architecture, ADR hoặc production code vì TASK-030 chỉ được ghi trong `.delivery/tasks/TASK-030/`. Contract ghi rõ các điểm implementation hiện chưa khớp như `/video-feed` default `0.50`, hard-code ẩn container và metadata thiếu debug fields để TASK-031 xử lý.
- Blockers: none
- Scope change requests: none

## Tóm tắt thiết kế

- Chốt `/api/v1/events/video-feed` là video stream lane; `conf_threshold` chỉ là display/debug threshold và thêm `show_static_containers=false` để bật/tắt bbox container khi debug.
- Giữ `/api/v1/events/live-detections` là endpoint legacy/debug trả direct array; mọi field CR-007 thêm vào phải optional/additive.
- Mở rộng `AREA_FRAME_METADATA` bằng các field `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`, `track_id` optional mà không đổi required fields từ TASK-016.
- Chuẩn hóa class-aware zone evaluation: bottom-center cho người/xe máy/xe đạp, footprint overlap cho nhóm xe/máy móc, bbox overlap ratio riêng cho container/shipping_container.
- Khẳng định metadata lane và bbox stream không tự sinh audio/popup/Telegram; event/alert lane chỉ nhận object đã qua application/per-class threshold, stability ngắn và cooldown.

---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-019
owner: verify-feature
status: approved
updated_at: "2026-08-21T11:17:39+07:00"
---

# Kết quả Task: TASK-019 — Verification cho CR-003 Realtime Area Metadata

- Mã task: TASK-019
- Kết quả: completed
- Outcome: completed
- Đầu vào đã dùng: `.delivery/tasks/TASK-019/TASK-PACKET.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-016/TASK-RESULT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `.delivery/tasks/TASK-018/TASK-RESULT.md`, backend/frontend implementation files under `backend/app/` and `frontend/src/`.
- Đầu ra đã tạo: `.delivery/tasks/TASK-019/TEST-REPORT.md`, `.delivery/tasks/TASK-019/TASK-RESULT.md`, `.delivery/tasks/TASK-019/BUG-001.md`.
- Bằng chứng xác minh: reran backend scoped pytest (`14 passed in 0.43s`), frontend lint/typecheck (both exit 0), frontend production build outside sandbox (success), schema trace review between backend `/events` response model and frontend event feed consumer, DB inspection for existing `ZONE_VIOLATION` rows, static trace for violation persistence from live-detections/WebSocket metadata lanes, and scoped event persistence regressions (`11 passed, 10 warnings in 25.61s`).
- Additional validation evidence on August 23, 2026: zone settings refresh probe passed (`19 passed, 13 warnings in 38.61s`) and confirmed that changing `BAI-KIEM` zone vertices plus `allowed_classes`/`forbidden_classes` refreshes runtime cache/pipeline state before `Giám sát khu vực` streams frames.
- Sai lệch: Verification used code inspection plus local command evidence; no production code was changed in this task.
- Điểm chặn: none
- Yêu cầu đổi phạm vi: none
- Verdict: failed

## Addendum 2026-08-21 - Event DB and 10s Clip Handoff

- Specific check result: passed for current code path.
- DB inspection found one existing severity-3 `ZONE_VIOLATION` row in `sentri_ai.db`.
- Current implementation writes new violations through `_persist_violation_event`, including `bbox` and `video_clip_url`.
- Current live-detections and WebSocket metadata paths both call the shared persistence flow.
- Current 10s clip handoff creates `/media/clips/clip_<camera>_<timestamp>.mp4` via `EventManager.slice_10s_ring_buffer_clip`, suitable as a future chatbot retrieval URL/file.
- Caveat: the existing historical DB row still points to `/videos/KiemHoa-Hik (1).mp4`; it was not backfilled. The current clip file is placeholder-based, not a real decoded 10-second slice.

## Addendum 2026-08-23 - Zone Settings Refresh Before Area Monitoring

- Specific check result: passed.
- The verification changed a `BAI-KIEM` zone's polygon vertices, `allowed_classes`, and `forbidden_classes`.
- Backend `PUT /zones/{zone_id}` refreshed `zone_cache_service` and called `pipeline.update_zones` with the updated zone payload and incremented `zone_version`.
- The subsequent `events.video_feed(camera_id="BAI-KIEM", draw_zones=False, db=...)` path used by `Giám sát khu vực` called `pipeline.update_zones` with the same refreshed vertices/classes and `zone_version`.
- Conclusion: after editing zone position and vehicle/object allow/deny rules, opening `Giám sát khu vực` uses the new backend runtime settings.

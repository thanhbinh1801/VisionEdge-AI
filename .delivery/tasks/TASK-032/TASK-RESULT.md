---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-032
owner: implement-frontend
status: approved
updated_at: "2026-08-27T20:38:18+07:00"
---

# Kết quả TASK-032 - Frontend Debug Controls và Type Surface cho Area Dashboard

- Task ID: TASK-032
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-032/TASK-PACKET.md`, `.delivery/tasks/TASK-030/API-CONTRACT.md`, `.delivery/tasks/TASK-030/TASK-RESULT.md`, `.delivery/tasks/TASK-031/TASK-RESULT.md`, `.delivery/API-CONTRACT.md`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `frontend/package.json`.
- Outputs produced: frontend Area Dashboard/type updates, `.delivery/tasks/TASK-032/TASK-RESULT.md`.
- Validation evidence: `npx --prefix frontend tsc --noEmit` exit code 1 vì trên Windows lệnh này in help TypeScript thay vì dùng project config; dùng project-equivalent `npm --prefix frontend run lint` đạt exit code 0 với `tsc --noEmit`; `npm --prefix frontend run build` lần đầu trong sandbox lỗi `spawn EPERM` khi Vite/esbuild khởi động process; chạy lại ngoài sandbox theo approval đạt exit code 0, `840 modules transformed`, build thành công trong `2.48s`, chỉ còn cảnh báo chunk lớn hơn `500 kB` của Vite.
- Deviations: Không sửa backend, Gate Dashboard, LPR/GATE-01 flow, event/alert behavior, schema database, migration, aggregate API contract, requirements, architecture hoặc master plan. `npx --prefix frontend tsc --noEmit` không dùng được đúng project config trong môi trường này nên đã dùng script `npm --prefix frontend run lint` tương đương do repo định nghĩa.
- Blockers: none
- Scope change requests: none
- Changed files: `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `.delivery/tasks/TASK-032/TASK-RESULT.md`.
- Tests changed: Không có test frontend hiện hữu được thêm mới; xác minh bằng TypeScript typecheck và production build theo `frontend/package.json`.
- Commands run: `npx --prefix frontend tsc --noEmit`; `npm --prefix frontend run lint`; `npm --prefix frontend run build`; `python D:\Skill\SKILLs\framework\scripts\current_timestamp.py`; `python D:\Skill\SKILLs\implement-frontend\scripts\validate_frontend_implementation.py D:\Hilab\Project34 TASK-032`.

## Tóm tắt triển khai

- Mở rộng `AreaMetadataObject` để chấp nhận các field additive CR-007: `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`, `track_id` optional/null và metadata zone hit tương ứng.
- Mở rộng `LiveDetection` và `getVideoFeedUrl()` để truyền `conf_threshold` và `show_static_containers` mà vẫn giữ call cũ backward-compatible.
- Thêm control debug trên Area Dashboard cho ngưỡng bbox và bật/tắt container tĩnh; default giữ `show_static_containers=false`.
- Metadata chip ưu tiên tên hiển thị/nhãn tiếng Việt theo `canonical_class`, giữ `raw_class`, method đánh giá zone, overlap ratio, `track_id` hoặc `detection_frame_id` để debug khi backend gửi về.
- Không tạo event/alert/audio/popup/Telegram từ metadata hoặc bbox debug lane.

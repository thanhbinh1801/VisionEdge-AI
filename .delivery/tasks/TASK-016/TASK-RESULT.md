---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-016
owner: design-api
status: approved
updated_at: "2026-08-20T18:50:16+07:00"
---

# Kết quả Task: TASK-016 — Realtime Metadata Contract cho Area Monitoring

- Mã task: TASK-016
- Kết quả: completed
- Outcome: completed
- Đầu vào đã dùng: `.delivery/tasks/TASK-016/TASK-PACKET.md`, `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `.delivery/changes/CR-003/CHANGE-IMPACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`, `backend/app/api/v1/websocket.py`, `backend/app/api/v1/zones.py`, `frontend/src/services/websocket.ts`, `frontend/src/services/api.ts`, `frontend/src/pages/AreaSecurityDashboard.tsx`.
- Đầu ra đã tạo: `.delivery/tasks/TASK-016/API-CONTRACT.md` (feature contract cho `AREA_FRAME_METADATA`, zone cache semantics, response envelopes, error model, compatibility notes). Các bản draft JSON ban đầu đã được thay thế bởi `docs/contracts/api/api-schema.json` và `docs/contracts/api/websocket-events.json`.
- Bằng chứng xác minh: So khớp contract với `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009` và `CR-003`; đối chiếu consumer hiện tại backend/frontend để xác định migration constraints; packet được chuẩn hóa theo task-packet contract; validator chuyên biệt cho `TASK-016` pass; contract JSON chính thức trong `docs/contracts/api/` parse hợp lệ và đã chứa phần CR-003.
- Sai lệch: Không sửa `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/*`, hoặc source ứng dụng; chỉ ghi artifact trong `.delivery/tasks/TASK-016/`.
- Điểm chặn: none
- Yêu cầu đổi phạm vi: none

## Design summary

- Chọn phương án additive event type `AREA_FRAME_METADATA` trên `/ws/v1/events`, không tạo channel riêng trong phạm vi `TASK-016`.
- Chốt `Area Security Dashboard` dùng metadata lane làm nguồn truth cho overlay/KPI; event lane tiếp tục phục vụ event feed và alert đã dedup.
- Chuẩn hóa `zone_version` và lỗi `ZONE_CACHE_REFRESH_FAILED` để ràng buộc cache invalidation là một phần của success semantics cho CRUD zone.

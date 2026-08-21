---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-018
owner: implement-frontend
status: in-review
updated_at: "2026-08-20T21:42:00+07:00"
---

# Task Result: TASK-018 — Frontend Area Dashboard consume Realtime Metadata Riêng

- Task ID: TASK-018
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-018/TASK-PACKET.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, `.delivery/tasks/TASK-017/TASK-RESULT.md`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/services/api.ts`, `frontend/src/services/websocket.ts`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/types/index.ts`, `frontend/src/context/AppContext.tsx`.
- Outputs produced: metadata-lane aware `AreaSecurityDashboard`, typed realtime WebSocket client for `/ws/v1/events`, zone envelope-compatible API client updates, extended frontend types for `AREA_FRAME_METADATA`, lifecycle hardening cho WebSocket client/hook để giam reconnect khong can thiet sau cleanup chu dong, `.delivery/tasks/TASK-018/TASK-RESULT.md`.
- Validation evidence: `npm run lint` exit 0; `npx tsc --noEmit` exit 0; `cmd /c npm run build > build-output.log 2>&1` trong sandbox exit 1 với `spawn EPERM` khi Vite/esbuild spawn process.
- Changed files: `frontend/src/services/websocket.ts`, `frontend/src/hooks/useWebSocket.ts`, `.delivery/tasks/TASK-018/TASK-RESULT.md`.
- Tests changed: Không thêm test file vì repo frontend hiện không có test runner/unit test script; verification dùng strict TypeScript, lint script và Vite build attempt để khóa integration regression trong phạm vi task.
- Commands run: `npm run lint` (exit 0); `npx tsc --noEmit` (exit 0); `cmd /c npm run build > build-output.log 2>&1` trong sandbox (exit 1, `spawn EPERM` từ `esbuild`).
- Deviations: Không chỉnh backend hoặc approved contracts; event feed vẫn giữ lane riêng qua `fetchLatestEvents`, còn metadata lane mới chịu trách nhiệm cập nhật overlay/KPI/stream insight cho Area Dashboard.
- Blockers: Sandbox Windows hien tai khong cho phep `esbuild` spawn trong buoc Vite build (`spawn EPERM`), nen khong co build artifact moi trong lan verify nay.
- Scope change requests: none

## Implementation summary

- Chuyển `AreaSecurityDashboard` từ polling `fetchLiveDetections` sang consume `AREA_FRAME_METADATA` qua WebSocket `/ws/v1/events`.
- Giữ MJPEG làm video renderer riêng, đồng thời thêm overlay bbox client-side từ metadata lane để tách nguồn hiển thị metadata khỏi event/history lane.
- Bổ sung trạng thái metadata (`connecting/online/degraded/offline`), `zone_version`, `pipeline_latency_ms`, và snapshot chips để người vận hành nhìn thấy realtime lane đang hoạt động.
- Cập nhật API zone client để hiểu response envelope mới của backend `TASK-017`, tránh làm vỡ zone bootstrap và zone CRUD flow trong UI hiện tại.
- Ghim vong doi WebSocket theo `cameraId` thay vi theo moi render callback, dung `ref` de cap nhat event handler ma khong teardown socket dang song.
- Chan auto-reconnect sau khi UI chu dong `disconnect()` va tranh lap reconnect timer chong len nhau khi socket dong/mount lai.

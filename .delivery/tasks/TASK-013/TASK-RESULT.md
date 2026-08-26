---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-013
owner: implement-frontend
status: in-review
updated_at: "2026-08-25T11:37:43+07:00"
---

# Kết quả Task: TASK-013 - AI Chatbot Assistant (Frontend)

- Task ID: TASK-013
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-013/TASK-PACKET.md` (revision 2), `.delivery/REQUIREMENTS.md` (REQ-008), `.delivery/tasks/TASK-011/TASK-RESULT.md`, `backend/app/api/v1/assistant.py`, `frontend/src/components/common/VideoModal.tsx`, `frontend/src/services/api.ts` (tham chiếu quy ước `API_BASE_URL`).
- Outputs produced: trang Chatbot gọi API thật `POST /api/v1/assistant/query`, thanh Prompt Chips có icon Lucide, nhúng `<VideoModal>` phát clip 10s và nút tải clip, đủ các trạng thái loading/empty/error/success.
- Changed files: `frontend/src/pages/AIChatbotAssistant.tsx`.
- Tests changed: none — dự án không có test runner frontend (`package.json` chỉ có `dev`, `build`, `lint`, `preview`). Xác minh bằng `tsc --noEmit` và `vite build`.
- Commands run: `npm run lint` (`tsc --noEmit`) — lượt 1 hỏng vì môi trường (`'tsc' is not recognized`), lượt 2 `LINT_EXIT=0`; `npm ci` (khôi phục `node_modules`, `added 175 packages`, exit 0); `npm run build` (`2279 modules transformed`, `built in 24.94s`, `BUILD_EXIT=0`).
- Validation evidence: `tsc --noEmit` exit 0 và `vite build` exit 0 sau khi khôi phục môi trường. Đối chiếu hợp đồng hai đầu: frontend gọi `${API_BASE_URL}/assistant/query`, backend đăng ký `include_router(assistant.router, prefix="/assistant")` dưới `/api/v1` → khớp `/api/v1/assistant/query`; bốn trường `answer`, `sql_query`, `event_id`, `clip_url` khớp đúng tên giữa `QueryResponse` (backend) và `AssistantAnswer` (frontend). Bundle 645.84 kB → 650.86 kB (+5 kB, do thêm icon Lucide và trang mới).
- Deviations: xem mục "Sai lệch" bên dưới.
- Blockers: none
- Scope change requests: none

## Nội dung triển khai

- **Gọi API thật thay mock.** Trang không còn dùng `sendChatMessage` của `AppContext` (vốn tra bảng cứng `qaKnowledgeBase`), mà `fetch` thẳng tới `POST /api/v1/assistant/query` và quản lý danh sách tin nhắn bằng state cục bộ.
- **Prompt Chips** với icon Lucide (`ShieldAlert`, `Car`, `Truck`) theo acceptance criteria 3 của REQ-008. `lucide-react` đã có sẵn trong `package.json`, không thêm dependency.
- **Chứng cứ clip 10s**: khi phản hồi có `clip_url`, hiện nút "Xem clip 10s" mở `<VideoModal>` và link "Tải clip" (`<a download>`), kèm mã sự kiện `event_id`. Không có `clip_url` thì không dựng thẻ video rỗng.
- **Các trạng thái**: loading (spinner "Đang tra cứu sự kiện…", khoá input và chips), success, empty (hiển thị nguyên văn câu trả lời "không có sự kiện nào" của backend), error (bong bóng đỏ riêng, `role="alert"`, kèm mã HTTP).
- **Accessibility**: `role="log"` + `aria-live="polite"` cho khung hội thoại, `role="group"` cho cụm chips, `aria-label` cho input/nút gửi/nút xem/nút tải, `role="alert"` cho lỗi, và trạng thái `disabled` phản ánh đúng bằng con trỏ lẫn độ mờ.
- **Minh bạch truy vấn**: `sql_query` hiện trong `<details>` thu gọn để người dùng kiểm chứng câu trả lời đến từ truy vấn nào.

## Sai lệch

- **Lời gọi API nằm trong trang, không nằm trong `services/api.ts`.** Quy ước repo là gom fetch vào `api.ts`, nhưng file đó ngoài write scope của TASK-013 (`Expected outputs` chỉ có `frontend/src/pages/AIChatbotAssistant.tsx`). Chọn giữ đúng write scope thay vì mở rộng. Đề xuất follow-up: chuyển `askAssistant()` sang `api.ts` cho đồng nhất.
- **`AppContext.sendChatMessage` và `qaKnowledgeBase` vẫn còn trong `AppContext.tsx`** nhưng trang này không dùng nữa. File đó ngoài write scope nên không gỡ. Đây là mã chết cần dọn ở một task riêng, nếu không sẽ có hai nguồn trả lời song song gây nhầm lẫn.
- **Nút tải clip đặt trong bong bóng tin nhắn, không đặt trong `VideoModal`.** `VideoModal.tsx` hiện chưa có nút tải và nằm ngoài write scope. Đặt trong tin nhắn vẫn thoả acceptance criteria 2 của REQ-008 ("kèm ... và nút tải xuống") mà không vượt phạm vi.
- **Bbox highlight trong clip chưa có.** Acceptance criteria 2 của REQ-008 yêu cầu clip "có bbox highlight đối tượng". `VideoModal` chỉ phát thẳng `video_clip_url` do backend trả về; muốn có bbox thì phải vẽ overlay trong `VideoModal` (ngoài write scope) hoặc backend phải burn-in bbox khi cắt clip. Cần một task riêng.
- Hướng dẫn RSC/`'use client'` trong skill không áp dụng: đây là SPA Vite + React 18, không phải Next.js, không có Server Component.

## Sự cố môi trường trong lúc thực hiện

Lượt lint đầu hỏng với `'tsc' is not recognized`. Nguyên nhân không phải mã nguồn: `frontend/node_modules` bị rỗng (0 entry) do junction `ve-merge/frontend/node_modules` trỏ vào `node_modules` thật, và lệnh `git worktree remove ../ve-merge --force` đã xoá xuyên qua junction. Khôi phục bằng `npm ci` từ `package-lock.json` (175 packages, exit 0); `git status` xác nhận `package.json` và `package-lock.json` không thay đổi, tức không có dependency nào bị đổi phiên bản. Mã nguồn không mất file nào (`src/` đủ 24 file).

---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-009
owner: implement-frontend
status: approved
updated_at: "2026-08-26T10:49:56+07:00"
---

# Kết quả Task: TASK-009 — Triển khai Tab 1 Gate Dashboard (LPR Cổng)

- Task ID: TASK-009
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-009/TASK-PACKET.md`, `.delivery/MASTER-PLAN.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `docs/contracts/api/websocket-events.json`, `frontend/src/services/api.ts`, `frontend/src/context/AppContext.tsx`, `frontend/src/types/index.ts`.
- Outputs produced: `frontend/src/pages/GateDashboard.tsx` — sửa sai lệch tham số live-detections, khôi phục khả năng tự phục hồi của vòng lặp nhận diện, và bổ sung trạng thái lỗi cho lane sự kiện LPR.
- Validation evidence: `npm run lint` (`tsc --noEmit`) exit 0; `npm run build` exit 0 với 839 modules transformed, `dist/assets/index-DCnpDvMB.js` 646.89 kB (gzip 180.49 kB), built in 20.95s; `git diff --check` exit 0.
- Changed files: `frontend/src/pages/GateDashboard.tsx` (79 insertions, 20 deletions).
- Tests changed: không thêm test file — `frontend/package.json` không khai báo script `test` và repo không có test runner frontend. Regression được kiểm bằng strict TypeScript compile và production Vite build.
- Commands run: `npm run lint` (exit 0); `npm run build` (exit 0); `git diff --stat -- frontend/src/pages/GateDashboard.tsx`; `git diff --check -- frontend/src/pages/GateDashboard.tsx` (exit 0).
- Deviations: xem mục `Sai lệch so với packet` bên dưới — input foundation lệch đường dẫn, write scope lấy theo MASTER-PLAN thay vì packet.
- Blockers: none
- Scope change requests: none

## Trạng thái trước khi làm

`frontend/src/pages/GateDashboard.tsx` đã tồn tại từ trước với đầy đủ layout: viewport stream `GATE-01`, 4 thẻ KPI Recharts (`AreaChart`, `BarChart`, `LineChart`, `RadialBarChart`), overlay SVG polygon zone, bbox realtime, pills quy tắc 8 loại đối tượng và danh sách biển số. Task chưa từng có `TASK-PACKET.md`/`TASK-RESULT.md`, nên phần chưa hoàn tất là artifact bàn giao cộng ba defect phát hiện khi rà soát theo completion gate.

## Defect đã sửa

### 1. Tham số `fetchLiveDetections` bị lệch vị trí — bbox không bám khung hình

`GateDashboard.tsx` gọi `fetchLiveDetections(CAMERA_ID, at)` trong khi chữ ký tại `frontend/src/services/api.ts:377` là `fetchLiveDetections(cameraId, confThreshold = 0.35, videoTime?)`.

Hậu quả: `video.currentTime` (ví dụ `12.5`) được gửi lên backend làm `conf_threshold`, còn `video_time` không bao giờ được gửi. Ngưỡng tin cậy trở thành giá trị vô nghĩa tăng dần theo thời gian phát, và backend suy luận trên frame nó tự đọc được thay vì frame đang hiển thị — đúng thứ mà comment ngay phía trên lời gọi tuyên bố là đang tránh.

TypeScript không bắt được lỗi này vì tham số có giá trị mặc định nên nhận `number | undefined` hợp lệ.

Sửa: thêm hằng `DETECTION_CONF_THRESHOLD = 0.35` và gọi đúng `fetchLiveDetections(CAMERA_ID, DETECTION_CONF_THRESHOLD, at)`.

### 2. Vòng lặp detection chết vĩnh viễn sau một lần lỗi

`fetchLiveDetections` ném lỗi khi response không `ok`. Hàm `tick()` không có `try/catch`, và lệnh `timer = window.setTimeout(tick, DETECTION_GAP_MS)` nằm sau `await`. Một nhịp backend lỗi khiến promise reject trước khi kịp hẹn lượt kế tiếp — vòng lặp nhận diện dừng hẳn cho đến khi người dùng tải lại trang.

Sửa: bọc `try/catch/finally`; lượt kế tiếp được hẹn trong `finally` nên vòng lặp tự phục hồi. Khi lỗi, bbox của lần thành công gần nhất được giữ nguyên thay vì xoá trắng, và `detectionError` được đặt để UI hiển thị.

### 3. UI kẹt ở trạng thái "Đang tải" khi backend lỗi

`fetchLatestEvents` (`api.ts:235`) cũng ném lỗi khi response không `ok`. `loadBackendData()` không có `try/catch` nên `setIsLoading(false)` không bao giờ chạy. Panel biển số kẹt ở "Đang tải dữ liệu nhận diện từ GATE-01…" vĩnh viễn, các thẻ KPI kẹt ở `…`, và cả trạng thái rỗng lẫn cảnh báo mất đồng bộ đều không thể hiển thị.

Sửa: bọc `try/catch/finally`; `setIsLoading(false)` chạy trong `finally`. Thêm `eventsError` và banner `role="alert"` phân biệt hai tình huống: còn dữ liệu cũ thì báo đang hiển thị lần đồng bộ gần nhất, chưa có dữ liệu thì hướng dẫn kiểm tra backend cổng 8000.

## Trạng thái UI được bảo toàn

- Loading: KPI hiện `…`, panel biển số hiện thông báo tải, `aria-busy` trên danh sách.
- Empty: `isEmpty` được siết thành `!isLoading && !eventsError && events.length === 0` để lỗi tải không bị hiển thị nhầm thành "chưa có dữ liệu".
- Error: banner `role="alert"` cho lane sự kiện; chip "AI gián đoạn · đang thử lại" cạnh chỉ báo trực tiếp cho lane detection; màn hình dự phòng khi `<video>` lỗi.
- Stale: chỉ báo chuyển "MẤT ĐỒNG BỘ" khi quá `STALE_AFTER_MS`.
- Accessibility: giữ nguyên `role="group"`/`aria-label` cụm KPI, `role="status" aria-live="polite"` cho chỉ báo trực tiếp, `aria-pressed` trên pills quy tắc và nút chọn zone, `aria-hidden` trên biểu đồ trang trí.
- Responsive: giữ nguyên breakpoint `NARROW_BREAKPOINT = 980`, đọc `window` chỉ bên trong `useEffect` nên lần render đầu vẫn tất định.

## Sai lệch so với packet

- Packet ghi `Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md`. Hai file này không tồn tại trong repo. `.delivery/tasks/TASK-002/TASK-RESULT.md` và `.delivery/tasks/TASK-004/TASK-RESULT.md` ghi rõ foundation đã được tái lập vào `.delivery/API-CONTRACT.md` + `docs/contracts/api/*.json` và vào chính styling assets đang chạy. Đã dùng các artifact đã duyệt này làm input thay thế; nội dung hợp đồng có đủ, chỉ lệch đường dẫn.
- Packet ghi `Write scope: .delivery/tasks/TASK-009/` do script `prepare_task.py` sinh cứng, mâu thuẫn với `Expected outputs: frontend/src/pages/GateDashboard.tsx`. Đã theo cột `Write scope` của `.delivery/MASTER-PLAN.md` (`frontend/src/pages/GateDashboard.tsx`) và không ghi ra file nào ngoài file đó cộng artifact task này.
- Không sửa `frontend/src/services/api.ts` dù defect 1 bắt nguồn từ chữ ký hàm ở đó — file này thuộc write scope của TASK-010/TASK-012. Toàn bộ sửa chữa nằm gọn trong phía gọi.
- Không đổi API contract, backend, MASTER-PLAN hay bất kỳ aggregate artifact nào.

## Ghi chú kiểm chứng

Repo không có test runner frontend (`package.json` chỉ có `dev`, `build`, `lint`, `preview`; `lint` thực chất là `tsc --noEmit`). Không thể chạy scoped component test theo bước 8 của skill. Verification dựa trên strict TypeScript compile và production build, cùng cách TASK-010/TASK-012 đã dùng.

Ba defect trên là lỗi runtime chỉ xuất hiện khi backend trả lỗi hoặc khi so đối chiếu chữ ký hàm — không lỗi nào bị `tsc` bắt, nên baseline trước khi sửa cũng pass lint. Chưa chạy được kiểm chứng runtime với backend thật trong phiên này.

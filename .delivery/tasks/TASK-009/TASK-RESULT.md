---
artifact: TASK-RESULT.md
version: 1.1.0
task_id: TASK-009
owner: implement-frontend
status: in-review
updated_at: "2026-08-20T15:47:56+07:00"
---

# Task Result: TASK-009 — Triển khai Tab 1 — Gate Dashboard (LPR Cổng)

- Task ID: TASK-009
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-009/TASK-PACKET.md`, `.delivery/tasks/TASK-002/API-FOUNDATION.md`, `.delivery/tasks/TASK-004/UI-UX-FOUNDATION.md`, `.delivery/MASTER-PLAN.md` (v1.9.0, approved), `docs/contracts/api/api-schema.json`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `frontend/src/pages/AreaSecurityDashboard.tsx` (mẫu tham chiếu polling + video + SVG overlay), kết quả đã duyệt của TASK-007 và TASK-008.
- Outputs produced: `frontend/src/pages/GateDashboard.tsx` (viết lại hoàn chỉnh, 4 biểu đồ KPI Recharts + luồng video GATE-01 + polling LPR realtime + BBox overlay).
- Changed files: `frontend/src/pages/GateDashboard.tsx` (trong write scope kế hoạch); `frontend/src/context/AppContext.tsx` (1 dòng, ngoài scope — đã được project owner phê duyệt mở rộng, xem Deviations).
- Tests changed: Không có test runner nào được cài trong `frontend/` (không có vitest/jest/testing-library trong `package.json`), nên không thể thêm unit test cho component mà không mở rộng write scope sang `package.json` + file cấu hình. Kiểm chứng thay thế bằng `tsc --noEmit` (exit 0), `vite build` (exit 0) và probe API thật trên backend đang chạy (bằng chứng bên dưới). Xem "Scope change requests".
- Commands run: `npm --prefix frontend run lint`, `npm --prefix frontend run build`, `npx vite build`, `curl` các endpoint backend đang chạy.
- Validation evidence:
  - `npm --prefix frontend run lint` (`tsc --noEmit`) → **exit 0**, không còn lỗi. Trước khi sửa: `src/context/AppContext.tsx(320,48): error TS7006: Parameter 'k' implicitly has an 'any' type.` → exit 2 (lỗi có sẵn từ trước, không do TASK-009 gây ra).
  - `npm --prefix frontend run build` (**verification method của kế hoạch**) → **exit 0**; `836 modules transformed`, `dist/assets/index-DHlvit6A.js 627.12 kB │ gzip: 173.56 kB` (kích thước tăng xác nhận Recharts đã được bundle).
  - `npx vite build` chạy riêng khi tsc còn lỗi → exit 0, xác nhận component tự nó bundle sạch.
  - Backend thật (`python main.py`, port 8000) — các endpoint mà trang tiêu thụ:
    - `GET /health` → `200`
    - `GET /videos/GATE_01.mp4` (range request) → `206` — luồng camera GATE-01 phát được.
    - `GET /api/v1/zones?camera_id=GATE-01` → 2 zone (`Làn IN 1`, `Làn IN 2`) với `vertices` dạng `{x, y}` %; khớp bộ ánh xạ của `fetchZones`.
    - `GET /api/v1/events/live-detections?camera_id=GATE-01` → 3 detection, `bbox` dạng `[left, top, width, height]` % — khớp đúng hợp đồng overlay BBox đã triển khai.
    - `GET /api/v1/events?camera_id=GATE-01&limit=3` → `[]` — đường dẫn empty state được kích hoạt thật (xem Deviations về LPR).

## Nội dung đã triển khai

- **Luồng camera GATE-01 thật**: thay nền gradient giả bằng `<video src="/videos/GATE_01.mp4" autoPlay loop muted playsInline>`, kèm error state khi không tải được tệp.
- **LPR realtime**: polling `fetchLatestEvents('GATE-01', 20)` + `fetchLiveDetections('GATE-01')` mỗi 3s (cùng nhịp với `AreaSecurityDashboard`), ánh xạ `license_plate` / `confidence` / `timestamp` / `zone_name` sang dòng biển số. Trước đây trang đọc `gateEvents` từ `AppContext` — biến này khai báo `const [gateEvents] = useState([])` không có setter nên **vĩnh viễn rỗng**; nay dữ liệu lấy trực tiếp từ backend.
- **BBox overlay động**: vẽ theo detection thật từ AI Vision Pipeline (thay hộp cứng `left: 79%, top: 79.5%`), tô đỏ khi `zone_violation`, gắn nhãn biển số cho detection tin cậy cao nhất.
- **4 thẻ KPI Recharts**: `AreaChart` (lượt xe qua cổng), `BarChart` (biển số đọc được), `LineChart` (không đọc được), `RadialBarChart` gauge (độ tin cậy trung bình) — tất cả dựng từ sự kiện thật gom theo từng phút.
- **Các trạng thái**: loading (`aria-busy`, giá trị `…`), empty (danh sách rỗng + biểu đồ "Chưa có dữ liệu"), stale/mất đồng bộ (>12s không có payload mới → chỉ báo đổi màu + gợi ý kiểm tra backend), lỗi video, và empty state riêng khi chưa cấu hình zone.
- **Accessibility**: `role="status"`/`aria-live` cho chỉ báo trực tiếp, `role="list"`/`listitem` cho danh sách biển số, `aria-pressed` cho pill quy tắc xe và nút chọn zone, `aria-label` cho video và các ô sửa tên, nhãn zone chuyển từ `<span>` click được sang `<button>` (đưa vào được bằng bàn phím), giữ nguyên focus ring mặc định, biểu đồ `aria-hidden` vì số liệu đã có ở dạng text.
- **Responsive**: breakpoint 980px qua listener `resize` đặt trong `useEffect` (lần render đầu tất định, không chạm `window` khi khởi tạo state); lưới KPI 4→2 cột, lưới chính 2→1 cột.
- **Framework boundary**: Vite SPA thuần client, không có RSC/`'use client'`, không import module backend/Node; toàn bộ truy cập mạng đi qua `src/services/api.ts`.

## Vòng kiểm thử độc lập (2026-08-20) & khiếm khuyết đã sửa

Chạy một lượt kiểm thử độc lập trên bản dựng đã hoàn thiện. Kết quả:

**Đạt**: typecheck exit 0; build exit 0; quét bundle `dist/` không có token Telegram / đường dẫn CSDL / thư viện Node-native / DB client; Recharts có trong bundle; `EventResponse` và `LiveDetection` khớp đúng trường mà frontend tiêu thụ; `GET /videos/GATE_01.mp4` → 206; 5 vòng polling khi không có vi phạm → không sinh sự kiện rác; pytest backend 16 pass / 1 fail có sẵn từ trước (`test_model_real_call`, thiếu `yolov8s-worldv2.pt`, không liên quan TASK-009). Không kiểm tra được hydration mismatch (Vite SPA thuần client, không SSR) và console trình duyệt (môi trường không có browser automation).

**Khiếm khuyết phát hiện — đã sửa trong lượt này**: `GET /api/v1/events?camera_id=GATE-01` trả về **cả** sự kiện `ZONE_VIOLATION` (`license_plate = null`), không chỉ sự kiện LPR. Bản triển khai đầu tiên tiêu thụ nguyên payload nên một người đi vào zone bị hiển thị thành dòng biển số `—` và bị đếm nhầm vào **cả hai** thẻ KPI "Lượt xe qua cổng" và "Không đọc được".

- Tái hiện: tạo zone tạm phủ tâm detection `person` (52.7, 45.0) với `forbidden_classes: ["person"]` → poll `live-detections` → endpoint `events` trả 4 dòng `ZONE_VIOLATION | license_plate=None`.
- Trước khi sửa: 4 dòng rác trong danh sách biển số, KPI "Lượt xe qua cổng" = 4, "Không đọc được" = 4.
- Sau khi sửa (lọc `event_type === 'LPR' || Boolean(license_plate)` trong `GateDashboard.tsx`): danh sách 0 dòng, cả hai KPI = 0 — đúng kỳ vọng.
- Dọn dẹp: zone tạm đã xoá, CSDL trở lại trạng thái ban đầu (0 sự kiện GATE-01, chỉ còn zone `zA`/`zB` gốc).
- Xác nhận lại sau khi sửa: `npm --prefix frontend run lint` exit 0, `npm --prefix frontend run build` exit 0.

- Deviations:
  1. **Đường dẫn Inputs trong packet không tồn tại.** Packet ghi `docs/contracts/API-FOUNDATION.md` và `docs/contracts/UI-UX-FOUNDATION.md`; thực tế `docs/contracts/` chỉ có `api/` và `db/`. Artifact thật nằm ở `.delivery/tasks/TASK-002/API-FOUNDATION.md` và `.delivery/tasks/TASK-004/UI-UX-FOUNDATION.md` (đều `status: approved`) — đã dùng bản này. Cần `plan-delivery` sửa lại đường dẫn trong MASTER-PLAN.
  2. **Mở rộng write scope 1 dòng, đã được project owner phê duyệt.** Completion gate dùng `npm --prefix frontend run build` = `tsc && vite build`, nhưng `tsc` fail sẵn từ trước ở `AppContext.tsx:320` (TS7006) — ngoài write scope của TASK-009. Project owner đã phê duyệt sửa: thêm chú thích kiểu `(q: any)` / `(k: string)`. `qaKnowledgeBase` vốn là `any[]` và luôn rỗng nên đây là thay đổi thuần kiểu, không đổi hành vi runtime.
  3. **Phần "nhận diện LPR" của completion gate chưa chứng minh được đầu-cuối.** Frontend đã nối dây đầy đủ, nhưng backend hiện **không sinh ra biển số nào**: không có endpoint OCR/LPR, `events.license_plate` không được bất kỳ đường ghi nào điền, và `/api/v1/events?camera_id=GATE-01` trả `[]`. Trang vì thế hiển thị empty state đúng như thiết kế. Hoàn thiện LPR là việc của backend, ngoài phạm vi một task `frontend-implementation`.
  4. **Không có error state phân biệt được với empty state.** `src/services/api.ts` nuốt lỗi và trả `[]`/giá trị mặc định, nên trang không thể phân biệt "backend chết" với "không có dữ liệu". Đã thay bằng chỉ báo stale dựa trên thời điểm đồng bộ gần nhất. Muốn có error state thật phải sửa `api.ts` (ngoài write scope).
  5. **Không dùng `src/contracts/api/`** như skill mô tả — thư mục này không tồn tại trong dự án. Đã dùng nguồn hợp đồng thực tế của repo: `src/types/index.ts` và interface `LiveDetection` trong `src/services/api.ts`.
  6. Completion gate nhắc "YOLOv26"; codebase thực tế chạy Ultralytics YOLO-World v2 với fallback YOLOv8 (`backend/app/services/vision_pipeline.py`). Sai lệch tên gọi này xuất hiện xuyên suốt các artifact `.delivery/`, không riêng TASK-009.
- Blockers: none
- Scope change requests:
  1. Bổ sung test runner cho frontend (vitest + @testing-library/react + cấu hình + script `test`) để các task `frontend-implementation` có thể nộp bằng chứng unit test thật thay vì chỉ typecheck/build. Cần một task riêng vì phải sửa `package.json` và thêm file cấu hình.
  2. Cho `implement-backend` một task triển khai LPR/OCR thật cho GATE-01 (điền `events.license_plate`) để phần "nhận diện LPR realtime" của completion gate TASK-009 có thể nghiệm thu đầu-cuối.
  3. Cho `design-api`/`implement-frontend` một task để `src/services/api.ts` phát tín hiệu lỗi ra ngoài (thay vì nuốt lỗi), phục vụ error state đúng nghĩa trên toàn bộ 4 tab.

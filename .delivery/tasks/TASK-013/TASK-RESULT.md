---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-013
owner: implement-frontend
status: approved
updated_at: "2026-08-26T11:01:55+07:00"
---

# Kết quả Task: TASK-013 — Triển khai Tab 4 AI Chatbot Assistant

- Task ID: TASK-013
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-013/TASK-PACKET.md`, `.delivery/MASTER-PLAN.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/api-schema.json`, `backend/app/api/v1/assistant.py`, `backend/app/models/schemas/assistant.py`, `backend/app/services/qa_agent.py`, `backend/app/api/router.py`, `frontend/src/components/common/VideoModal.tsx`, `frontend/src/context/AppContext.tsx`.
- Outputs produced: `frontend/src/pages/AIChatbotAssistant.tsx` nối vào API trợ lý thật và phát clip bằng `<VideoModal>`; `frontend/src/services/api.ts` thêm `askAssistant()`; `frontend/src/context/AppContext.tsx` thay knowledge base mock bằng lời gọi backend bất đồng bộ; `frontend/src/types/index.ts` cập nhật `AIChatMessage`; `frontend/vite.config.ts` proxy `/media`; `.delivery/tasks/TASK-013/BUG-001.md`.
- Validation evidence: `npm run lint` (`tsc --noEmit`) exit 0; `npm run build` exit 0 với 840 modules transformed, `dist/assets/index-DReDBFgc.js` 647.84 kB (gzip 181.01 kB), built in 18.41s; ad-hoc FastAPI `TestClient` gọi `POST /api/v1/assistant/query` trả `200` đúng schema `{answer, sql_query, clip_url}`; `git diff --check` exit 0.
- Changed files: `frontend/src/pages/AIChatbotAssistant.tsx`, `frontend/src/context/AppContext.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `frontend/vite.config.ts` (tổng 6 file frontend đổi, 296 insertions / 257 deletions gồm cả TASK-009 trước đó).
- Tests changed: không thêm test file — `frontend/package.json` không khai báo script `test` và repo không có test runner frontend. `backend/tests/test_chatbot.py` mà MASTER-PLAN nêu làm verification method hiện không tồn tại và thuộc capability backend, không tạo trong task này.
- Commands run: `npm run lint` (exit 0); `npm run build` (exit 0); ad-hoc `python -c` với `fastapi.testclient.TestClient` trên `app.api.v1.assistant` (2 truy vấn, cùng trả HTTP 200); `ls data/clips/`; `find . -name sample_evidence.mp4` (rỗng); `grep -rn "app.mount" backend/`; `git diff --stat -- frontend/`; `git diff --check -- frontend/` (exit 0).
- Deviations: write scope mở rộng theo chỉ đạo trực tiếp của project owner; completion gate đạt phần frontend nhưng phụ thuộc backend cho Text-to-SQL và clip — xem `Trạng thái completion gate` và `BUG-001`.
- Blockers: none cho phạm vi frontend. Phần backend chặn gate đã ghi thành `.delivery/tasks/TASK-013/BUG-001.md`, chờ dispatch `backend-implementation` riêng.
- Scope change requests: none

## Trạng thái trước khi làm

Tab 4 đã có khung giao diện nhưng **không có kết nối backend nào**:

- `sendChatMessage()` trong `AppContext.tsx` so khớp từ khóa với mảng `qaKnowledgeBase`. Mảng này được khai báo `const qaKnowledgeBase: any[] = []` — rỗng tuyệt đối. Mọi câu hỏi vì vậy luôn rơi vào `fallbackQA` và nhận đúng một câu: *"Không có dữ liệu sự kiện nào ghi nhận trên hệ thống cơ sở dữ liệu."* Chatbot không hoạt động với bất kỳ đầu vào nào.
- Endpoint thật `POST /api/v1/assistant/query` (`backend/app/api/router.py:13`) tồn tại nhưng chưa bao giờ được frontend gọi.
- Thẻ "clip bằng chứng" là ảnh giả dựng bằng CSS: các khối gradient mô phỏng khung hình, thanh tua đặt cứng ở `32%`, nút play và nút "Tải 10s" không gắn handler. Không có phần tử `<video>` nào. `<VideoModal>` — component dùng chung mà completion gate chỉ đích danh — không hề được import.

## Đã làm

### 1. Nối vào API trợ lý thật

Thêm `askAssistant()` vào `services/api.ts`, khớp đúng `QueryResponse` tại `backend/app/models/schemas/assistant.py` (`answer: str`, `sql_query: Optional[str]`, `clip_url: Optional[str]`). Hàm kiểm tra `answer` phải là chuỗi trước khi trả về, và chuẩn hóa hai trường optional về `null` nếu backend gửi kiểu khác — không cast mù bằng `as`.

### 2. Thay knowledge base mock bằng luồng bất đồng bộ

`sendChatMessage()` trở thành `async`, chèn ngay bong bóng trả lời trạng thái `pending` với một id cố định, rồi **thay tại chỗ** bong bóng đó khi backend phản hồi thay vì nối thêm tin nhắn mới. Lỗi gọi API được bắt và hiển thị thành bong bóng `status: 'error'` kèm nguyên văn lý do, không nuốt lỗi. Đã xóa `qaKnowledgeBase` và `fallbackQA`.

Kiểu `AIChatMessage` bỏ object `clip` trang trí (`tint`, `boxColor`, `boxLabel`…) và thay bằng `sqlQuery`, `clipUrl`, `status` — phản ánh đúng dữ liệu backend thật sự trả về.

### 3. Clip 10s phát được bằng `<VideoModal>`

Gỡ toàn bộ thẻ clip giả. Khi `clipUrl` có giá trị, hiển thị thẻ gọn với nhãn `CLIP 10s`, nút "Xem clip" mở `<VideoModal>` (chứa `<video controls autoPlay>` thật) và link tải trực tiếp. Không có `clipUrl` thì không hiện gì — thay vì vẽ bằng chứng không tồn tại.

### 4. Prompt chips, trạng thái và accessibility

- Prompt chips gợi ý gửi thẳng câu hỏi; bị vô hiệu hóa khi đang chờ phản hồi.
- Loading: ô nhập, nút gửi và chips khóa lại khi `isPending`, bong bóng trả lời hiện "Đang tra cứu sự kiện…" dạng in nghiêng mờ.
- Error: bong bóng viền đỏ mang `role="alert"`.
- Nút gửi vô hiệu hóa khi ô nhập rỗng.
- Câu SQL backend sinh ra hiển thị trong `<details>` thu gọn để người dùng kiểm chứng câu trả lời.
- Log hội thoại mang `role="log"`, `aria-live="polite"`, `aria-busy`; ô nhập và các nút icon đều có `aria-label`; SVG trang trí gắn `aria-hidden`.
- Tự cuộn xuống tin nhắn mới nhất sau mỗi lần log thay đổi.

### 5. Proxy `/media`

`vite.config.ts` trước đó chỉ proxy `/videos` và `/api`. Backend trả `clip_url` dưới tiền tố `/media/`, nên dev server sẽ không chuyển tiếp được. Đã thêm `/media`.

## Trạng thái completion gate

Gate: *"Trang Chatbot tiếng Việt với thanh gợi ý Prompt Chips, trả lời Text-to-SQL đính kèm trình phát `<VideoModal>` clip 10s chứng cứ."*

| Thành phần | Trạng thái |
|---|---|
| Trang chatbot tiếng Việt | Đạt |
| Thanh gợi ý Prompt Chips | Đạt |
| Gọi API trả lời thật thay mock | Đạt — verify bằng TestClient, HTTP 200 đúng schema |
| Trình phát `<VideoModal>` cho clip | Đạt về phía frontend |
| Trả lời Text-to-SQL thật | Đạt — sau khi sửa BUG-001 (xem phụ lục backend) |
| Clip 10s phát được end-to-end | Đạt — sau khi sửa BUG-001 (xem phụ lục backend) |

Hai mục cuối ban đầu chưa đạt vì backend là stub và `/media` chưa mount. Đã ghi thành `BUG-001` thay vì sửa xuyên biên giới trong lượt `frontend-implementation`; sau đó project owner cho phép xử lý bằng capability `backend-implementation` — kết quả ở phụ lục dưới.

---

# Phụ lục: Xử lý BUG-001 bằng capability `backend-implementation`

- Owner phụ lục: `implement-backend`
- Ngày: 2026-08-26
- Ủy quyền: chỉ đạo trực tiếp của project owner sau khi `BUG-001` được báo cáo.

## Outputs produced (backend)

- `backend/main.py` — mount `/media/clips` và `/media/crops` từ `settings.CLIPS_DIR` / `settings.CROPS_DIR`, tạo sẵn thư mục trước khi mount.
- `backend/app/services/qa_agent.py` — thay stub bằng Fallback Rule Engine theo ADR-004, thực thi SQL thật trên SQLite; 5 intent, phạm vi thời gian theo `ICT_TZ`, `clip_url` lấy từ `events.video_clip_url`, chốt an toàn chặn SQL ghi.
- `backend/tests/test_chatbot.py` — mới, 16 test (đây cũng là verification method mà MASTER-PLAN khai báo cho TASK-013).

## Validation evidence (backend)

| Lệnh | Kết quả |
|---|---|
| `python -m pytest backend/tests/test_chatbot.py -q -p no:warnings` | `16 passed in 58.43s` |
| `python -m pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py -q` | `22 passed in 68.08s` |
| `python -m pytest backend/tests/test_dataset_object_labeling.py backend/tests/test_dataset_zone_sync.py backend/tests/test_database.py backend/tests/test_database_config.py -q` | `16 passed in 3.46s` |
| `GET /media/clips/clip_GATE-01_1787716332.mp4` qua TestClient | `200 video/mp4`, 2 949 159 bytes (trước đây 404) |
| `GET /media/clips/khong-ton-tai.mp4` | `404` |

Kiểm chứng trên CSDL production thật (800 sự kiện, 3 camera): bốn câu hỏi khác nhau cho bốn câu trả lời khác nhau với số liệu thật và clip URL thật — chi tiết trong `BUG-001.md`, mục `Verify`.

## Deviations (backend)

- **Artifact ownership**: phần backend này được ghi làm phụ lục trong `TASK-RESULT.md` của TASK-013 thay vì tạo `TASK-NNN` mới, vì `CLAUDE.md` cấm tự phát sinh và đánh số task khi chưa được yêu cầu rõ ràng. File này do đó có hai owner: `implement-frontend` cho phần chính và `implement-backend` cho phụ lục. Nếu project owner muốn tách thành task riêng, cần cấp số task một cách tường minh.
- **ADR-004**: nhánh LLM chưa được bật vì `Settings` không có khóa API của bất kỳ LLM provider nào. Nhánh đang chạy là Fallback Rule Engine mà chính ADR-004 quy định. Đây là hiện thực hóa một nửa ADR, không phải toàn bộ.
- `events.py:297` vẫn dựng `video_clip_url` mặc định viết cứng khi bản ghi không có clip. Đề mục 3 trong `Cách sửa` của `BUG-001` chưa thực hiện vì nằm ngoài phạm vi được giao trong lượt này và chạm tới lane sự kiện của TASK-017/TASK-027.

## Blockers (backend)

Không có blocker cho BUG-001.

Ghi nhận độc lập: `backend/tests/test_video_feed_regression.py` có **3 test fail** với `AttributeError: 'Query' object has no attribute 'replace'` tại `backend/app/services/frame_extractor.py:55`. Lỗi này **không do công việc BUG-001**:

- `test_video_feed_regression.py` không nằm trong danh sách file bị sửa (`git status`), tức là test gốc không đổi.
- `frame_extractor.py` đang ở trạng thái modified do một đợt refactor đồng thời từ bên ngoài phiên này (đổi import `app.*` → `backend.app.*`, thêm `VideoSourceUnavailableError` và `_camera_env_video_path`). Hàm `_camera_env_video_path` là code mới của đợt refactor đó.
- Phạm vi sửa của BUG-001 chỉ gồm `backend/main.py` (thêm 2 mount), `backend/app/services/qa_agent.py` và `backend/tests/test_chatbot.py`.

Cần chủ sở hữu đợt refactor `frame_extractor.py` xử lý; chưa mở bug riêng vì chưa xác định được task sở hữu.

## Sai lệch so với packet

- **Write scope**: packet ghi `.delivery/tasks/TASK-013/`. Project owner đã chỉ đạo trực tiếp mở rộng sang `frontend/src/pages/AIChatbotAssistant.tsx` "và các file liên quan". Đã ghi vào 5 file frontend liệt kê ở `Changed files`. Không file backend nào bị sửa.
- **Expected outputs** ghi `backend/ai/text_to_sql.py`. File này không tồn tại; code chatbot backend thực tế nằm ở `backend/app/services/qa_agent.py` như project owner xác nhận. Không sửa file backend nào vì capability của task là `frontend-implementation` — bản chất công việc đó là `backend-implementation`.
- **Inputs** ghi `docs/contracts/API-FOUNDATION.md`; file này không tồn tại. Đã dùng `.delivery/API-CONTRACT.md` + `docs/contracts/api/api-schema.json` cùng chính source backend làm contract, giống cách xử lý ở `TASK-009`.
- Không đổi API contract, backend, MASTER-PLAN hay aggregate artifact nào.

## Ghi chú kiểm chứng

Repo không có test runner frontend nên không chạy được scoped component test theo bước 8 của skill; verification dựa trên strict TypeScript compile và production build, cùng cách `TASK-009`/`TASK-010`/`TASK-012` đã dùng.

Contract backend được kiểm bằng `fastapi.testclient.TestClient` chạy ad-hoc, không ghi file test nào vào `backend/`. Hai truy vấn khác nhau trả về response giống hệt — đây chính là bằng chứng cho `BUG-001`, đồng thời xác nhận schema mà `askAssistant()` parse là đúng.

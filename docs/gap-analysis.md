# Phân tích Khoảng cách (Gap Analysis) — SentriAI Mini

> Sinh bởi skill `project-gap-audit` Phase C. Chỉ đọc code, không sửa gì.
> Mỗi phán quyết trỏ về file đã mở trong phiên audit.

- Ngày chạy: 2026-08-23
- **Phạm vi: module `ASSISTANT` (Hỏi đáp AI)** + `REQ-EVENT-001` vì nó chặn module này
- Requirements đối chiếu: `docs/requirements.md` — 7 mục
- Trạng thái cây làm việc: 16 file đang modified, 4 mục untracked **trước khi** audit chạy
- Câu hỏi mở chưa chốt: Q1–Q5 trong `docs/requirements.md` mục 1. Phần dưới chạy
  dưới giả định đã nêu rõ tại từng gap.

---

## 1. Tổng hợp

| Verdict | Số lượng |
|---|---|
| IMPLEMENTED | 0 |
| PARTIAL | 1 |
| MISSING | 4 |
| DIVERGENT | 2 |
| UNVERIFIABLE | 0 |

| Severity | Số gap |
|---|---|
| CRITICAL | 3 |
| HIGH | 2 |
| MEDIUM | 1 |
| LOW | 1 |

**Ba gap chặn nhất:** `GAP-001`, `GAP-002`, `GAP-003`.

---

## 2. Bảng truy vết requirement → verdict

| REQ | Tên | Verdict | Bằng chứng (file:line) | GAP |
|---|---|---|---|---|
| REQ-ASSISTANT-001 | Trả lời NL dựa trên sự kiện đã lưu | DIVERGENT | `backend/app/services/qa_agent.py:15-16` | GAP-001 |
| REQ-ASSISTANT-002 | Số liệu + chi tiết sự kiện | MISSING | `frontend/src/context/AppContext.tsx:39-44` | GAP-002 |
| REQ-ASSISTANT-003 | Clip 10s + nút tải | MISSING | `frontend/src/pages/AIChatbotAssistant.tsx:309` | GAP-003 |
| REQ-ASSISTANT-004 | LLM text-to-SQL / function calling | MISSING | `backend/app/services/qa_agent.py:1` | GAP-004 |
| REQ-ASSISTANT-005 | Thanh câu hỏi gợi ý | PARTIAL | `frontend/src/pages/AIChatbotAssistant.tsx:8-12, 320-340` | GAP-005 |
| REQ-ASSISTANT-006 | Trình phát clip trong modal | MISSING | `frontend/src/components/common/VideoModal.tsx:8` | GAP-006 |
| REQ-EVENT-001 | Trích & lưu clip 10s | DIVERGENT | `backend/app/services/event_manager.py:49-51` | GAP-007 |

Không mục nào đạt `IMPLEMENTED`. Toàn bộ bề mặt của module tồn tại (route, service,
component, schema), nhưng không đường dẫn nào đi hết từ câu hỏi tới dữ liệu thật.

---

## 3. Chi tiết từng gap

### GAP-001 — QA agent trả lời chuỗi cứng, không chạm CSDL

- **Requirement:** REQ-ASSISTANT-001
- **Verdict:** DIVERGENT
- **Severity:** CRITICAL
- **Bằng chứng:**
  - `backend/app/services/qa_agent.py:14-16` — `sql = "SELECT COUNT(*) FROM events;"`
    và `answer = "Hệ thống đã ghi nhận 15 sự kiện hôm nay."` là hằng số. Chuỗi SQL
    được **trả về** cho client nhưng không bao giờ được **thực thi**.
  - `backend/app/services/qa_agent.py:18-20` — nhánh duy nhất là `if "vi phạm" in
    query_lower`, gán một cặp hằng khác. Toàn bộ module chỉ có hai câu trả lời khả dĩ.
  - `backend/app/services/qa_agent.py:1` — chỉ `import logging`; không import
    `Session`, không import repository, không có kết nối CSDL nào.
  - `backend/app/api/v1/assistant.py:5-11` — router không nhận `Depends(get_db)`,
    nên ngay ở tầng route đã không có đường vào CSDL.
- **File bị ảnh hưởng:** `backend/app/services/qa_agent.py`,
  `backend/app/api/v1/assistant.py`, `backend/app/models/schemas/assistant.py`
- **Nguyên nhân gốc:** service được scaffold theo `ADR-004` nhưng phần truy vấn chưa
  bao giờ được hiện thực; `sql_query` được để lộ ra response schema tạo cảm giác
  hệ thống đang chạy text-to-SQL trong khi nó chỉ trả về một chuỗi trang trí.
- **Tác động:** Hỏi "hôm nay có bao nhiêu xe lạ vào?" luôn nhận đúng một câu trả lời
  bất kể CSDL rỗng hay có 500 sự kiện. Đây là một trong bốn màn bắt buộc của RFP.
- **Confidence:** FACT

### GAP-002 — Frontend chat không gọi backend, luôn trả một câu duy nhất

- **Requirement:** REQ-ASSISTANT-002
- **Verdict:** MISSING
- **Severity:** CRITICAL
- **Bằng chứng:**
  - `frontend/src/context/AppContext.tsx:39` — `const qaKnowledgeBase: any[] = [];`
    **mảng rỗng**.
  - `frontend/src/context/AppContext.tsx:314-327` — `sendChatMessage` tra cứu trong
    mảng rỗng đó rồi rơi xuống `fallbackQA`. Vì `qaKnowledgeBase` rỗng, `.find()`
    luôn trả `undefined`, nên **mọi** câu hỏi đều nhận `fallbackQA`.
  - `frontend/src/context/AppContext.tsx:41-44` — `fallbackQA.text = 'Không có dữ
    liệu sự kiện nào ghi nhận trên hệ thống cơ sở dữ liệu.'`, `clip: undefined`.
  - `frontend/src/pages/AIChatbotAssistant.tsx:1-2` — component chỉ import `React`
    và `useApp`; không import gì từ `services/api.ts`.
  - `frontend/src/services/api.ts` — không có hàm nào gọi `/assistant`; các endpoint
    được bọc là `/events`, `/zones`, `/vehicles`, `/events/live-detections`,
    `/kpi` (dòng 17, 56, 79, 119, 138, 162, 180, 190, 203).
- **File bị ảnh hưởng:** `frontend/src/context/AppContext.tsx`,
  `frontend/src/services/api.ts`, `frontend/src/pages/AIChatbotAssistant.tsx`
- **Nguyên nhân gốc:** đường dây frontend → backend cho module này chưa bao giờ được
  nối; UI vẫn chạy trên cơ chế mock nhưng kho mock đã bị dọn rỗng, nên nó thoái hoá
  thành một câu trả lời tĩnh.
- **Tác động:** Backend dù có sửa xong `GAP-001` thì giao diện vẫn không hiển thị
  kết quả — hai gap này phải vá cùng nhau mới thấy hiệu quả.
- **Confidence:** FACT

### GAP-003 — Không có clip 10s nào được đính kèm; nút tải không làm gì

- **Requirement:** REQ-ASSISTANT-003
- **Verdict:** MISSING
- **Severity:** CRITICAL
- **Bằng chứng:**
  - `frontend/src/pages/AIChatbotAssistant.tsx:108` — khối clip render có điều kiện
    `{m.clip && (...)}`; mà `m.clip` luôn là `undefined` (xem GAP-002), nên khối này
    **không bao giờ render**.
  - `frontend/src/pages/AIChatbotAssistant.tsx:309` — nút `Tải 10s` không có
    `onClick`; đối chiếu dòng 326 và 372 là hai nút duy nhất trong file có handler.
  - `backend/app/services/qa_agent.py:24` — `clip_url` trả về hằng
    `"/media/clips/sample_evidence.mp4"`. Không có route nào phục vụ tiền tố
    `/media/` — `backend/main.py:48-57` chỉ mount `/videos` và `/assets`.
  - `data/clips/` — thư mục rỗng (0 mục).
- **File bị ảnh hưởng:** `frontend/src/pages/AIChatbotAssistant.tsx`,
  `backend/app/services/qa_agent.py`, `backend/main.py`,
  `backend/app/services/event_manager.py`
- **Nguyên nhân gốc:** ba lỗi độc lập chồng lên nhau — chưa có clip được sinh
  (GAP-007), tiền tố URL không khớp static mount nào, và nút tải chỉ là vỏ giao diện.
- **Tác động:** Vi phạm trực tiếp câu chốt của RFP mục 2.4 — "luôn kèm đoạn video 10
  giây". RFP phần Lưu ý nêu rõ trọng tâm nghiệm thu là luồng "…lưu sự kiện kèm clip
  → hỏi đáp có trích dẫn"; mắt xích trích dẫn hiện đứt hoàn toàn.
- **Confidence:** FACT

### GAP-004 — Không có tích hợp LLM nào trong dự án

- **Requirement:** REQ-ASSISTANT-004
- **Verdict:** MISSING
- **Severity:** HIGH
- **Bằng chứng:**
  - `backend/requirements.txt` và `requirements.txt` — không dependency nào là LLM
    client (không `openai`, `anthropic`, `langchain`, `ollama`, `google-genai`).
  - `backend/app/services/qa_agent.py:1` — chỉ `import logging`.
  - `.delivery/ADR/ADR-004-llm-text-to-sql-with-fallback.md:15` — trạng thái
    `approved`, quyết định "Tích hợp LLM Text-to-SQL với cơ chế Fallback Rule-based
    Engine". Quyết định kiến trúc đã duyệt nhưng chưa có dấu vết hiện thực.
  - Cái đang tồn tại (`qa_agent.py:18`, khớp chuỗi `"vi phạm"`) tương ứng với nhánh
    *fallback* của ADR-004, không phải nhánh LLM.
- **File bị ảnh hưởng:** `backend/app/services/qa_agent.py`, `backend/requirements.txt`,
  `backend/app/core/config.py` (chưa có biến cấu hình API key)
- **Nguyên nhân gốc:** chưa chốt vendor LLM (câu hỏi mở Q1) nên phần này chưa khởi động.
- **Tác động:** Câu hỏi ngoài hai mẫu cứng không xử lý được. Hạ severity xuống HIGH
  thay vì CRITICAL vì RFP mục 3 cho phép "text-to-SQL **hoặc** function calling" —
  vẫn còn khoảng lựa chọn kỹ thuật, và một rule engine đủ tốt trên CSDL thật sẽ gỡ
  được phần lớn tác động người dùng.
- **Confidence:** FACT (hiện trạng) / UNKNOWN (hướng giải quyết — chờ Q1, Q2)

### GAP-005 — Nút gợi ý có, nhưng thiếu icon theo spec cấp 2

- **Requirement:** REQ-ASSISTANT-005
- **Verdict:** PARTIAL
- **Severity:** LOW
- **Bằng chứng:**
  - `frontend/src/pages/AIChatbotAssistant.tsx:8-12` — ba câu gợi ý được khai báo,
    khớp ví dụ trong RFP mục 2.4.
  - `frontend/src/pages/AIChatbotAssistant.tsx:320-340` — render thành nút, `onClick`
    gọi `sendChatMessage(s)`. Tiêu chí nghiệm thu 1 **đạt**.
  - Không file nào trong `frontend/src/pages/` import `lucide-react`; nơi duy nhất
    dùng là `frontend/src/components/layout/Header.tsx`. Tiêu chí 2 (cấp 2) không đạt.
- **File bị ảnh hưởng:** `frontend/src/pages/AIChatbotAssistant.tsx`
- **Nguyên nhân gốc:** yêu cầu icon đến từ CR-002 (hiện đại hoá UI stack) và chưa
  được áp dụng xuống màn này.
- **Tác động:** Thẩm mỹ. Không chặn luồng nghiệp vụ nào.
- **Confidence:** FACT

### GAP-006 — `VideoModal` tồn tại nhưng không nơi nào dùng

- **Requirement:** REQ-ASSISTANT-006
- **Verdict:** MISSING
- **Severity:** MEDIUM
- **Bằng chứng:**
  - `frontend/src/components/common/VideoModal.tsx:8` — component được export đầy đủ
    (60 LOC, nhận `videoUrl` + `onClose`).
  - Tìm chuỗi `VideoModal` trên toàn `frontend/src/` chỉ trả về chính file định nghĩa
    nó — **không import nào**. Đây là component chết.
  - `frontend/src/pages/AIChatbotAssistant.tsx:108-313` — thẻ clip được vẽ inline
    ngay trong luồng chat, không mở modal.
- **File bị ảnh hưởng:** `frontend/src/components/common/VideoModal.tsx`,
  `frontend/src/pages/AIChatbotAssistant.tsx`
- **Nguyên nhân gốc:** component được dựng theo `REQ-008` AC2 nhưng khâu nối vào màn
  chat chưa làm; thẻ clip inline được viết theo mockup thay thế.
- **Tác động:** MEDIUM chứ không cao hơn, vì đây là ràng buộc **cấp 2** — RFP cấp 1
  chỉ đòi "kèm đoạn video" và "nút tải", không quy định modal. Nếu Q5 chốt là
  nice-to-have thì gap này hạ xuống LOW.
- **Confidence:** DERIVED
- **Suy luận:** FACT — VideoModal không được import ở đâu; FACT — RFP 2.4 không nhắc
  modal; FACT — cấp 2 REQ-008 AC2 yêu cầu `<VideoModal>` → yêu cầu này do đội tự thêm
  qua CR-002, nên mức chặn nghiệm thu thấp hơn các gap cấp 1.

### GAP-007 — Clip 10s là file placeholder 31 byte, không phải MP4

- **Requirement:** REQ-EVENT-001
- **Verdict:** DIVERGENT
- **Severity:** HIGH
- **Bằng chứng:**
  - `backend/app/services/event_manager.py:49-51` — ghi
    `f.write(b"MP4_RING_BUFFER_10S_SAMPLE_DATA")` vào file `.mp4`. Đây là 31 byte
    text, không phải container MP4; không trình phát nào mở được.
  - `backend/app/services/event_manager.py:53` — vẫn log `"Sliced 10s evidence video
    clip"` như thể đã cắt thật, nên lỗi này im lặng trong log.
  - `backend/app/services/event_manager.py:54` — trả `/media/clips/{filename}`, tiền
    tố không khớp static mount nào trong `backend/main.py:48-57`.
  - `docs/contracts/db/schema.sql:77` — cột `video_clip_url VARCHAR(512)` đã có sẵn,
    nên phía lưu trữ không phải vấn đề.
  - `data/clips/` rỗng → trên cây làm việc hiện tại chưa có sự kiện nào từng gọi tới
    hàm này.
- **File bị ảnh hưởng:** `backend/app/services/event_manager.py`,
  `backend/app/api/v1/events.py`, `backend/main.py`
- **Nguyên nhân gốc:** ring buffer chưa được hiện thực; placeholder được để lại để
  bề mặt hàm chạy được, và `EventManager` cũng chưa được nối vào đường ghi sự kiện
  thật (`events.py` không import nó).
- **Tác động:** Chặn `REQ-ASSISTANT-003` và cả tiêu chí nghiệm thu tổng thể số 2 của
  `.delivery/REQUIREMENTS.md` ("trích xuất đúng 10s video clip cho mọi sự kiện").
- **Confidence:** FACT

---

## 4. Chưa kiểm tra

| Đường dẫn / hạng mục | Lý do |
|---|---|
| Module VEHICLE, DATASET, ALERT | ngoài phạm vi cả hai lát cắt đã audit |
| `backend/tests/*.py` | không có test nào đặt tên theo assistant/qa; chưa mở nội dung để xác nhận độ phủ |
| Hành vi runtime của `POST /api/v1/assistant/query` | chưa chạy server; kết luận rút từ đọc code, không từ gọi thật |
| `frontend/src/services/api.ts:203` gọi `/kpi` | endpoint này không có trong `app/api/router.py`; nghi là gap nhưng thuộc module khác, chưa xác minh |
| `.delivery/tasks/TASK-*/TASK-RESULT.md` | chưa đọc; có thể chứa lý do vì sao các mục trên còn là stub |
| `Prototype/Intern-LPR-Gate.dc.html` | mới trích text, chưa đối chiếu chi tiết layout màn "Trợ lý sự kiện" |

---
---

# Phần B — Lát cắt Live Detection Overlay

> Bổ sung 2026-08-23, cùng skill, cùng ràng buộc chỉ-đọc.

- **Phạm vi:** bounding box, class label + confidence score, ROI/polygon zone,
  point-in-polygon — module `GATE`, `AREA`, `ZONE`, cộng `PLATFORM` vì nó chặn cả lát cắt.
- Requirements đối chiếu: `docs/requirements.md` mục 2B — 8 mục
- Câu hỏi mở: Q6–Q10 (`docs/requirements.md` mục 1B). **Q6, Q8, Q9, Q10 đã được
  người dùng chốt trong phiên**; quyết định ghi tại từng gap. Q7 tự khép (hai tầng
  nguồn thống nhất "tâm bbox").
- Kiểm chứng đã chạy: `pytest backend/tests -q` → **89 passed** (80s).

## B1. Tổng hợp

| Verdict | Số lượng |
|---|---|
| IMPLEMENTED | 3 |
| PARTIAL | 3 |
| MISSING | 1 |
| DIVERGENT | 1 |
| UNVERIFIABLE | 0 |

| Severity | Số gap |
|---|---|
| CRITICAL | 1 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 2 |

**Ba gap chặn nhất:** `GAP-100`, `GAP-101`, `GAP-104`.

## B2. Bảng truy vết requirement → verdict

| REQ | Tên | Verdict | Bằng chứng (file:line) | GAP |
|---|---|---|---|---|
| REQ-GATE-001 | Overlay khung + biển số + độ tin cậy (cổng) | DIVERGENT | `frontend/src/pages/GateDashboard.tsx:396`, `:736-738` | GAP-101 |
| REQ-AREA-001 | Bbox vẽ đúng vị trí trên video khu vực | IMPLEMENTED | `frontend/src/pages/AreaSecurityDashboard.tsx:439-494`; đồng bộ frame qua `?t=` tại `:71-72` + `backend/app/api/v1/events.py:270` | — (xem GAP-105) |
| REQ-AREA-002 | Nhãn lớp đối tượng trên box | IMPLEMENTED | `backend/app/api/v1/events.py:338`; render tại `AreaSecurityDashboard.tsx:490` | — |
| REQ-AREA-003 | Confidence score trên overlay khu vực | MISSING | không có tham chiếu `confidence` nào trong `AreaSecurityDashboard.tsx` (grep toàn file); backend đã trả tại `events.py:347` | GAP-102 |
| REQ-AREA-004 | Mã màu 3 mức severity | PARTIAL | nhánh vàng có tại `AreaSecurityDashboard.tsx:452-454` nhưng không có đường sinh dữ liệu | GAP-103 |
| REQ-ZONE-001 | ROI đa giác chồng lên khung hình | IMPLEMENTED | `AreaSecurityDashboard.tsx:338-365`, `GateDashboard.tsx:626-654` | — (xem GAP-105) |
| REQ-ZONE-002 | Mọi camera vẽ/sửa được zone trên khung hình thật | PARTIAL | `frontend/src/pages/ZoneTagSettings.tsx:398-401`, `:542` | GAP-104 |
| REQ-ZONE-003 | Point-in-polygon theo tâm bbox | IMPLEMENTED | `backend/app/services/vision_pipeline.py:212-259`; test `backend/tests/test_ai_engine.py:18,37`, `backend/tests/test_zone_geometry.py` | — (xem GAP-106) |
| REQ-PLATFORM-001 *(phát sinh)* | Cài đặt lại được môi trường chạy overlay | PARTIAL | `requirements.txt`, `backend/requirements.txt` | GAP-100 |

## B3. Chi tiết gap

### GAP-100 — `ultralytics` không được khai báo trong bất kỳ manifest nào

- **Severity:** CRITICAL
- **Requirement:** REQ-PLATFORM-001 (chặn REQ-AREA-001, REQ-ZONE-003, REQ-GATE-001)
- **Bằng chứng:**
  - `backend/requirements.txt` (12 dòng) — không có `ultralytics`, không có `torch`.
  - `requirements.txt` (root, 7 dòng) — cũng không có; thiếu luôn `sqlalchemy`,
    `pydantic`, `pydantic-settings`, `httpx`, `websockets` mà backend đang dùng.
  - Gói thực sự đang chạy: `ultralytics 8.4.123`, chỉ tồn tại trong `.venv`
    (`.venv/Lib/site-packages/ultralytics-8.4.123.dist-info/`), tức được cài tay.
  - Đường phụ thuộc: `vision_pipeline.py:169` `from ultralytics import YOLOWorld`,
    `:180` `from ultralytics import YOLO` — cả hai nằm trong `try/except` chỉ ghi
    `logger.warning` rồi `self.model = None` (`:189`).
- **File bị ảnh hưởng:** `requirements.txt`, `backend/requirements.txt`
- **Nguyên nhân gốc:** weights và runtime YOLO được cài thủ công lúc phát triển,
  manifest không được cập nhật theo. `except` nuốt lỗi import làm sự cố không lộ ra
  lúc khởi động — server vẫn lên, `/docs` vẫn chạy.
- **Tác động:** Trên máy mới `pip install -r requirements.txt` xong, `self.model`
  là `None` → `process_frame` trả `[]` ngay tại `vision_pipeline.py:266` →
  `/events/live-detections` luôn trả mảng rỗng → **cả hai màn giám sát không vẽ
  được một box nào**, và UI hiển thị đúng thông báo "Không phát hiện đối tượng
  trong khung hình" nên lỗi trông như "video không có gì" chứ không như lỗi cài đặt.
  Hai trong bốn màn bắt buộc của RFP mất chức năng chính.
- **Confidence:** FACT

### GAP-101 — Biển số trên box ở màn cổng không đến từ chính box đó

- **Severity:** HIGH
- **Requirement:** REQ-GATE-001 AC1, AC2
- **Bằng chứng:**
  - `GateDashboard.tsx:396`: `const latestPlate = events.find((e) => e.plate !== '—')`
    — lấy sự kiện **đã lưu trong CSDL** gần nhất có biển số.
  - `GateDashboard.tsx:391-394`: `primaryDetection` = detection có `confidence` cao
    nhất trong khung hình, **không liên quan tới biển số**.
  - `GateDashboard.tsx:736-737`: badge của box đó = `${latestPlate.plate} · ${latestPlate.conf}%`.
    Hai nguồn dữ liệu độc lập bị ghép lại thành một nhãn.
  - Không có engine OCR/LPR nào trong `backend/app/services/` (grep `ocr|easyocr|paddle|lpr`
    chỉ trả về tên cột CSDL và chuỗi `event_type`, không có code nhận dạng).
- **File bị ảnh hưởng:** `frontend/src/pages/GateDashboard.tsx`,
  `backend/app/services/` (thiếu module LPR)
- **Nguyên nhân gốc:** pipeline chỉ có phát hiện đối tượng (YOLO), chưa có bước OCR
  biển số; UI vẫn giữ layout mockup vốn giả định có biển số nên phải mượn dữ liệu
  từ bảng `events` (chủ yếu là dữ liệu seed) để lấp chỗ trống.
- **Tác động:** Overlay khẳng định một điều không đúng — người xem demo hiểu rằng hệ
  thống vừa đọc được biển số đó từ khung hình đang phát, trong khi chuỗi này thuộc
  về một sự kiện khác trong quá khứ. Đây chính là dạng dương tính giả mà RFP mục 2.1
  yêu cầu tránh, và nó khó phát hiện hơn một ô trống.
- **Confidence:** FACT

### GAP-102 — Overlay màn khu vực không hiển thị confidence score

- **Severity:** MEDIUM
- **Requirement:** REQ-AREA-003
- **Quyết định nguồn:** Q6 — người dùng chốt **"tiêu chí nghiệm thu"** (2026-08-23).
  Ghi rõ: RFP mục 2.2 không yêu cầu; ràng buộc này do người dùng đặt ra trong phiên,
  không phải do khách hàng.
- **Bằng chứng:**
  - `backend/app/api/v1/events.py:347` — payload **có** trường `confidence`.
  - `backend/app/api/v1/events.py:338` — `label = f"{vn_name.upper()} · {status_text}"`,
    ghép tên lớp với trạng thái cho phép/vi phạm, **không chèn confidence**.
  - `AreaSecurityDashboard.tsx:490` render đúng chuỗi `label` đó và không đọc
    `o.confidence` ở bất kỳ đâu trong file.
  - Đối chiếu: `GateDashboard.tsx:738` đã làm đúng — `Math.round(d.confidence * 100)` + `%`.
- **File bị ảnh hưởng:** `backend/app/api/v1/events.py` (nếu sửa ở `label`),
  `frontend/src/pages/AreaSecurityDashboard.tsx` (nếu sửa ở tầng render)
- **Nguyên nhân gốc:** chuỗi `label` được backend dựng sẵn phục vụ ngữ nghĩa
  nghiệp vụ (cho phép / vi phạm), và frontend tiêu thụ nguyên chuỗi đó thay vì tự
  ghép từ các trường rời — nên không còn chỗ chèn confidence ở phía client.
- **Tác động:** Hai màn giám sát trình bày không nhất quán: màn cổng có `· 87%`,
  màn khu vực không. Người vận hành không phân biệt được detection chắc chắn với
  detection ở sát ngưỡng 0.30 (`vision_pipeline.py:89`), vốn là khác biệt đáng kể
  với footage cảng nơi confidence thật rơi vào khoảng 0.36–0.42.
- **Confidence:** FACT (thiếu) / ASSUMPTION (mức bắt buộc — theo Q6)

### GAP-103 — Severity mức 2 (Vàng) không có đường sinh trong nhánh sống

- **Severity:** MEDIUM
- **Requirement:** REQ-AREA-004
- **Quyết định nguồn:** Q8 — người dùng chốt **"mức 2 phải sinh được"**; điều kiện
  kích hoạt vẫn là UNKNOWN.
- **Bằng chứng:**
  - `vision_pipeline.py:328` — `"severity": 1` là giá trị khởi tạo duy nhất.
  - `vision_pipeline.py:343` — khi vi phạm: `zone.get("severity", 3)`.
  - `backend/app/api/v1/events.py:260` — `zones_payload` **hardcode** `"severity": 3`,
    nên nhánh `.get` ở trên luôn ra 3.
  - `docs/contracts/db/schema.sql:34-42` — bảng `zones` **không có cột `severity`**
    (chỉ `vertices`, `allowed_classes`, `forbidden_classes`, `color`), nên không có
    nguồn dữ liệu nào để đọc ra mức khác.
  - Giá trị 2 chỉ xuất hiện ở nhánh chết: `backend/app/models/domain/zone.py:11`,
    `backend/app/models/schemas/zone.py:8` — không file nào trong nhánh sống import.
  - Frontend đã sẵn sàng: `AreaSecurityDashboard.tsx:452-454` có nhánh `severity === 2`
    → `#ff9f0a`. Nhánh này **không bao giờ chạy**.
- **File bị ảnh hưởng:** `docs/contracts/db/schema.sql`, `backend/database/models.py`,
  `backend/app/api/v1/events.py`
- **Nguyên nhân gốc:** cột `severity` của zone bị bỏ khi chuyển sang schema viết tay,
  nhưng code đọc nó thì giữ lại dưới dạng `.get(..., 3)` — một mặc định che mất việc
  dữ liệu không tồn tại.
- **Tác động:** `.delivery/REQUIREMENTS.md` REQ-003 mô tả thang 3 mức nhưng chỉ 2 mức
  quan sát được trên màn khu vực. Mọi vi phạm zone đều đỏ, không phân biệt được mức
  "cần kiểm tra" với mức "vi phạm rõ ràng".
- **Confidence:** FACT (mức 2 không sinh được) / UNKNOWN (điều kiện đúng để sinh — Q8)

### GAP-104 — Camera `XUONG-AN-NINH` hiện zone nhưng không sửa được zone

- **Severity:** HIGH
- **Requirement:** REQ-ZONE-002 AC1, AC2
- **Quyết định nguồn:** Q9 — người dùng chốt **"phạm vi mở rộng, cần hoàn thiện"**.
- **Bằng chứng:**
  - `docs/contracts/db/schema.sql:186-187` — seed 2 zone cho camera này
    (`zX1` "Zone máy móc xưởng", `zX2` "Zone lối đi bộ"); xác nhận trong CSDL đang
    chạy: `sentri_ai.db` bảng `zones` có đủ 7 bản ghi / 3 camera.
  - `AreaSecurityDashboard.tsx:230` — có nút chọn camera này;
    `:163` — trỏ tới `/videos/XUONG-AN-NINH.mp4`. Zone của nó **được vẽ lên màn giám sát**.
  - `ZoneTagSettings.tsx:398-401` — danh sách camera của trình vẽ zone **chỉ có**
    `BAI-KIEM` và `GATE-01`.
  - `ZoneTagSettings.tsx:542` — ảnh nền chọn theo biểu thức nhị phân:
    `GATE-01` thì `/assets/cam-gate.png`, còn lại đều `/assets/cam-baikiem.png` —
    không có nhánh cho camera thứ ba.
- **File bị ảnh hưởng:** `frontend/src/pages/ZoneTagSettings.tsx`, `Prototype/assets/`
  (thiếu ảnh nền), `docs/contracts/db/schema.sql`
- **Nguyên nhân gốc:** camera thứ ba được thêm ở tầng giám sát và tầng dữ liệu nhưng
  trình cấu hình không được mở rộng theo; điều kiện chọn ảnh nền viết nhị phân nên
  mọi camera không phải `GATE-01` đều nhận ảnh Bãi Kiểm.
- **Tác động:** Phá vỡ vòng nghiệp vụ trung tâm mà RFP mục 2.3 yêu cầu — "Zone lưu
  lại phải cập nhật ngay ở các màn giám sát" — theo chiều ngược lại: zone hiển thị
  nhưng không có đường sửa. Người dùng thấy vùng cấm sai vị trí ở Xưởng An Ninh sẽ
  không có cách nào chỉnh, và nếu trình vẽ được mở rộng mà quên ảnh nền thì họ sẽ
  vẽ zone của Xưởng lên nền Bãi Kiểm — sai còn khó phát hiện hơn.
- **Confidence:** FACT

### GAP-105 — `objectFit: cover` làm overlay lệch khỏi video ở `XUONG-AN-NINH`

- **Severity:** LOW
- **Requirement:** REQ-AREA-001 AC2, REQ-ZONE-001 AC3
- **Quyết định nguồn:** Q10 — người dùng chốt **"chỉ camera thứ 3 là GAP"**; sai lệch
  ~0.5% của hai camera còn lại nằm dưới ngưỡng nhìn thấy được, không ghi thành gap.
- **Bằng chứng (đo trong phiên):**
  - Khung chứa video: `aspectRatio: '16/9'` (= 1.7778) —
    `AreaSecurityDashboard.tsx:312`, `GateDashboard.tsx:574`.
  - Video: `objectFit: 'cover'` — `AreaSecurityDashboard.tsx:333`, `GateDashboard.tsx:620`.
  - Kích thước thật (đo bằng OpenCV trên `data/video/`):
    `BAI-KIEM.mp4` 1274×720 (1.7694), `GATE-01.mp4` 1274×720 (1.7694),
    **`XUONG-AN-NINH.mp4` 1228×720 (1.7056)**.
  - Overlay dùng phần trăm của **khung chứa**, không phải của video:
    bbox `AreaSecurityDashboard.tsx:445-448`; polygon `svg viewBox="0 0 100 100"
    preserveAspectRatio="none"` `:339-340`.
  - Suy ra: `cover` cắt dọc `1.7778/1.7056 − 1 ≈ 4.2%` chiều cao video ở camera thứ ba
    (mỗi mép ~2.1%), trong khi bbox/polygon không bù phần cắt đó.
- **File bị ảnh hưởng:** `frontend/src/pages/AreaSecurityDashboard.tsx`,
  `frontend/src/pages/GateDashboard.tsx`
- **Nguyên nhân gốc:** hệ toạ độ overlay neo vào khung chứa, còn ảnh video neo vào
  chính nó sau khi bị `cover` cắt. Hai hệ chỉ trùng nhau khi tỉ lệ video đúng bằng 16/9.
- **Tác động:** bbox và polygon ở Xưởng An Ninh lệch dọc tới ~2.1% chiều cao khung
  hình và bị giãn ~4.2%. Vì **bbox và polygon lệch cùng chiều cùng mức**, phán quyết
  point-in-polygon ở backend vẫn đúng (nó tính trên toạ độ gốc của frame, không qua
  CSS) — sai lệch chỉ là thị giác. Đó là lý do severity LOW chứ không cao hơn.
- **Confidence:** FACT (số đo) / DERIVED (mức lệch — suy từ quy tắc `object-fit: cover`
  và ba số đo tỉ lệ ở trên)

### GAP-106 — Hai điểm giòn trong `point_in_polygon` và vòng lặp zone

- **Severity:** LOW
- **Requirement:** REQ-ZONE-003 AC4 (nợ kỹ thuật, chưa ảnh hưởng nghiệm thu)
- **Bằng chứng:**
  1. `vision_pipeline.py:223-231` — cờ `is_percentage` suy **chỉ từ đa giác**
     (`max_coord > 1.0`), còn điểm được quy đổi theo từng trục độc lập:
     `px / 100.0 if px > 1.0 else px`. Một điểm dạng phần trăm nằm trong dải 1% sát
     mép trái (x ≤ 1.0) sẽ **không** được chia 100 trong khi y thì có → hai trục
     khác thang đo. Đường gọi hiện tại không dính lỗi này: `process_frame:339` luôn
     truyền `norm_bbox` đã chuẩn hoá 0–1 (`:314`), còn đa giác từ CSDL luôn là 0–100,
     nên nhánh chạy là nhánh đúng. Đây là bẫy cho người gọi sau, không phải lỗi đang xảy ra.
  2. `vision_pipeline.py:333-347` — vòng lặp zone chỉ `break` ở nhánh vi phạm (`:345`).
     Với zone không vi phạm, `zone_name` bị **ghi đè** bởi mọi zone chứa điểm đó tiếp
     theo (`:347`), nên khi các zone chồng lấn, tên zone "an toàn" hiển thị là zone
     cuối cùng trong danh sách chứ không phải zone cụ thể nào có ý nghĩa.
- **File bị ảnh hưởng:** `backend/app/services/vision_pipeline.py`
- **Nguyên nhân gốc:** (1) heuristic tự đoán đơn vị thay cho một hợp đồng đơn vị
  tường minh giữa hai tầng; (2) nhánh `else` dùng chung biến với nhánh vi phạm nhưng
  không có quy tắc chọn khi nhiều zone cùng khớp.
- **Tác động:** Hiện chưa sai kết quả nghiệm thu nào — thuật toán ray-casting đúng và
  đã có test (`test_ai_engine.py:18` cho nhiều định dạng, `:37` cho tâm bbox;
  `test_zone_geometry.py` 8 test cho hình học zone seed). Rủi ro nằm ở lần mở rộng sau.
- **Confidence:** FACT (mã nguồn) / DERIVED (kịch bản kích hoạt — chưa dựng test tái hiện)

## B4. Điểm đã nghi ngờ nhưng **không** phải gap

Ghi lại để lần audit sau khỏi mở lại:

| Nghi vấn | Kết luận | Bằng chứng |
|---|---|---|
| Zone vẽ trên PNG tĩnh (`/assets/cam-baikiem.png`) trong khi detection chạy trên MP4 → ROI đăng ký sai khung hình | **Không phải gap** cho `BAI-KIEM` và `GATE-01` | Dựng ảnh đối chiếu trong phiên (frame video tại t=5s so với PNG): cùng camera, cùng góc, cùng bố cục; đồng hồ in trên hình 09:40:58 (video) vs 09:53:03 (PNG), cùng ngày 06-15-2026. Tỉ lệ PNG 2942×1656 (1.7766) và 2966×1662 (1.7846) đều sát 16/9 |
| Overlay lệch pha với video do backend đọc frame theo con trỏ riêng | **Đã xử lý** | Client truyền `video.currentTime` qua `?t=`: `AreaSecurityDashboard.tsx:71-72`, `api.ts:170-172`; backend seek bằng `read_at()`: `events.py:270`, `events.py:150-179`. Có test: `test_live_detections.py:229`, `:252` |
| `api.ts` nuốt lỗi trả mảng rỗng nên không phân biệt được "backend chết" với "không có đối tượng" | **Đã xử lý riêng cho live-detections** | `api.ts:149-178` trả `{ok, detections}`; UI phân biệt tại `AreaSecurityDashboard.tsx:34`, `:518-519`. Các hàm khác trong `api.ts` vẫn nuốt lỗi |
| Detection giả được tiêm khi YOLO im lặng | **Đã gỡ** | `events.py:285-291` và `:296-303` ghi rõ đã bỏ; test chốt lại: `test_live_detections.py:276`, `:291`, `:329` |
| `.env.example` khai báo khác bộ biến `config.py` thực đọc (theo ghi chú nền + `CLAUDE.md`) | **Ghi chú đã lỗi thời** | Hai bên nay khớp: `DATABASE_URL`, `VIDEOS_DIR`, `IMAGES_DIR`, `CLIPS_DIR`, `CROPS_DIR`, `VIDEO_*_PATH`, `DETECTION_CONFIDENCE_THRESHOLD`, `EVENT_COOLDOWN_SECONDS` — `.env.example` vs `backend/app/core/config.py:39-65` |
| `point_in_polygon` dùng sai điểm đại diện (đáy thay vì tâm) | **Đúng spec** | RFP mục 3 và `.delivery/REQUIREMENTS.md` REQ-002 đều ghi "tâm"; `vision_pipeline.py:251-259` dùng tâm |
| `PolygonZoneEditor.tsx` là stub | **Đúng, nhưng không ảnh hưởng chức năng** | File 67 dòng, không có `<svg>`/`<polygon>`; nó chỉ là bảng chú giải quy tắc zone. Trình vẽ thật nằm inline trong `ZoneTagSettings.tsx:521-700` và có đủ 4 thao tác RFP yêu cầu (`handleVertexMouseDown` `:671`, `handleEdgeMouseDown` `:700`, `handlePolygonMouseDown` `:606`, chế độ vẽ `:515-517`). Tên component gây hiểu nhầm — nợ kỹ thuật, không phải thiếu chức năng |

## B5. Chưa kiểm tra (lát cắt overlay)

| Đường dẫn / hạng mục | Lý do |
|---|---|
| Độ chính xác thật của YOLO trên footage (precision/recall) | cần chạy server + đối chiếu ground truth; audit này chỉ đọc mã và chạy test |
| Hành vi overlay khi trình duyệt thật render | chưa mở trình duyệt; kết luận về `objectFit` rút từ số đo tỉ lệ + quy tắc CSS, không từ ảnh chụp màn hình |
| `frontend` không có test runner (`package.json`) | không có test nào để chạy cho tầng render overlay — khoảng trống độ phủ, chưa quy thành gap riêng |
| `backend/scripts/render_zone_overlay.py` | công cụ kiểm chứng overlay được `CLAUDE.md` nhắc tới; chưa chạy trong phiên này |
| Tiêu chí "< 1 giây" của REQ-001 AC3 | `DETECTION_GAP_MS = 700` (`AreaSecurityDashboard.tsx:22`) là khoảng nghỉ, chưa đo độ trễ suy luận thật nên chưa phán quyết |

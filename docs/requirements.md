# Đặc tả Yêu cầu — SentriAI Mini

> Sinh bởi skill `project-gap-audit` Phase B. Bản trích **truy nguyên được** từ
> nguồn, không phải bản thiết kế. Mọi dòng gắn nhãn FACT / DERIVED / ASSUMPTION / UNKNOWN.

- Ngày dựng: 2026-08-23
- **Phạm vi bản này:**
  - module `ASSISTANT` (Hỏi đáp AI) — trích ngày 2026-08-23, mục 2
  - **lát cắt Live Detection Overlay** (`GATE` / `AREA` / `ZONE`) — bổ sung
    2026-08-23, mục 2B: bounding box, class label + confidence, ROI/polygon zone,
    point-in-polygon
  - Các module VEHICLE, DATASET, ALERT chưa được trích.
- Nguồn cấp 1: `Prototype/RFP Bài tập Intern.dc.html` (v1.0, 17/08/2026), mục 2.4 và mục 3
- Nguồn cấp 1 (UI): `Prototype/Intern-LPR-Gate.dc.html` — màn "Trợ lý sự kiện"
- Nguồn cấp 2: `.delivery/REQUIREMENTS.md` (v1.4.0, status `approved`) — `REQ-008`
- Nguồn cấp 2 (kiến trúc): `.delivery/ADR/ADR-004-llm-text-to-sql-with-fallback.md` (v1.0.0, approved)
- Trạng thái câu hỏi mở: **đang chờ người dùng** (xem mục 1)

---

## 1. Câu hỏi mở — phải trả lời trước Phase C

| # | Mục | Nhãn | Nguồn nói gì | Cần quyết định |
|---|---|---|---|---|
| Q1 | Nhà cung cấp / model LLM cho text-to-SQL | UNKNOWN | RFP mục 3 chỉ ghi "LLM truy vấn trên CSDL sự kiện (text-to-SQL hoặc function calling)", không nêu vendor. ADR-004 quyết định "tích hợp LLM" nhưng cũng không nêu vendor. Không manifest nào (`backend/requirements.txt`, `requirements.txt`) có dependency LLM. | Dùng LLM nào, chạy cloud hay local? |
| Q2 | Ngưỡng "Fallback Rule-based Engine" kích hoạt khi nào | UNKNOWN | ADR-004 nêu tên cơ chế fallback, không nêu điều kiện chuyển | Fallback khi LLM lỗi, khi timeout, hay khi độ tin cậy thấp? |
| Q3 | Clip 10s là cắt sẵn lúc sinh sự kiện, hay cắt on-demand lúc trả lời | UNKNOWN | RFP mục 3 nói "trích và lưu clip 10s quanh thời điểm sự kiện" (nghe như cắt sẵn); mục 2.4 nói câu trả lời "luôn kèm đoạn video 10 giây... từ giây nào đến giây nào" (nghe như tham chiếu khoảng thời gian) | Lưu file clip riêng, hay chỉ lưu offset rồi seek trên video gốc? |
| Q4 | "Luôn kèm clip" áp dụng cho mọi câu trả lời hay chỉ câu về sự kiện cụ thể | ASSUMPTION | RFP 2.4 viết "luôn kèm"; cấp 2 REQ-008 AC2 thu hẹp lại còn "câu trả lời về sự kiện vi phạm/cụ thể" | Câu hỏi tổng hợp kiểu "hôm nay có bao nhiêu xe" có bắt buộc kèm clip không? |
| Q5 | "bbox highlight đối tượng" trong clip | ASSUMPTION | Chỉ cấp 2 (`REQ-008` AC2) yêu cầu; RFP cấp 1 không nhắc | Vẽ bbox lên clip là bắt buộc nghiệm thu hay nice-to-have? |

**Q1 và Q3 chặn việc triển khai** — không chốt thì không thể ước lượng khối lượng
việc của `GAP-004` và `GAP-003` bên dưới.

### 1B. Câu hỏi mở — lát cắt Live Detection Overlay

| # | Mục | Nhãn | Nguồn nói gì | Cần quyết định |
|---|---|---|---|---|
| Q6 | Overlay màn Giám sát khu vực có bắt buộc hiển thị **confidence score** không | ASSUMPTION | RFP mục 2.1 (màn cổng) yêu cầu rõ "khung nhận diện + biển số + **độ tin cậy**". RFP mục 2.2 (màn khu vực) chỉ nói "phát hiện đối tượng trong các zone đa giác", **không nhắc overlay hay độ tin cậy**. Cấp 2 `REQ-002` AC 1-4 cũng không yêu cầu. Yêu cầu này đến từ prompt người dùng phiên này. | Confidence trên màn khu vực là tiêu chí nghiệm thu hay nice-to-have? |
| Q7 | Điểm đại diện cho point-in-polygon | FACT (đã chốt) | RFP mục 3: "kiểm tra **tâm** đối tượng nằm trong zone đa giác (point-in-polygon)"; cấp 2 `REQ-002` Behavior: "theo vị trí tâm (bounding box center)". Hai tầng nguồn thống nhất. | Không cần quyết định — tâm bbox là đúng spec. Ghi lại đây để chặn đề xuất đổi sang bottom-center. |
| Q8 | Mức severity 2 (Vàng) áp dụng cho overlay khu vực như thế nào | UNKNOWN | Cấp 2 `REQ-003` định nghĩa mức 2 = "Xe lạ / Cần kiểm tra" — một khái niệm của module VEHICLE (biển số). Không nguồn nào nói một *đối tượng không biển số* trong zone khi nào thì là mức 2. | Overlay khu vực có bao giờ được vàng không, và theo điều kiện gì? |
| Q9 | Camera `XUONG-AN-NINH` có nằm trong phạm vi nghiệm thu không | UNKNOWN | RFP mục 2.2 chỉ nêu `BAI-KIEM`; cấp 2 `REQ-002` cũng chỉ nêu `BAI-KIEM`. Nhưng code đã hiện thực camera này (`AreaSecurityDashboard.tsx:230`, 2 zone seed trong `schema.sql:186-187`). | Đây là phạm vi mở rộng cần hoàn thiện, hay tính năng thừa nên bỏ? |
| Q10 | Sai số hình học chấp nhận được của overlay | UNKNOWN | Không nguồn nào nêu dung sai. | Lệch bao nhiêu % chiều cao khung hình thì coi là fail? |

**Q6 và Q9 chặn phán quyết** — xem `GAP-101` và `GAP-104`.

---

## 2. Danh sách requirement — module ASSISTANT

### REQ-ASSISTANT-001 Trả lời câu hỏi ngôn ngữ tự nhiên dựa trên sự kiện đã lưu

- **Behavior:** Người dùng nhập câu hỏi tiếng Việt về sự kiện đã ghi nhận; hệ thống
  truy vấn CSDL sự kiện và sinh câu trả lời từ dữ liệu thật trong bảng `events`.
- **Source:** RFP mục 2.4 ("Khung chat hỏi bằng ngôn ngữ tự nhiên về sự kiện đã lưu")
- **Tầng nguồn:** cấp 1 (RFP)
- **Priority:** P0 (`.delivery/REQUIREMENTS.md` REQ-008)
- **Acceptance criteria:**
  1. Câu trả lời thay đổi theo nội dung bảng `events`; không phải chuỗi hằng.
  2. Hai câu hỏi khác nhau về mặt ngữ nghĩa cho ra hai câu trả lời khác nhau.
- **Confidence:** FACT

### REQ-ASSISTANT-002 Câu trả lời nêu số liệu và chi tiết sự kiện

- **Behavior:** Câu trả lời chứa số lượng và chi tiết sự kiện liên quan (thời gian,
  camera, zone, loại đối tượng / biển số).
- **Source:** RFP mục 2.4 ("Câu trả lời nêu số liệu + chi tiết sự kiện")
- **Tầng nguồn:** cấp 1 (RFP)
- **Priority:** P0 (cấp 2 REQ-008)
- **Acceptance criteria:**
  1. Với câu hỏi đếm ("hôm nay có bao nhiêu xe lạ vào?"), con số khớp `SELECT COUNT(*)` tương ứng trên `events`.
  2. Với câu hỏi lọc ("có xe máy nào vào khu vực cấm không?"), liệt kê được sự kiện cụ thể thay vì chỉ trả lời có/không.
- **Confidence:** FACT

### REQ-ASSISTANT-003 Mỗi câu trả lời kèm clip 10 giây có nút tải

- **Behavior:** Câu trả lời về sự kiện đính kèm đoạn video 10 giây của sự kiện đó,
  nêu rõ camera và khoảng giây, kèm nút tải clip về.
- **Source:** RFP mục 2.4 ("luôn kèm đoạn video 10 giây của sự kiện liên quan
  (camera nào, từ giây nào đến giây nào), có nút tải clip") + mục 3 dòng "Lưu sự kiện"
- **Tầng nguồn:** cấp 1 (RFP)
- **Priority:** P0 (cấp 2 REQ-008 AC2)
- **Acceptance criteria:**
  1. Payload trả về chứa `camera_id`, giây bắt đầu, giây kết thúc của clip.
  2. Clip phát được (file MP4 hợp lệ, không phải placeholder).
  3. Nút tải tải về đúng file đó.
- **Confidence:** FACT
- **Phụ thuộc:** cơ chế trích clip 10s ở tầng sự kiện — xem `REQ-EVENT-001`.

### REQ-ASSISTANT-004 Truy vấn bằng LLM text-to-SQL hoặc function calling

- **Behavior:** Việc chuyển câu hỏi tiếng Việt thành truy vấn dữ liệu do LLM đảm
  nhiệm (text-to-SQL hoặc function calling), có cơ chế fallback rule-based.
- **Source:** RFP mục 3, dòng "Hỏi đáp" + `ADR-004` (approved)
- **Tầng nguồn:** cấp 1 (RFP nêu cơ chế) — chi tiết fallback là cấp 2 (ADR-004)
- **Priority:** P0 (cấp 2 REQ-008)
- **Acceptance criteria:**
  1. Có tích hợp LLM thật; câu hỏi ngoài tập mẫu vẫn xử lý được.
  2. Khi LLM không khả dụng, fallback trả lời được mà không sập endpoint.
- **Confidence:** FACT (yêu cầu) / UNKNOWN (vendor — xem Q1, Q2)

### REQ-ASSISTANT-005 Thanh câu hỏi gợi ý nhanh

- **Behavior:** Giao diện chat hiển thị các nút câu hỏi gợi ý bấm được.
- **Source:** `Prototype/Intern-LPR-Gate.dc.html` màn "Trợ lý sự kiện" (`{{ s.text }}`) + cấp 2 REQ-008 AC3
- **Tầng nguồn:** cấp 1 (mockup) — yêu cầu "Lucide React icons" là cấp 2 (CR-002)
- **Priority:** P1 — DERIVED (RFP không xếp hạng; cấp 2 gộp chung P0 cho cả REQ-008,
  nhưng đây là yếu tố phụ trợ không chặn luồng nghiệp vụ `cấu hình → phát hiện →
  lưu sự kiện → hỏi đáp` mà RFP nhấn mạnh ở phần Lưu ý)
- **Acceptance criteria:**
  1. Có ít nhất một hàng nút gợi ý; bấm vào gửi luôn câu hỏi đó.
  2. (cấp 2) Nút kèm icon Lucide React.
- **Confidence:** DERIVED
- **Suy luận:** FACT — mockup có khối `{{ s.text }}` lặp; FACT — cấp 2 AC3 yêu cầu
  Lucide icons; FACT — RFP phần Lưu ý xác định trọng tâm là luồng nghiệp vụ, không
  phải chi tiết giao diện → yếu tố này là P1.

### REQ-ASSISTANT-006 Trình phát clip trong modal

- **Behavior:** Bấm vào thẻ clip mở trình phát video 10s trong modal.
- **Source:** cấp 2 `REQ-008` AC2 (`<VideoModal>`, có bbox highlight)
- **Tầng nguồn:** **cấp 2** — RFP cấp 1 chỉ yêu cầu "kèm đoạn video" và "nút tải",
  không quy định modal hay bbox highlight
- **Priority:** P1 — DERIVED (ràng buộc do đội tự thêm qua CR-002, không phải khách hàng)
- **Acceptance criteria:**
  1. Có component modal phát được clip đính kèm.
  2. (Q5) Bbox highlight — chưa chốt là bắt buộc hay không.
- **Confidence:** DERIVED

### REQ-EVENT-001 Trích và lưu clip 10s quanh thời điểm sự kiện *(phụ thuộc, ngoài module)*

- **Behavior:** Khi sinh sự kiện, hệ thống cắt và lưu đoạn video 10 giây quanh thời
  điểm đó, lưu đường dẫn vào CSDL.
- **Source:** RFP mục 3, dòng "Lưu sự kiện"
- **Tầng nguồn:** cấp 1 (RFP)
- **Priority:** P0
- **Acceptance criteria:**
  1. File clip là MP4 phát được.
  2. `events.video_clip_url` trỏ tới file tồn tại.
- **Confidence:** FACT
- **Ghi chú:** đưa vào bản này vì nó chặn `REQ-ASSISTANT-003`. Việc kiểm kê đầy đủ
  module EVENT chưa thực hiện.

---

## 2B. Danh sách requirement — lát cắt Live Detection Overlay

### REQ-GATE-001 Overlay khung nhận diện + biển số + độ tin cậy trên khung hình trực tiếp

- **Behavior:** Màn Giám sát cổng vẽ khung nhận diện lên video trực tiếp của
  `GATE-01`, kèm chuỗi biển số và độ tin cậy.
- **Source:** RFP mục 2.1 dòng "Hiển thị khung nhận diện + biển số + độ tin cậy
  trên khung hình trực tiếp"; mockup `Prototype/Intern-LPR-Gate.dc.html` badge
  `{{ livePlate }} · 97%`
- **Tầng nguồn:** cấp 1 (RFP + mockup)
- **Priority:** P0 (cấp 2 `REQ-001`)
- **Acceptance criteria:**
  1. Có khung vẽ trên video, toạ độ bám theo đối tượng thật trong khung hình.
  2. Nhãn kèm độ tin cậy dạng phần trăm.
  3. Khung và nhãn cập nhật realtime (cấp 2 `REQ-001` AC3: < 1 giây).
- **Confidence:** FACT

### REQ-AREA-001 Bounding box của đối tượng phát hiện được vẽ đúng vị trí trên video khu vực

- **Behavior:** Màn Giám sát khu vực vẽ bounding box của từng đối tượng YOLO phát
  hiện lên đúng vị trí tương ứng trong khung hình đang phát.
- **Source:** cấp 2 `REQ-002` AC1 ("xác định chính xác bounding box"); RFP mục 2.2
  ("Phát hiện đối tượng trong các zone đa giác")
- **Tầng nguồn:** cấp 1 (RFP nêu việc phát hiện) — từ "bounding box" là cấp 2
- **Priority:** P0
- **Acceptance criteria:**
  1. Box bao quanh đối tượng thật, không phải hộp mặc định/bịa.
  2. Toạ độ box khớp khung hình người dùng đang nhìn (không lệch pha với `<video>`).
  3. Không phát hiện được thì không vẽ box nào và nói rõ lý do.
- **Confidence:** FACT

### REQ-AREA-002 Nhãn lớp đối tượng hiển thị trên box

- **Behavior:** Mỗi box kèm nhãn tiếng Việt của lớp đối tượng trong bộ 8 lớp chuẩn.
- **Source:** RFP mục 2.2 (liệt kê loại xe + người); CR-001 (bộ 8 lớp)
- **Tầng nguồn:** cấp 1 (danh mục lớp) — hiển thị nhãn trên box là DERIVED
- **Priority:** P0
- **Acceptance criteria:**
  1. Nhãn thuộc bộ 8 lớp chuẩn, dùng tên tiếng Việt.
  2. Lớp không nhận ra thì bỏ detection, không gán nhãn đoán.
- **Confidence:** DERIVED
- **Suy luận:** FACT — RFP mục 2.2 yêu cầu "phát hiện **và phân loại**"; FACT —
  overlay là nơi duy nhất thể hiện kết quả phân loại theo thời gian thực trên màn
  khu vực (`AreaSecurityDashboard.tsx:439-494`) → nhãn phải nằm trên box.

### REQ-AREA-003 Confidence score hiển thị trên overlay khu vực

- **Behavior:** Mỗi box trên màn khu vực kèm độ tin cậy của detection.
- **Source:** **không có nguồn cấp 1 hoặc cấp 2 trực tiếp** — suy từ RFP mục 2.1
  (màn cổng) và yêu cầu người dùng phiên 2026-08-23
- **Tầng nguồn:** ngoài nguồn (yêu cầu phiên)
- **Priority:** UNKNOWN
- **Acceptance criteria:**
  1. Nhãn box chứa độ tin cậy dạng phần trăm, lấy từ `confidence` backend trả về.
- **Confidence:** ASSUMPTION — **xem Q6, chặn phán quyết**

### REQ-ZONE-001 ROI đa giác hiển thị chồng lên khung hình giám sát

- **Behavior:** Các zone đa giác đã cấu hình được vẽ chồng lên video ở cả màn cổng
  và màn khu vực, có màu và tên zone.
- **Source:** RFP mục 2.2 ("các zone đa giác"), mục 2.3 ("Zone lưu lại phải cập
  nhật ngay ở các màn giám sát")
- **Tầng nguồn:** cấp 1 (RFP)
- **Priority:** P0
- **Acceptance criteria:**
  1. Polygon vẽ đúng toạ độ phần trăm đã lưu trong `zones.vertices`.
  2. Zone sửa trong Cài đặt phản ánh ngay ở màn giám sát, không cần restart.
  3. Polygon đăng ký đúng vào cùng hệ toạ độ với bounding box.
- **Confidence:** FACT

### REQ-ZONE-002 Mọi camera có zone đều vẽ/sửa được zone trên khung hình thật của chính nó

- **Behavior:** Công cụ Cài đặt cho phép chọn camera và vẽ zone trên khung hình
  thật của camera đó.
- **Source:** RFP mục 2.3 dòng "Vẽ zone: chọn camera (Bãi Kiểm, Cổng vào), vẽ zone
  trên khung hình thật"
- **Tầng nguồn:** cấp 1 (RFP) — RFP chỉ liệt kê 2 camera; camera thứ ba là mở rộng
  của đội (xem Q9)
- **Priority:** P0 cho `BAI-KIEM` + `GATE-01`; UNKNOWN cho `XUONG-AN-NINH`
- **Acceptance criteria:**
  1. Mỗi camera có zone trong CSDL đều chọn được trong Cài đặt.
  2. Nền vẽ là khung hình thật của đúng camera đó.
- **Confidence:** FACT (2 camera RFP) / UNKNOWN (camera thứ ba — Q9)

### REQ-ZONE-003 Point-in-polygon theo tâm bounding box quyết định vi phạm

- **Behavior:** Hệ thống lấy tâm bounding box, kiểm tra nằm trong hay ngoài đa giác
  zone, rồi đối chiếu danh sách cho phép/cấm của zone để sinh vi phạm.
- **Source:** RFP mục 3 ("kiểm tra tâm đối tượng nằm trong zone đa giác
  (point-in-polygon)"); cấp 2 `REQ-002` Behavior + AC1, AC2
- **Tầng nguồn:** cấp 1 (RFP) — cả hai tầng thống nhất, xem Q7
- **Priority:** P0
- **Acceptance criteria:**
  1. Thuật toán ray-casting cho kết quả đúng với đa giác lồi và lõm.
  2. Điểm kiểm tra là tâm bbox, không phải góc hay đáy.
  3. Đối tượng thuộc danh sách cấm và nằm trong zone → sinh cảnh báo ngay.
  4. Toạ độ điểm và toạ độ đa giác cùng một hệ quy chiếu.
- **Confidence:** FACT

### REQ-AREA-004 Mã màu overlay theo 3 mức severity

- **Behavior:** Box đổi màu theo mức độ: 1 xanh, 2 vàng, 3 đỏ.
- **Source:** cấp 2 `REQ-003` (Mức 1 Xanh / Mức 2 Vàng / Mức 3 Đỏ)
- **Tầng nguồn:** **cấp 2** — RFP cấp 1 chỉ nói "sinh cảnh báo vi phạm", không phân 3 mức
- **Priority:** P0 (cấp 2 `REQ-003`)
- **Acceptance criteria:**
  1. Ba mức đều có đường sinh trong nhánh sống và đều quan sát được trên overlay.
- **Confidence:** DERIVED — điều kiện sinh mức 2 là UNKNOWN, xem Q8

---

## 3. Requirement bị loại khỏi phạm vi

| Mục nguồn | Lý do loại |
|---|---|
| RFP mục 4 — repo Git, README, docker-compose | sản phẩm bàn giao, không phải hành vi phần mềm |
| RFP mục 4 — video demo 3–5 phút | sản phẩm bàn giao |
| RFP mục 4 — bộ nhãn ≥ 5 nhãn × ≥ 20 mẫu | thuộc module DATASET, không thuộc phạm vi bản này |
| RFP mục 5 — thời gian, lịch review | quản trị dự án |

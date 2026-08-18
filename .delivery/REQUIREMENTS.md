---
artifact: REQUIREMENTS
version: 1.1.0
owner: Product Owner & Engineering Team
status: approved
updated_at: 2026-08-17T22:07:32+07:00
---

Discovery status: confirmed
Delivery scope: full-product

# Đặc tả Yêu cầu Hệ thống Giám sát Camera AI (SentriAI Mini)

## 1. Mạch Nghiệp vụ & Phạm vi (Scope Summary)

Hệ thống cung cấp giải pháp giám sát an ninh camera AI tự động cho 2 kịch bản chính (Cổng vào LPR và Giám sát Khu vực Zone), kết hợp quản lý danh sách biển số, vẽ zone đa giác linh hoạt, gán nhãn mẫu đối tượng custom, và AI Assistant hỏi đáp sự kiện bằng ngôn ngữ tự nhiên kèm clip chứng cứ 10 giây. Tất cả luồng thao tác và giao diện tuân thủ chính xác thiết kế mẫu chuẩn trong folder `Prototype` (`Intern-LPR-Gate.dc.html` và `RFP Bài tập Intern.dc.html`).

---

## 2. Danh sách Yêu cầu Sản phẩm (Product Requirements)

### REQ-001: Nhận diện biển số xe tại Cổng (LPR Gate Monitoring)
- **Behavior**: Hệ thống đọc stream video từ camera cổng (`GATE-01`), tự động phát hiện và nhận diện biển số xe (LPR) khi xe đi vào zone làn IN (Làn IN 1, Làn IN 2). Hiển thị bounding box biển số, chuỗi biển số và độ tin cậy realtime trên giao diện. Hiển thị khối chỉ số KPI trực tiếp (Lượt xe qua cổng, Biển số đọc được, Không đọc được, Độ tin cậy trung bình).
- **Rationale**: Kiểm soát tự động lưu lượng phương tiện ra vào cổng mà không cần nhân viên ghi chép thủ công.
- **Priority**: P0 (Bắt buộc - Core feature)
- **Source**: User RFP & UI Mockup (Prototype: Màn 1 - Giám sát cổng)
- **Acceptance Criteria**:
  1. Nhận diện chính xác biển số xe với độ tin cậy >= 85% trong điều kiện ánh sáng chuẩn.
  2. Ghi nhận thời gian, camera_id, làn IN, chuỗi biển số, ảnh crop biển số và lưu clip 10s.
  3. Thời gian phản hồi hiển thị trên UI realtime < 1 giây kể từ khi xe đi vào làn IN.
  4. Hiển thị đúng 4 thẻ KPI thống kê trực tiếp: Lượt xe qua cổng, Biển số đọc được, Không đọc được, Độ tin cậy trung bình.
- **Status**: approved
- **Delivery classification**: new

### REQ-002: Giám sát Khu vực & Kiểm tra Quy tắc Zone (Area Zone Violations)
- **Behavior**: Hệ thống đọc stream camera khu vực (`BAI-KIEM`), phát hiện và phân loại đối tượng (người, xe container, xe tải, xe nâng, xe cẩu, xe con, xe máy, xe đạp) theo vị trí tâm (bounding box center) trong các Zone đa giác. So sánh với quy tắc cấm/cho phép của từng Zone để sinh cảnh báo vi phạm khi có đối tượng không hợp lệ. Hiển thị các thẻ KPI giám sát khu vực (Đối tượng trong khu, Vi phạm loại xe, Xe nâng/container hoạt động, Tổng số zone).
- **Rationale**: Đảm bảo an toàn lao động và ngăn chặn truy cập trái phép vào vùng cấm trong khu vực bãi kiểm/kho hàng.
- **Priority**: P0 (Bắt buộc - Core feature)
- **Source**: User RFP & UI Mockup (Prototype: Màn 1b - Giám sát khu vực)
- **Acceptance Criteria**:
  1. Xác định chính xác vị trí tâm đối tượng nằm trong hay ngoài đa giác zone (Point-in-polygon).
  2. Phát cảnh báo ngay lập tức nếu loại đối tượng nằm trong danh sách cấm của zone.
  3. Hiển thị danh sách sự kiện khu vực với trạng thái rõ ràng (`Được phép`, `Vi phạm`).
  4. Hiển thị đầy đủ bộ 4 thẻ KPI thống kê realtime cho khu vực bãi kiểm.
- **Status**: approved
- **Delivery classification**: new

### REQ-003: Phân cấp Mức độ Cảnh báo (Alert Severity Classification)
- **Behavior**: Tự động phân loại sự kiện theo 3 mức độ nguy hiểm:
  - Mức 1 (Xanh - Green): Xe quen / Đối tượng hợp lệ / Đúng quy định zone.
  - Mức 2 (Vàng - Yellow): Xe lạ / Cần kiểm tra (chưa tồn tại trong danh sách whitelist/blacklist hoặc sai loại xe nhẹ).
  - Mức 3 (Đỏ - Red): Vi phạm zone cấm / Đối tượng không được phép vào zone.
- **Rationale**: Tránh quá tải thông tin cho người vận hành, ưu tiên tập trung vào các sự kiện có mức độ rủi ro cao.
- **Priority**: P0
- **Source**: Khách hàng xác nhận (Q2 interview & Prototype)
- **Acceptance Criteria**:
  1. Sự kiện mức 3 phải được đánh dấu nổi bật màu đỏ và ưu tiên lên đầu danh sách sự kiện hot.
  2. Sự kiện mức 2 được đánh dấu màu vàng để nhân viên an ninh rà soát.
- **Status**: approved
- **Delivery classification**: new

### REQ-004: Khử trùng lặp sự kiện (Event Deduplication & Cooldown)
- **Behavior**: Áp dụng cơ chế cửa sổ thời gian (Cooldown 10-15 giây) cho mỗi đối tượng/biển số trong cùng một Zone. Khi một đối tượng đứng yên hoặc di chuyển trong zone liên tục, hệ thống chỉ sinh 1 Event chính và 1 Clip 10s đại diện thay vì tạo hàng loạt cảnh báo trùng lặp mỗi giây.
- **Rationale**: Giảm nhiễu báo động giả, tối ưu dung lượng đĩa cứng lưu trữ clip và giữ chất lượng dữ liệu sạch cho AI Q&A.
- **Priority**: P0
- **Source**: Khách hàng xác nhận (Q1 interview & RFP)
- **Acceptance Criteria**:
  1. Trong vòng 15s, cùng một biển số/đối tượng lưu lại trong zone chỉ tạo đúng 1 bản ghi sự kiện.
  2. Nếu đối tượng rời zone và quay lại sau khoảng thời gian cooldown, sự kiện mới được khởi tạo bình thường.
- **Status**: approved
- **Delivery classification**: new

### REQ-005: Cấu hình Zone Đa giác tương tác (Interactive Polygon Zone Setup)
- **Behavior**: Cho phép chọn camera (GATE-01, BAI-KIEM), chuyển đổi giữa công cụ "Chọn" và "Vẽ zone". Chế độ vẽ zone hỗ trợ click từng đỉnh tạo polygon đa giác mới. Chế độ chọn zone cho phép kéo đỉnh ô vuông để chỉnh hình dạng, kéo điểm tròn giữa cạnh để thêm góc mới, kéo thân đa giác để di chuyển zone, và bấm xóa zone. Mỗi zone cho phép cấu hình bật/tắt (toggle ✓ được phép / ✕ cấm) từng loại đối tượng.
- **Rationale**: Linh hoạt thay đổi vùng giám sát theo sơ đồ thực tế của doanh nghiệp mà không cần sửa code.
- **Priority**: P0
- **Source**: User RFP & UI Mockup (Prototype: Màn 2 - Cài đặt vẽ zone)
- **Acceptance Criteria**:
  1. Cấu hình zone vẽ trên UI được cập nhật ngay lập tức xuống AI pipeline mà không cần restart server.
  2. Hỗ trợ thao tác kéo thả đỉnh, thêm đỉnh ở cạnh, di chuyển thân zone mượt mà trên Canvas/SVG.
  3. Cập nhật bảng quy tắc cấm/cho phép theo từng loại xe/đối tượng ngay trên thẻ điều khiển zone.
- **Status**: approved
- **Delivery classification**: new

### REQ-006: Quản lý Biển số Quen / Lạ (Vehicle Whitelist & Blacklist Management)
- **Behavior**: Hiển thị danh sách biển số đã thu thập từ các lượt vào cổng (Ảnh crop, Biển số, Loại xe, Lượt vào, Lần cuối), hỗ trợ 1-click gán nhãn `Xe quen` (được phép) / `Xe lạ` (cần chú ý).
- **Rationale**: Tự động nhận diện xe nội bộ/đã đăng ký vs xe bên ngoài đến làm việc.
- **Priority**: P1
- **Source**: User RFP & UI Mockup (Prototype: Màn 2 - Gắn nhãn xe)
- **Acceptance Criteria**:
  1. Đổi nhãn Xe quen / Xe lạ với 1 click và cập nhật trạng thái ngay cho các sự kiện tiếp theo.
  2. Biển số chưa từng đăng ký khi qua cổng tự động được hệ thống gán nhãn tạm thời là `Xe lạ`.
- **Status**: approved
- **Delivery classification**: new

### REQ-007: Tool Gắn nhãn Mẫu Đối tượng Custom (Custom Object Labeling & Dataset Tool)
- **Behavior**: Cho phép import hình ảnh hoặc video file. Với video, hỗ trợ thanh timeline scrubber (`00:00` - `02:30`) và danh sách tick chọn khung hình để gán nhãn. Người dùng kéo khoanh bbox quanh đối tượng, chọn phân loại (`Người` hoặc `Hình dáng xe`), đặt tên nhãn custom (vd: Xe nâng reach stacker, Người mặc áo phản quang) và bấm "Lưu mẫu đã gắn". Nhãn mới tự động xuất hiện trong danh sách cấu hình loại xe/đối tượng của mọi zone.
- **Rationale**: Mở rộng khả năng phát hiện của AI cho các loại phương tiện/trang phục đặc thù trong nhà máy/cảng biển.
- **Priority**: P1
- **Source**: User RFP & UI Mockup (Prototype: Màn 2 - Gắn nhãn đối tượng)
- **Acceptance Criteria**:
  1. Hỗ trợ gắn nhiều mẫu bbox trên cùng một khung hình và lưu batch ("Lưu X mẫu đã gắn").
  2. Hỗ trợ timeline duyệt các khung hình từ file video import.
  3. Nhãn mới lưu xong lập tức đồng bộ vào danh sách phân loại đối tượng cho tất cả các zone.
- **Status**: approved
- **Delivery classification**: new

### REQ-008: AI Assistant Hỏi đáp Sự kiện kèm Clip Chứng cứ (AI Event Q&A Agent)
- **Behavior**: Cung cấp giao diện Chatbot bằng ngôn ngữ tự nhiên (tiếng Việt). Hiển thị các nút câu hỏi gợi ý nhanh (Prompt Chips). Người dùng nhập các thắc mắc (vd: *"Hôm nay có bao nhiêu xe lạ vào?"*, *"Có xe máy nào vào khu vực cấm không?"*), AI sử dụng LLM (Text-to-SQL / Structured Query) truy vấn CSDL sự kiện, tổng hợp câu trả lời số liệu kèm đính kèm trình phát video và nút tải Clip 10s làm chứng cứ. Hỗ trợ fallback Rule-based khi không có API key.
- **Rationale**: Tra cứu sự cố, truy xuất dữ liệu an ninh nhanh chóng bằng lời nói/văn bản thay vì rà soát video thủ công tốn hàng giờ.
- **Priority**: P0
- **Source**: User RFP & UI Mockup (Prototype: Màn 3 - Hỏi đáp AI)
- **Acceptance Criteria**:
  1. Trả lời chính xác số lượng và chi tiết sự kiện theo đúng mốc thời gian / lọc zone người dùng hỏi.
  2. Mỗi câu trả lời về sự kiện vi phạm/cụ thể BẮT BUỘC kèm theo thẻ xem video clip 10s phát trực tiếp trên giao diện (có bbox highlight đối tượng) và nút tải xuống.
  3. Hiển thị thanh gợi ý câu hỏi nhanh (Prompt Chips) hỗ trợ người dùng chọn câu hỏi phổ biến.
- **Status**: approved
- **Delivery classification**: new

### REQ-009: Cảnh báo Tức thì Đa kênh cho Bảo vệ / Người thực thi (Real-time Multi-channel Alerts)
- **Behavior**: Khi phát sinh sự kiện Mức 3 (Vi phạm zone cấm / Xe cấm xâm nhập), hệ thống lập tức phát âm thanh cảnh báo còi hiệu (audio alert beep) và popup nổi bật trên Web UI, đồng thời gửi thông báo sự kiện (kèm hình ảnh/chi tiết) qua Telegram Bot / Zalo OA đến điện thoại của nhân viên an ninh / bảo vệ trực ca.
- **Rationale**: Đảm bảo lực lượng an ninh phản ứng tức thì với các vi phạm mà không cần ngồi giám sát liên tục màn hình.
- **Priority**: P1 (Ưu tiên cao)
- **Source**: Khách hàng đề xuất & xác nhận bổ sung
- **Acceptance Criteria**:
  1. Phát tiếng bíp / âm thanh còi cảnh báo ngay trên trình duyệt Web UI khi có WebSocket event Mức 3.
  2. Gửi tin nhắn chứa chi tiết thời gian, camera, zone vi phạm và ảnh crop sang Telegram Bot trong thời gian < 2 giây.
- **Status**: approved
- **Delivery classification**: new

---

## 3. Tiêu chí Nghiệm thu Tổng thể (Global Acceptance Criteria)
1. Chạy mượt mà với 2 video demo mẫu (Cổng GATE-01 và Bãi kiểm BAI-KIEM) ở tốc độ FPS >= 5.
2. Trích xuất đúng 10s video clip cho mọi sự kiện vi phạm hoặc xe qua cổng.
3. Giao diện bám sát 100% thiết kế và trải nghiệm từ mẫu `Intern-LPR-Gate.dc.html` (đủ 4 tab: Giám sát cổng, Giám sát khu vực, Cài đặt, Hỏi đáp AI).

---
artifact: REQUIREMENTS.md
version: 1.6.0
owner: collect-requirements
status: approved
updated_at: "2026-08-24T22:06:32+07:00"
---

Discovery status: confirmed
Delivery scope: change-request

# Đặc tả Yêu cầu Hệ thống Giám sát Camera AI (SentriAI Mini)

## 1. Mạch Nghiệp vụ & Phạm vi (Scope Summary)

Hệ thống cung cấp giải pháp giám sát an ninh camera AI tự động cho 2 kịch bản chính (Cổng vào LPR và Giám sát Khu vực Zone), sử dụng mô hình phát hiện đối tượng **YOLOv26**, kết hợp quản lý danh sách biển số, vẽ zone đa giác linh hoạt bằng SVG Canvas, gán nhãn mẫu đối tượng custom, và AI Assistant hỏi đáp sự kiện bằng ngôn ngữ tự nhiên kèm clip chứng cứ 10 giây. Giao diện người dùng được xây dựng trên nền tảng React Framework hiện đại (Vite + React / Next.js) kết hợp Tailwind CSS, Lucide React icons, Recharts và SVG Canvas.

---

## 2. Nhật ký Thay đổi Yêu cầu (Change Requests Audit Trail)

## CR-001 Baseline Business Logic & Polygon Zone Refinements

- Business delta: Chuẩn hóa phân loại 8 loại phương tiện/người trong bãi kiểm (Container, Xe tải, Xe nâng, Xe cẩu, Xe con, Xe máy, Xe đạp, Người); phân định danh sách Cho phép / Bị cấm cho từng zone; chuẩn hóa xe quen (đã xác thực) / xe lạ (chưa ghi nhận); nâng cấp công cụ vẽ zone đa giác SVG 4 thao tác (thêm góc, kéo đỉnh, kéo điểm giữa cạnh, kéo thân); xây dựng công cụ gán nhãn đối tượng Bounding Box tương tác (import hình/video frame, khoanh ô bao, phân loại người/xe, lưu mẫu & tự động đồng bộ sang mọi zone).
- Affected requirement IDs: `REQ-002`, `REQ-005`, `REQ-006`, `REQ-007`
- Previous meaning: Phân loại đối tượng cứng (Person, Truck, Forklift), quy tắc zone mâu thuẫn, phân loại xe cũ (WHITELIST/BLACKLIST/CONTRACTOR/VISITOR), vẽ zone tĩnh thiếu thao tác kéo thả và công cụ gán nhãn mẫu custom chưa hỗ trợ Bounding Box/tải hình.
- Source: Đánh giá kiểm thử Prototype bãi kiểm và cài đặt từ Khách hàng / Product Owner
- Status: active

---

## CR-002 Modernization of Web UI Stack to React Framework & YOLOv26

- Business delta: Chuyển đổi giao diện người dùng từ HTML5/Vanilla JS sang React Framework hiện đại (Vite + React / Next.js, Tailwind CSS, Lucide React icons, Recharts cho đồ thị KPI, SVG Canvas cho Zone Editor) kết hợp React State & Hooks quản lý luồng dữ liệu thời gian thực. Cập nhật mô hình AI Vision mặc định sang YOLOv26.
- Affected requirement IDs: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`, `REQ-006`, `REQ-007`, `REQ-008`, `REQ-009`
- Previous meaning: Giao diện người dùng xây dựng bằng HTML5, Vanilla JS, inline SVG và DOM manipulation thủ công; mô hình phát hiện đối tượng sử dụng YOLOv8.
- Source: Yêu cầu hiện đại hóa công nghệ từ Khách hàng / Product Owner
- Status: active

---

## CR-003 Area Realtime Metadata Lane & In-memory Zone Cache

- Business delta: Với luồng Giám sát Khu vực, hệ thống phải tách riêng `video stream lane`, `realtime metadata lane`, và `event/alert lane`; duy trì zone cache in-memory theo `camera_id`; và loại bỏ DB khỏi hot path xử lý từng frame.
- Affected requirement IDs: `REQ-002`, `REQ-004`, `REQ-005`, `REQ-009`
- Previous meaning: UI khu vực có thể dựa vào event feed/polling để phản ánh trạng thái gần realtime; cooldown event và metadata frame-to-frame chưa được tách nghĩa rõ; zone update chỉ được mô tả ở mức "cập nhật xuống AI pipeline" mà chưa ràng buộc cache/invalidation runtime.
- Source: Change request CR-003, `.delivery/changes/CR-003/CHANGE-IMPACT.md`
- Status: active

---

## CR-004 Real Object Labeling Flow in Settings

- Business delta: Chuyển chức năng `Nhãn đối tượng` trong tab `Cài đặt` từ mock/local state sang flow dữ liệu thật: import ảnh/video được backend lưu file và metadata để tải lại; chọn frame video bằng timeline scrubber; vẽ, lưu, sửa và xóa bbox samples trong DB; quản lý nhãn custom với tạo, sửa tên, soft delete và restore; tự động đồng bộ nhãn custom vào danh sách loại đối tượng của mọi zone với trạng thái mặc định là `cấm`. 8 loại đối tượng mặc định là nhãn hệ thống bị khóa sửa tên/xóa nhưng vẫn được chọn để gắn bbox samples.
- Affected requirement IDs: `REQ-005`, `REQ-007`
- Previous meaning: Công cụ nhãn đối tượng đã được mô tả ở mức import hình/video frame, khoanh bbox, đặt nhãn và đồng bộ vào zone, nhưng chưa ràng buộc file media thật được backend lưu lại, reload persisted samples từ DB, sửa bbox đã lưu, soft delete/restore nhãn custom, uniqueness tên nhãn, batch validation, hay rule mặc định `cấm` khi sync vào zone rules.
- Source: Phỏng vấn Product Owner cho CR-004 ngày 2026-08-24, dựa trên `.delivery/changes/CR-004/CHANGE-IMPACT.md`
- Status: active

---

## CR-005 Area Violation Telegram Evidence Notification

- Business delta: Khi đối tượng thuộc danh sách cấm đi vào zone trong luồng giám sát khu vực, hệ thống phải gửi đúng 1 thông báo Telegram cho event đầu tiên đã qua dedup/cooldown, kèm tin nhắn chứa thời gian vi phạm đúng, camera, zone, loại đối tượng, lý do vi phạm và gửi trực tiếp file video clip chứng cứ 10s. Nếu Telegram gửi lỗi, event/clip vẫn được lưu và UI vẫn cảnh báo; lỗi gửi Telegram được ghi nhận để kiểm tra sau.
- Affected requirement IDs: `REQ-002`, `REQ-003`, `REQ-004`, `REQ-008`, `REQ-009`
- Previous meaning: Thông báo Telegram cho sự kiện Mức 3 mới ràng buộc chi tiết thời gian, camera, zone vi phạm và ảnh crop trong thời gian dưới 2 giây; chưa chốt phạm vi chỉ cho đối tượng cấm vào zone khu vực, chưa bắt buộc gửi trực tiếp video clip 10s, chưa định nghĩa "thời gian vi phạm đúng", chưa ràng buộc loại đối tượng/lý do vi phạm trong nội dung Telegram, và chưa chốt hành vi khi Telegram gửi thất bại.
- Source: Phỏng vấn Product Owner cho CR-005 ngày 2026-08-24, dựa trên yêu cầu nghiệp vụ "Khi có vi phạm ở giám sát khu vực..." và xác nhận tóm tắt discovery trong phiên làm việc.
- Status: active

---

## 3. Danh sách Yêu cầu Sản phẩm (Product Requirements)

## REQ-001 Nhận diện biển số xe tại Cổng (LPR Gate Monitoring)

- Behavior: Hệ thống đọc stream video từ camera cổng (`GATE-01`), tự động phát hiện bằng mô hình **YOLOv26** và nhận diện biển số xe (LPR) khi xe đi vào zone làn IN (Làn IN 1, Làn IN 2). Giao diện React render bounding box biển số, chuỗi biển số và độ tin cậy realtime thông qua React Custom Hooks (`useWebSocket`). Hiển thị khối chỉ số KPI trực tiếp (Lượt xe qua cổng, Biển số đọc được, Không đọc được, Độ tin cậy trung bình) bằng các thẻ Recharts visualizer widgets.
- Rationale: Kiểm soát tự động lưu lượng phương tiện ra vào cổng mà không cần nhân viên ghi chép thủ công.
- Priority: P0
- Source: User RFP & UI Mockup (Prototype: Màn 1 - Giám sát cổng)
- Acceptance criteria: 1. Nhận diện chính xác biển số xe với độ tin cậy >= 85% trong điều kiện ánh sáng chuẩn bằng YOLOv26 & OCR Engine. 2. Ghi nhận thời gian, camera_id, làn IN, chuỗi biển số, ảnh crop biển số và lưu clip 10s. 3. Thời gian phản hồi cập nhật trên React UI realtime < 1 giây kể từ khi xe đi vào làn IN. 4. Hiển thị đúng 4 thẻ KPI thống kê trực tiếp sử dụng Recharts components: Lượt xe qua cổng, Biển số đọc được, Không đọc được, Độ tin cậy trung bình.
- Status: approved
- Delivery classification: changed

## REQ-002 Giám sát Khu vực & Kiểm tra Quy tắc Zone (Area Zone Violations)

- Behavior: Hệ thống đọc stream camera khu vực (`BAI-KIEM`), phát hiện và phân loại đối tượng (người, xe container, xe tải, xe nâng, xe cẩu, xe con, xe máy, xe đạp) bằng mô hình **YOLOv26** theo vị trí tâm (bounding box center) trong các Zone đa giác. Luồng runtime phải tách riêng `video stream lane` và `realtime metadata lane`: video renderer tiếp tục phục vụ hiển thị khung hình, còn metadata lane phát snapshot theo frame gồm đối tượng, zone hit, trạng thái stream và latency để UI cập nhật overlay/KPI mà không phụ thuộc vào polling event history. So sánh với quy tắc cấm/cho phép của từng Zone để sinh cảnh báo vi phạm khi có đối tượng thuộc danh sách cấm đi vào zone, kèm loại đối tượng và lý do vi phạm đủ rõ để dùng lại trong Event Feed, AI Assistant và Telegram evidence notification. Giao diện React hiển thị các thẻ KPI giám sát khu vực sử dụng Recharts (Đối tượng trong khu, Vi phạm loại xe, Xe nâng/container hoạt động, Tổng số zone).
- Rationale: Đảm bảo an toàn lao động và ngăn chặn truy cập trái phép vào vùng cấm trong khu vực bãi kiểm/kho hàng.
- Priority: P0
- Source: User RFP & UI Mockup (Prototype: Màn 1b - Giám sát khu vực)
- Acceptance criteria: 1. Mô hình YOLOv26 xác định chính xác bounding box và vị trí tâm đối tượng nằm trong hay ngoài đa giác zone (Point-in-polygon). 2. UI khu vực nhận snapshot metadata realtime theo frame/sampling interval mà không cần polling `events` để cập nhật overlay hoặc KPI gần realtime. 3. Phát cảnh báo ngay lập tức nếu loại đối tượng nằm trong danh sách cấm của zone. 4. Sự kiện vi phạm khu vực ghi nhận được camera, zone, loại đối tượng và lý do vi phạm theo nghĩa "đối tượng thuộc danh sách cấm đi vào zone". 5. Hiển thị danh sách sự kiện khu vực trên React Event Feed với trạng thái rõ ràng (Được phép, Vi phạm) như một lane dẫn xuất riêng khỏi metadata lane. 6. Hiển thị đầy đủ bộ 4 thẻ KPI thống kê realtime cho khu vực bãi kiểm qua Recharts visualizers.
- Status: approved
- Delivery classification: changed

## REQ-003 Phân cấp Mức độ Cảnh báo (Alert Severity Classification)

- Behavior: Tự động phân loại sự kiện theo 3 mức độ nguy hiểm và quản lý bằng React State badges: Mức 1 (Xanh - Green): Xe quen / Đối tượng hợp lệ / Đúng quy định zone; Mức 2 (Vàng - Yellow): Xe lạ / Cần kiểm tra; Mức 3 (Đỏ - Red): Vi phạm zone cấm / Đối tượng không được phép vào zone. Trong CR-005, chỉ sự kiện Mức 3 của luồng giám sát khu vực do đối tượng thuộc danh sách cấm đi vào zone mới thuộc phạm vi gửi Telegram evidence notification.
- Rationale: Tránh quá tải thông tin cho người vận hành, ưu tiên tập trung vào các sự kiện có mức độ rủi ro cao.
- Priority: P0
- Source: Khách hàng xác nhận (Q2 interview & Prototype)
- Acceptance criteria: 1. Sự kiện mức 3 được React UI đánh dấu nổi bật badge màu đỏ và tự động sắp xếp lên đầu danh sách sự kiện hot. 2. Sự kiện mức 2 được đánh dấu màu vàng để nhân viên an ninh rà soát. 3. Telegram evidence notification của CR-005 không được kích hoạt bởi sự kiện không phải vi phạm zone cấm trong luồng giám sát khu vực.
- Status: approved
- Delivery classification: changed

## REQ-004 Khử trùng lặp sự kiện (Event Deduplication & Cooldown)

- Behavior: Áp dụng cơ chế cửa sổ thời gian (Cooldown 10-15 giây) cho mỗi đối tượng/biển số trong cùng một Zone trên `event/alert lane`. Khi một đối tượng đứng yên hoặc di chuyển trong zone liên tục, hệ thống chỉ sinh 1 Event chính, 1 Clip 10s đại diện và, với CR-005, chỉ 1 thông báo Telegram cho event đầu tiên đã qua dedup. Cooldown không được chặn việc phát `realtime metadata lane`; metadata snapshot cho giám sát khu vực vẫn phải tiếp tục được publish để UI cập nhật trạng thái frame-to-frame mà không làm giật lag giao diện.
- Rationale: Giảm nhiễu báo động giả, tối ưu dung lượng đĩa cứng lưu trữ clip và giữ chất lượng dữ liệu sạch cho AI Q&A.
- Priority: P0
- Source: Khách hàng xác nhận (Q1 interview & RFP)
- Acceptance criteria: 1. Trong vòng 15s, cùng một biển số/đối tượng lưu lại trong zone chỉ tạo đúng 1 bản ghi sự kiện. 2. Trong cùng cửa sổ cooldown, cùng một đối tượng trong cùng zone cấm không được gửi thêm Telegram nếu đã gửi cho event đầu tiên. 3. Nếu đối tượng rời zone và quay lại sau khoảng thời gian cooldown, sự kiện mới được khởi tạo bình thường và hiển thị lên React UI Feed. 4. Trong suốt thời gian cooldown, metadata lane vẫn tiếp tục phản ánh sự hiện diện/chuyển động của đối tượng trên dashboard khu vực.
- Status: approved
- Delivery classification: changed

## REQ-005 Cấu hình Zone Đa giác tương tác (Interactive Polygon Zone Setup)

- Behavior: Cung cấp React UI Component SVG Canvas Editor (`<PolygonZoneEditor>`) cho phép chọn camera (`GATE-01`, `BAI-KIEM`), chuyển đổi giữa công cụ Chọn và Vẽ zone. Chế độ vẽ zone hỗ trợ click từng đỉnh tạo polygon đa giác mới qua React state. Chế độ chọn zone cho phép kéo đỉnh ô vuông để chỉnh hình dạng, kéo điểm tròn giữa cạnh để thêm góc mới, kéo thân đa giác để di chuyển zone, và bấm xóa zone. Mỗi zone cho phép cấu hình bật/tắt (toggle ✓ được phép / ✕ cấm) từng loại đối tượng. Danh sách loại đối tượng của zone gồm 8 loại mặc định và các nhãn custom đang hoạt động được đồng bộ từ công cụ `Nhãn đối tượng`; nhãn custom mới hoặc được restore phải tự động xuất hiện trong mọi zone với trạng thái mặc định là `cấm`. Backend phải duy trì zone cache in-memory theo `camera_id`, trong đó DB là source of truth cho CRUD còn runtime cache là source trực tiếp cho luồng xử lý frame khu vực.
- Rationale: Linh hoạt thay đổi vùng giám sát theo sơ đồ thực tế của doanh nghiệp mà không cần sửa code.
- Priority: P0
- Source: User RFP & UI Mockup (Prototype: Màn 2 - Cài đặt vẽ zone)
- Acceptance criteria: 1. Cấu hình zone vẽ trên React SVG Canvas UI được cập nhật ngay lập tức xuống AI pipeline mà không cần restart server. 2. Sau mỗi thao tác CRUD zone hoặc đồng bộ nhãn custom vào zone rules, runtime cache theo `camera_id` được refresh/invalidate thành công để frame loop áp dụng quy tắc mới mà không cần DB read cho từng frame. 3. Hỗ trợ thao tác kéo thả đỉnh, thêm đỉnh ở cạnh, di chuyển thân zone mượt mà trên React SVG Canvas với Custom Hook `usePolygonEditor`. 4. Cập nhật bảng quy tắc cấm/cho phép theo từng loại xe/đối tượng ngay trên thẻ điều khiển zone với Lucide React icons (Check, X). 5. Khi nhãn custom mới được tạo hoặc restore, nhãn đó xuất hiện trong danh sách loại đối tượng của mọi zone với trạng thái mặc định là `cấm`; người dùng có thể đổi trạng thái theo từng zone sau đó.
- Status: approved
- Delivery classification: changed

## REQ-006 Quản lý Biển số Quen / Lạ (Vehicle Whitelist & Blacklist Management)

- Behavior: Hiển thị danh sách biển số thu thập từ các lượt vào cổng dưới dạng React Data Table (`<VehicleTagTable>`) (Ảnh crop, Biển số, Loại xe, Lượt vào, Lần cuối), hỗ trợ 1-click gán nhãn Xe quen (được phép) / Xe lạ (cần chú ý) sử dụng React state & API service handlers.
- Rationale: Tự động nhận diện xe nội bộ/đã đăng ký vs xe bên ngoài đến làm việc.
- Priority: P1
- Source: User RFP & UI Mockup (Prototype: Màn 2 - Gắn nhãn xe)
- Acceptance criteria: 1. Đổi nhãn Xe quen / Xe lạ với 1 click và cập nhật trạng thái tức thì trên React UI cho các sự kiện tiếp theo. 2. Biển số chưa từng đăng ký khi qua cổng tự động được hệ thống gán nhãn tạm thời là Xe lạ.
- Status: approved
- Delivery classification: changed

## REQ-007 Tool Gắn nhãn Mẫu Đối tượng Custom (Custom Object Labeling & Dataset Tool)

- Behavior: Cho phép import hình ảnh hoặc video file vào React Component `<DatasetAnnotator>`; file import được backend lưu cùng metadata để có thể tải lại source/frame và bbox samples sau khi reload trang. Với video, người dùng dùng timeline scrubber để chọn frame hiện tại, vẽ nhiều bbox trên frame đó, lưu, rồi chuyển sang frame khác nếu cần. Người dùng kéo khoanh bbox quanh đối tượng trên canvas React, chọn nhãn từ 8 nhãn hệ thống hoặc nhãn custom, và lưu batch mẫu đã gắn vào DB. 8 nhãn mặc định là nhãn hệ thống: không được sửa tên hoặc xóa, nhưng vẫn được chọn để gắn bbox samples và bổ sung dữ liệu huấn luyện. Nhãn custom hỗ trợ tạo mới, sửa tên, soft delete và restore không giới hạn thời gian; tên nhãn custom phải duy nhất không phân biệt hoa/thường. Nhãn custom mới hoặc được restore tự động xuất hiện trong danh sách cấu hình của mọi zone với trạng thái mặc định là `cấm`. Nhãn custom mới chỉ cam kết quản lý dataset/rules, chưa bắt buộc AI realtime nhận diện class mới nếu chưa có model đã huấn luyện.
- Rationale: Mở rộng khả năng phát hiện của mô hình YOLOv26 cho các loại phương tiện/trang phục đặc thù trong nhà máy/cảng biển.
- Priority: P1
- Source: User RFP & UI Mockup (Prototype: Màn 2 - Gắn nhãn đối tượng)
- Acceptance criteria: 1. Sau khi import ảnh/video, reload trang vẫn tải lại được media source, metadata, frame đang gắn nhãn và các bbox samples đã lưu từ DB. 2. Hỗ trợ gắn nhiều mẫu bbox trên cùng một frame và lưu batch; nếu bất kỳ sample nào thiếu nhãn, bbox rỗng/quá nhỏ hoặc source/frame không hợp lệ thì toàn bộ batch không được lưu và người dùng nhận được lỗi để sửa. 3. Với video, timeline scrubber cho phép chọn frame hiện tại để vẽ bbox; không yêu cầu batch liên frame hoặc gallery trích frame tự động trong CR-004. 4. BBox sample đã lưu có thể được chọn để chỉnh lại khung bbox hoặc đổi nhãn, và thay đổi phải được lưu/tải lại từ DB. 5. 8 nhãn hệ thống không thể sửa tên hoặc xóa, nhưng có thể được chọn để gắn thêm bbox samples và tăng số lượng mẫu. 6. Nhãn custom mới phải có tên duy nhất không phân biệt hoa/thường; đổi tên nhãn custom cập nhật xuyên suốt samples và zone rules mà không tạo nhãn mới. 7. Không cho xóa nhãn custom đang được dùng trong zone rules; với nhãn không còn được dùng, hệ thống hỏi xác nhận trước khi soft delete, giữ samples để restore và không giới hạn thời gian restore trong CR-004. 8. Khi tạo hoặc restore nhãn custom, hệ thống tự động đồng bộ nhãn vào danh sách loại đối tượng của mọi zone với trạng thái mặc định là `cấm`.
- Status: approved
- Delivery classification: changed

## REQ-008 AI Assistant Hỏi đáp Sự kiện kèm Clip Chứng cứ (AI Event Q&A Agent)

- Behavior: Cung cấp React UI Component Chatbot (`<AIChatbotAssistant>`) với ngôn ngữ tự nhiên (tiếng Việt). Hiển thị các nút câu hỏi gợi ý nhanh (Prompt Chips). Người dùng nhập thắc mắc (vd: "Hôm nay có bao nhiêu xe lạ vào?", "Có xe máy nào vào khu vực cấm không?"), AI sử dụng LLM Text-to-SQL truy vấn CSDL, tổng hợp câu trả lời số liệu kèm đính kèm trình phát video `<VideoModal>` đính kèm clip 10s chứng cứ và nút tải về. Với sự kiện vi phạm khu vực thuộc CR-005, mốc thời gian, camera, zone, loại đối tượng, lý do vi phạm và clip 10s phải nhất quán với event được dùng để gửi Telegram.
- Rationale: Tra cứu sự cố, truy xuất dữ liệu an ninh nhanh chóng bằng lời nói/văn bản thay vì rà soát video thủ công tốn hàng giờ.
- Priority: P0
- Source: User RFP & UI Mockup (Prototype: Màn 3 - Hỏi đáp AI)
- Acceptance criteria: 1. Trả lời chính xác số lượng và chi tiết sự kiện theo đúng mốc thời gian / lọc zone người dùng hỏi. 2. Mỗi câu trả lời về sự kiện vi phạm/cụ thể BẮT BUỘC kèm theo thẻ xem video clip 10s trong modal `<VideoModal>` (có bbox highlight đối tượng) và nút tải xuống. 3. Với sự kiện vi phạm khu vực được gửi Telegram theo CR-005, AI Assistant truy xuất cùng mốc thời gian vi phạm đúng và cùng clip 10s chứng cứ của event đó. 4. Hiển thị thanh gợi ý câu hỏi nhanh (Prompt Chips) với Lucide React icons hỗ trợ người dùng chọn câu hỏi phổ biến.
- Status: approved
- Delivery classification: changed

## REQ-009 Cảnh báo Tức thì Đa kênh cho Bảo vệ / Người thực thi (Real-time Multi-channel Alerts)

- Behavior: Khi phát sinh sự kiện Mức 3 (Vi phạm zone cấm / Xe cấm xâm nhập), hệ thống phát âm thanh cảnh báo còi hiệu thời gian thực thông qua React shared component `<AudioBeepPlayer>` (Web Audio API context) và popup nổi bật trên React UI, đồng thời gửi thông báo qua Telegram Bot / Zalo OA. Với CR-005, khi đối tượng thuộc danh sách cấm đi vào zone trong luồng giám sát khu vực, Telegram Bot phải gửi trực tiếp file video clip chứng cứ 10s kèm tin nhắn có thời gian vi phạm đúng, camera, zone, loại đối tượng và lý do vi phạm. Lane cảnh báo Mức 3 phải được dẫn xuất từ event đã qua phân loại/dedup, không lấy trực tiếp từ metadata snapshot để tránh lặp còi hoặc cảnh báo giả.
- Rationale: Đảm bảo lực lượng an ninh phản ứng tức thì với các vi phạm mà không cần ngồi giám sát liên tục màn hình.
- Priority: P1
- Source: Khách hàng đề xuất & xác nhận bổ sung
- Acceptance criteria: 1. Component `<AudioBeepPlayer>` phát tiếng bíp còi hiệu ngay trên trình duyệt khi có WebSocket event Mức 3 từ event lane đã dedup. 2. Với vi phạm khu vực do đối tượng thuộc danh sách cấm đi vào zone, Telegram Bot gửi tin nhắn chứa tối thiểu thời gian vi phạm đúng, camera, zone, loại đối tượng và lý do vi phạm. 3. Telegram Bot gửi trực tiếp file video clip chứng cứ 10s gắn với cùng event vi phạm khu vực. 4. Thời gian vi phạm đúng là thời điểm frame đầu tiên được xác nhận là vi phạm sau khi qua luật zone và dedup, không phải thời điểm bắt đầu clip hoặc thời điểm lưu event. 5. Nếu gửi Telegram thất bại, event và clip vẫn được lưu, UI vẫn cảnh báo, và lỗi gửi Telegram được ghi nhận để kiểm tra sau. 6. Metadata lane có thể phản ánh đối tượng vi phạm trước hoặc đồng thời với alert, nhưng không được tự kích hoạt audio/notification nếu chưa có event Mức 3 hợp lệ.
- Status: approved
- Delivery classification: changed

---

## 4. Tiêu chí Nghiệm thu Tổng thể (Global Acceptance Criteria)

1. Chạy mượt mà với 2 video demo mẫu (Cổng GATE-01 và Bãi kiểm BAI-KIEM) ở tốc độ FPS >= 5 với mô hình YOLOv26.
2. Trích xuất đúng 10s video clip cho mọi sự kiện vi phạm hoặc xe qua cổng.
3. Giao diện React đạt 100% chức năng & bố cục thiết kế chuẩn (đủ 4 trang/tab chính: Gate Dashboard, Area Security Dashboard, Zone & Tag Settings, AI Chatbot Assistant, cùng 4 shared components: Header, Sidebar, Audio Beep Alert Player, Video Modal 10s).

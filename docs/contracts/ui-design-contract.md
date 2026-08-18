---
artifact: UI-DESIGN-CONTRACT
task_id: TASK-005
status: completed
updated_at: "2026-08-18T14:20:40+07:00"
---

# Hợp Đồng Thiết Kế UI/UX Foundation & Quy Chuẩn Giao Diện (SentriAI Mini)

## 1. Định Hướng Thiết Kế & Nguyên Tắc Đánh Giá
- **Thiết kế dựa trên Prototype**: Giao diện UI tuân thủ đúng luồng nghiệp vụ và bố cục 4 tab chính theo mẫu Prototype `Intern-LPR-Gate.dc.html` và `RFP Bài tập Intern.dc.html`.
- **Tối ưu trải nghiệm (WOW Factor)**: Áp dụng CSS mượt mà, dark theme hiện đại, màu sắc trực quan theo phân cấp cảnh báo Level 1/2/3.
- **Không bắt buộc Pixel-Perfect**: Theo đúng tiêu chí đánh giá bài tập RFP, giao diện tập trung vào tính hoạt động mượt mà của luồng nghiệp vụ, không ép buộc sao chép từng pixel so với prototype HTML.

## 2. Bố Cục 4 Tab Chính
1. **Tab 1 — Giám Sát Cổng LPR (`gate_dashboard.js`)**:
   - Khung xem video stream Cổng (`GATE-01.mp4`).
   - 4 Thẻ KPI: Tổng lượt xe, Xe quen (whitelist), Xe lạ, Tỷ lệ OCR thành công (%).
   - Danh sách nhận diện biển số realtime kèm nút/popover sửa tay biển số `plate_correction_modal.js` khi confidence < 85%.
2. **Tab 2 — Giám Sát Bãi Kiểm Hàng (`area_dashboard.js`)**:
   - Khung xem video stream Bãi kiểm (`BAI-KIEM.mp4`).
   - 4 Thẻ KPI Bãi kiểm: Tổng đối tượng, Vi phạm Zone, Số lượt Container, Số lượt Xe nâng/cẩu.
   - Hiển thị Overlay đa giác Zone và BBox đối tượng theo màu Severity Level (Xanh: L1, Vàng: L2, Đỏ: L3).
3. **Tab 3 — AI Assistant Q&A Chatbot (`ai_chatbot.js`)**:
   - Khung Chatbot hỏi đáp sự kiện ngôn ngữ tự nhiên bằng tiếng Việt.
   - Nút Prompt Chips gợi ý nhanh ("Hôm nay có xe lạ nào vào không?", "Cho tôi xem xe vi phạm zone bãi kiểm").
   - Trình phát video MP4 10s trích xuất sự kiện chứng cứ kèm nút tải xuống clip (`video_modal.js`).
4. **Tab 4 — Cấu Hình & Gán Nhãn (`settings/`)**:
   - `zone_editor.js`: Công cụ vẽ/chỉnh sửa Zone đa giác SVG tương tác (2 chế độ Chọn/Vẽ kéo thả).
   - `vehicle_tagger.js`: Quản lý danh sách biển số xe quen / xe lạ 1-click.
   - `custom_labeler.js`: Tool khoanh BBox gán nhãn mẫu custom dataset kèm timeline scrubber.

## 3. UI Tokens & Color Palette
- **Severity Level 1 (Thông tin)**: Neutral Blue (`#3B82F6`)
- **Severity Level 2 (Cảnh báo nhẹ)**: Amber/Yellow (`#F59E0B`)
- **Severity Level 3 (Báo động nghiêm trọng)**: Crimson Red (`#EF4444`) - Kèm Web Sound Beep & Telegram Alert.

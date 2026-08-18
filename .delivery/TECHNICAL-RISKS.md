---
artifact: TECHNICAL-RISKS
version: 1.0.0
owner: Software Architect & Engineering Team
status: approved
updated_at: 2026-08-17T22:39:59+07:00
---

# Đánh giá Rủi ro Kỹ thuật (Technical Risks & Mitigations) - SentriAI Mini

## 1. Danh sách Rủi ro Kỹ thuật & Biện pháp Giảm thiểu

| Risk ID | Mô tả Rủi ro | Tác động (Impact) | Xác suất (Probability) | Nguyên nhân & Triệu chứng | Biện pháp Giảm thiểu (Mitigation Strategy) | Rủi ro Tồn dư |
|---|---|---|---|---|---|---|
| **TR-001** | Trễ luồng xử lý Video AI (FPS drop < 5 FPS) khi chạy đồng thời LPR và YOLO trên CPU. | Cao | Trung bình | Mô hình YOLO và OCR ngốn tài nguyên CPU khi xử lý khung hình 1080p liên tục. | 1. Resize khung hình đầu vào xuống 640x360 cho AI inferencing.<br>2. Hạ tần số quét AI xuống 5-10 FPS thay vì 30 FPS.<br>3. Chạy luồng Capture và AI ở 2 thread riêng biệt. | Nhẹ, đạt &ge; 10 FPS ổn định trên CPU thông thường. |
| **TR-002** | Trình duyệt không phát trực tiếp được clip 10s do lỗi Codec / Format video. | Cao | Thấp | File video xuất ra dùng H.265 / AVI / Motion-JPEG mà trình duyệt web không hỗ trợ native. | Bắt buộc mã hóa clip 10s bằng H.264 (libx264) + audio AAC qua OpenCV/FFmpeg wrapper. | Thấp, tương thích 100% Chrome/Edge/Safari. |
| **TR-003** | Khung hình bị giật lag khi người dùng vẽ/chỉnh sửa Zone đa giác trên Canvas Web UI. | Trung bình | Thấp | Xử lý DOM redraw quá nhiều lần khi kéo thả đỉnh polygon. | Dùng SVG overlay thay vì re-render HTML Canvas liên tục; tối ưu hàm drag handler. | Thấp. |
| **TR-004** | LLM API bị quá thời gian phản hồi (Timeout > 5s) hoặc hết API Key / Quota. | Cao | Trung bình | Mạng chậm hoặc hết quota OpenAI/Gemini làm nghẽn tính năng Hỏi đáp AI. | Triển khai Fallback Rule-based Keyword Matcher chạy local offline. Khi LLM lỗi/timeout > 3s, tự chuyển sang Rule-based matcher. | Thấp. |
| **TR-005** | Tốn dung lượng ổ đĩa do ghi quá nhiều clip 10s khi có nhiều vi phạm liên tục. | Trung bình | Trung bình | Chưa áp dụng Cooldown hoặc đối tượng đứng yên trong zone gây sinh clip liên tục. | 1. Ép buộc cơ chế Cooldown 10-15s (`REQ-004`).<br>2. Thêm Cron job / Background Task dọn dẹp các clip cũ hơn 7 ngày. | Thấp, giữ dung lượng đĩa < 1 GB. |

---

## 2. Kế hoạch Dự phòng Kỹ thuật (Contingency Plan)

1. **Khi không có GPU**: Chạy YOLOv8n (nano) hoặc YOLOv11n (bản nhẹ nhất) đã được export sang ONNX Runtime / OpenVINO CPU mode.
2. **Khi không có API Key cho AI Q&A**: Sử dụng Rule-based Matcher quét từ khóa trong câu hỏi (ví dụ: `xe lạ`, `xe máy`, `container`, `vi phạm`, `15R-158.45`) để truy vấn trực tiếp CSDL SQLite và trả về kết quả chuẩn xác.

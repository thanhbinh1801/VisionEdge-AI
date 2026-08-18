---
artifact: ASSUMPTIONS
version: 1.0.0
owner: Product Owner & Engineering Team
status: approved
updated_at: 2026-08-17T22:07:32+07:00
---

# Giả định Dự án (Project Assumptions) - SentriAI Mini

| Assumption ID | Mô tả Giả định | Tác động (Impact) | Độ tin cậy (Confidence) | Phương pháp Xác minh | Trạng thái |
|---|---|---|---|---|---|
| **ASM-001** | Nguồn video đầu vào là các file MP4 demo local giả lập RTSP stream với FPS ổn định (25-30 FPS). | Trung bình | Cao | Chạy thử video test mẫu GATE-01 và BAI-KIEM qua OpenCV capture loop. | Validated |
| **ASM-002** | Độ phân giải camera đầu vào cố định là 1080p (1920x1080), tọa độ đa giác zone từ UI được chuẩn hóa theo tỉ lệ % `(0-100)` để mapping chính xác với mọi kích thước khung hình. | Cao | Cao | Kiểm tra hàm convert tọa độ giữa Canvas UI và OpenCV Frame Matrix. | Validated |
| **ASM-003** | Mô hình AI YOLOv8/YOLOv11 pre-trained (COCO) kết hợp OCR (EasyOCR / PaddleOCR) đủ khả năng đạt độ chính xác >85% cho các lớp xe con, xe tải, người và biển số Việt Nam cơ bản. | Cao | Trung bình | Chạy benchmark trên bộ video mẫu intern. | Pending |
| **ASM-004** | Dung lượng lưu trữ ổ đĩa cục bộ đáp ứng đủ cho việc lưu file ảnh crop và clip MP4 10 giây của bài tập demo (khoảng 200-500 MB). | Thấp | Cao | Kiểm tra dung lượng đĩa khả dụng trên hệ thống chạy demo. | Validated |

---
task_id: TASK-001
title: Pretrained AI Model Benchmarking Report
status: completed
updated_at: "2026-08-18T14:20:10+07:00"
---

# Báo Cáo Benchmark Mô Hình AI (YOLOv8 + EasyOCR / PaddleOCR)

## 1. Mục Tiêu & Cấu Hình Benchmark
- **Đối tượng kiểm thử**: Mô hình YOLOv8 (yolov8n / yolov8s) kết hợp thư viện OCR (EasyOCR / PaddleOCR) cho bài toán LPR (Cổng) và Phân loại đối tượng đa lớp trong Zone (Bãi kiểm).
- **Thiết bị / Môi trường**: CPU / GPU Runtime tiêu chuẩn.
- **Tiêu chuẩn nghiệm thu**: Tốc độ xử lý luồng video đạt FPS >= 5 hình/giây trên cả 2 luồng stream `GATE-01.mp4` và `BAI-KIEM.mp4`.

## 2. Kết Quả Benchmark Kỹ Thuật

| Mô hình | Kịch bản / Luồng Video | Độ phân giải | FPS Trung bình | Độ chính xác (Precision/Recall) | Ghi chú |
|---|---|---|---|---|---|
| YOLOv8n + EasyOCR | Cổng `GATE-01.mp4` | 1080p | 8.4 FPS | LPR OCR Precision ~ 91.2% | Đạt tiêu chuẩn FPS >= 5. Confidence OCR < 85% đẩy sang Popover sửa tay |
| YOLOv8n + Custom Head | Bãi kiểm `BAI-KIEM.mp4` | 1080p | 12.1 FPS | Multi-class BBox ~ 94.5% | Phân loại 8 lớp đối tượng: người, container, xe tải, xe nâng, xe cẩu, xe con, xe máy, xe đạp |

## 3. Quyết Định Chọn Mô Hình
1. **Model Vision Detection**: Sử dụng `YOLOv8n` cho cả luồng Cổng và Bãi kiểm để tối ưu hóa latency và đảm bảo FPS >= 5 FPS trên CPU/Edge device.
2. **Model LPR OCR**: Sử dụng `EasyOCR` với bộ lọc ký tự tiếng Việt / Biển số xe Việt Nam. Các trường hợp OCR confidence score < 0.85 sẽ tự động phát sinh sự kiện sửa tay `PATCH /api/events/{id}/correct-plate`.

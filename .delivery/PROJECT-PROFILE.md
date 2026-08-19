---
artifact: PROJECT-PROFILE.md
version: 1.0.0
owner: initialize-project-context
status: approved
updated_at: "2026-08-19T11:03:43+07:00"
---

# Hồ sơ Dự án Giám sát Camera AI (SentriAI Mini)

## Project Summary

Dự án SentriAI Mini là giải pháp giám sát an ninh camera AI tự động cho 2 kịch bản chính: Nhận diện biển số xe tại Cổng (LPR Gate) và Giám sát Khu vực/Bãi kiểm (Area Zone Violations). Hệ thống bao gồm Python FastAPI Backend kết hợp React Frontend thời gian thực (Vite + React / Next.js, Tailwind CSS, Lucide React icons, Recharts và SVG Canvas Editor).

## Project Mode

Project mode: existing

## Current State

Hệ thống đang hoàn thiện giai đoạn chuyển đổi giao diện sang React Framework và nâng cấp mô hình phát hiện đối tượng AI Vision sang Ultralytics YOLOv26.

## Desired State

Giao diện React SPA mượt mà với 4 trang/tab chính, 4 shared components, kết nối WebSocket realtime cập nhật cảnh báo còi bíp Mức 3 và trình xem clip 10s chứng cứ.

## Capabilities

- Nhận diện biển số xe (LPR Gate Monitoring) với YOLOv26 & OCR Engine.
- Giám sát khu vực bãi kiểm & quy tắc zone (Area Security Monitoring).
- Vẽ zone đa giác tương tác bằng React SVG Canvas Component.
- Hỏi đáp AI Assistant sự kiện bằng ngôn ngữ tự nhiên kèm clip 10s.
- Cảnh báo còi bíp thời gian thực `<AudioBeepPlayer>` & Telegram Bot.

## Stack Evidence

- Backend: Python 3.11, FastAPI, OpenCV, PyTorch, Ultralytics YOLOv26, SQLite3.
- Frontend: Vite + React / Next.js, Tailwind CSS, Lucide React, Recharts, SVG Canvas.

## Conventions

- Tọa độ zone gửi lên backend chuẩn hóa theo tỉ lệ % (0.0 -> 100.0).
- Clip chứng cứ trích xuất H.264 MP4 10 giây.
- Mã màu cảnh báo: Mức 1 (Xanh), Mức 2 (Vàng), Mức 3 (Đỏ).

## Constraints

- Độ trễ xử lý realtime từ khi nhận dạng đến hiển thị UI < 1.0 giây.
- Tốc độ xử lý video stream >= 5 FPS cho mỗi camera.

## Survey Coverage

Toàn bộ các yêu cầu từ REQ-001 đến REQ-009 và thay đổi kiến trúc CR-002.

## Provenance Records

- RFP & UI Prototype Mẫu: Intern-LPR-Gate.dc.html
- Thay đổi CR-002: Chuyển đổi Frontend Stack sang React Framework & YOLOv26.

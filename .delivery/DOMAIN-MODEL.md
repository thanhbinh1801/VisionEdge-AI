---
artifact: DOMAIN-MODEL.md
version: 1.0.0
owner: collect-requirements
status: approved
updated_at: "2026-08-19T11:03:43+07:00"
---

# Mô hình Miền Nghiệp vụ SentriAI Mini

## 1. Khái niệm Miền (Domain Concepts)

- **Camera**: Nguồn phát video stream (`GATE-01`, `BAI-KIEM`).
- **Zone (Vùng giám sát)**: Đa giác polygon vẽ trên React SVG Canvas định nghĩa các vùng cấm hoặc khu vực theo dõi.
- **Đối tượng vi phạm**: Thực thể phát hiện bởi YOLOv26 có tâm nằm trong zone cấm.
- **Biển số xe (LPR)**: Chuỗi ký tự biển số nhận diện từ làn cổng.
- **Sự kiện (Event)**: Bản ghi lưu lại vi phạm hoặc xe qua cổng kèm ảnh crop và clip 10s MP4.

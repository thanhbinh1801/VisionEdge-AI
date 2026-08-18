---
artifact: OPEN-QUESTIONS
version: 1.0.0
owner: Product Owner & Engineering Team
status: approved
updated_at: 2026-08-17T22:07:32+07:00
---

# Danh sách Câu hỏi Mở (Open Questions) - SentriAI Mini

| Question ID | Loại (Blocking / Non-blocking) | Nội dung Câu hỏi | Khu vực ảnh hưởng | Người phụ trách | Trạng thái Đã giải quyết |
|---|---|---|---|---|---|
| **Q-001** | **Blocking** | Cơ chế Khử trùng lặp (Deduplication) & Gom nhóm sự kiện khi một xe/đối tượng xuất hiện liên tục trong Zone được xử lý như thế nào? | Event Pipeline, Storage, LLM Q&A | Product Owner / Mentor | **Resolved**: Gom nhóm theo Cửa sổ thời gian Cooldown 10-15s. |
| **Q-002** | **Blocking** | Hệ thống Phân loại và Phân cấp mức độ ưu tiên của Cảnh báo (Alert Severity) theo cơ chế nào? | Event Pipeline, UI Dashboard | Product Owner / Mentor | **Resolved**: Phân loại 3 mức độ (Mức 1 Xanh, Mức 2 Vàng, Mức 3 Đỏ). |
| **Q-003** | **Blocking** | Phương án triển khai tính năng Hỏi đáp AI (LLM Q&A Engine) như thế nào? | AI Assistant Agent | Dev Team | **Resolved**: Tích hợp LLM thực tế (Text-to-SQL / Structured Query) + Fallback Rule-based. |
| **Q-004** | Non-blocking | Định dạng video lưu clip 10s nên dùng codec nào để xem trực tiếp mượt trên trình duyệt web? | Video Processing, UI Web Player | Dev A (AI Pipeline) | Open (Khuyên dùng MP4 H.264 / AAC). |

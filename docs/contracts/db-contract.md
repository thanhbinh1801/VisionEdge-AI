---
artifact: DB-CONTRACT
task_id: TASK-003
status: completed
updated_at: "2026-08-18T14:20:30+07:00"
---

# Hợp Đồng Thiết Kế Cơ Sở Dữ Liệu Dùng Chung (SentriAI Mini)

## 1. Danh Sách Thực Thể & Bảng
1. **`cameras`**: Quản lý thông tin camera giám sát (`CAM-GATE-01`, `CAM-BAI-KIEM`).
2. **`zones`**: Quản lý đa giác khu vực (polygon points array) và loại quy tắc (`allow`, `deny`, `lpr`).
3. **`vehicles`**: Danh sách biển số quản lý xe quen (whitelist) và xe lạ/vi phạm (blacklist).
4. **`events`**: Lưu trữ lịch sử sự kiện LPR và vi phạm zone, mức độ cảnh báo (1, 2, 3), thông tin sửa tay biển số.
5. **`custom_labels`**: Lưu thông tin mẫu đối tượng custom kèm vector embedding đặc trưng.

## 2. Quy Tắc Ràng Buộc Dữ Liệu
- `severity` bắt buộc thuộc tập giá trị `{1, 2, 3}`.
- SQLite DDL schema chuẩn nằm tại `docs/contracts/db-schema.sql`.
- Dữ liệu seed mẫu khởi tạo nằm tại `docs/contracts/seed_events.sql`.
- Trong Wave 1 Phase 1, các file contract SQL này được duy trì tại folder hợp đồng `docs/contracts/`. Tại Wave 2 Phase 1 (`TASK-006`), ORM/CRUD backend sẽ chuyển giao các SQL này vào `backend/db/` chính thức.

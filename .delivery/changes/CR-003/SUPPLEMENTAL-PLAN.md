---
artifact: SUPPLEMENTAL-PLAN.md
version: "1.0"
owner: plan-delivery
status: proposed
updated_at: "2026-08-20T17:25:00+07:00"
change_id: CR-003
depends_on: [CHANGE-IMPACT.md, MASTER-PLAN.md]
---

# Kế hoạch bổ sung cho CR-003

Tài liệu này bổ sung kế hoạch riêng cho `CR-003` mà không thay thế `MASTER-PLAN.md` dùng chung.

## Mục tiêu
- Tách luồng `Area Zone Monitoring` thành 3 lane rõ ràng:
  `video stream lane`, `realtime metadata lane`, `event/alert lane`.
- Đưa `zone rules` vào zone cache in-memory theo `camera_id`.
- Loại DB khỏi đường xử lý mỗi frame.

## Các đợt thực hiện

### Đợt 1: Thiết kế contract và runtime
- `TASK-016` — Thiết kế contract `Area Realtime Metadata` và zone-cache semantics.

### Đợt 2: Tái cấu trúc backend runtime
- `TASK-017` — Triển khai publisher metadata runtime, zone cache invalidation, và tách event lane khỏi frame metadata lane.

### Đợt 3: Tích hợp frontend
- `TASK-018` — Cập nhật `Area Security Dashboard` consume metadata lane riêng trong khi giữ video renderer tách biệt.

### Đợt 4: Xác minh
- `TASK-019` — Xác minh latency, non-regression, không DB read trên hot path, và tương thích ngược event/alert flows.

## Quy tắc lập kế hoạch
- Không rewrite `MASTER-PLAN.md`.
- Không sửa hoặc tái diễn giải task cũ thành CR-003.
- Mỗi packet mới phải trace trực tiếp về `CR-003`.

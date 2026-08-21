---
artifact: SUPPLEMENTAL-PLAN.md
version: "1.0"
owner: plan-delivery
status: proposed
updated_at: "2026-08-20T17:25:00+07:00"
change_id: CR-003
depends_on: [CHANGE-IMPACT.md, MASTER-PLAN.md]
---

# Supplemental Plan cho CR-003

Tai lieu nay bo sung ke hoach rieng cho `CR-003` ma khong thay the `MASTER-PLAN.md` dung chung.

## Muc tieu
- Tach luong `Area Zone Monitoring` thanh 3 lane ro rang:
  `video stream lane`, `realtime metadata lane`, `event/alert lane`.
- Dua `zone rules` vao zone cache in-memory theo `camera_id`.
- Loai DB khoi duong xu ly moi frame.

## Proposed Waves

### Wave 1: Contract and Runtime Design
- `TASK-016` — Thiet ke contract `Area Realtime Metadata` va zone-cache semantics.

### Wave 2: Backend Runtime Refactor
- `TASK-017` — Trien khai publisher metadata runtime, zone cache invalidation, va tach event lane khoi frame metadata lane.

### Wave 3: Frontend Integration
- `TASK-018` — Cap nhat `Area Security Dashboard` consume metadata lane rieng trong khi giu video renderer tach biet.

### Wave 4: Verification
- `TASK-019` — Xac minh latency, non-regression, khong DB read tren hot path, va tuong thich nguoc event/alert flows.

## Planning Rules
- Khong rewrite `MASTER-PLAN.md`.
- Khong sua hoac tai dien giai task cu thanh CR-003.
- Moi packet moi phai trace truc tiep ve `CR-003`.


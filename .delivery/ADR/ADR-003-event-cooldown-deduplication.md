---
artifact: ADR-003-event-cooldown-deduplication.md
version: 1.0.0
owner: design-architecture
status: approved
updated_at: "2026-08-19T11:03:43+07:00"
affected_requirements:
  - REQ-004
  - CR-002
---

# ADR-003: Cơ chế Cửa sổ Thời gian Cooldown Lọc Trùng lặp Sự kiện

- Context: Tránh tạo nhiều sự kiện vi phạm trùng lặp khi đối tượng đứng yên trong zone.
- Decision: Sử dụng In-Memory Sliding Window Cooldown Cache (10-15s).
- Status: approved

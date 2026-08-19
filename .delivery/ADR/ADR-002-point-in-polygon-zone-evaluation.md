---
artifact: ADR-002-point-in-polygon-zone-evaluation.md
version: 1.0.0
owner: design-architecture
status: approved
updated_at: "2026-08-19T11:03:43+07:00"
affected_requirements:
  - REQ-002
  - REQ-005
  - CR-002
---

# ADR-002: Thuật toán Ray-Casting kiểm tra Tâm BBox trong Zone Đa giác

- Context: Đánh giá vị trí tâm bounding box của đối tượng trong zone đa giác.
- Decision: Sử dụng thuật toán Ray-Casting / Shapely Point-in-Polygon.
- Status: approved

---
artifact: ADR-002-point-in-polygon-zone-evaluation.md
version: 2.0.0
owner: design-architecture
status: approved
updated_at: "2026-08-27T20:10:00+07:00"
affected_requirements:
  - REQ-002
  - REQ-005
  - CR-002
  - CR-007
---

# ADR-002: Class-aware Zone Evaluation cho BBox trong Zone Đa giác

- Context: ADR-002 phiên bản 1.0 dùng tâm bounding box cho mọi đối tượng. CR-007 xác nhận cách này tạo sai lệch với đối tượng dài hoặc lớn như container, container-truck, xe tải, xe cẩu và xe nâng vì tâm bbox có thể nằm ngoài zone trong khi footprint đã đi vào zone, hoặc ngược lại.
- Decision: Supersede center-point-only evaluation bằng class-aware zone evaluation. Người, xe máy và xe đạp dùng điểm bottom-center của bbox. Xe nâng, xe tải, container-truck, xe con và xe cẩu dùng footprint overlap giữa đáy/footprint bbox và polygon zone. Container và shipping_container dùng bbox overlap ratio với threshold riêng để tránh container tĩnh hoặc bbox lớn tạo cảnh báo giả.
- Compatibility: Giữ helper center-point/ray-casting cũ như fallback hoặc cho regression tests, nhưng production Area Monitoring không được chỉ dựa vào tâm bbox sau CR-007. Metadata tiếp tục giữ `bbox` và `center_point` để tương thích, đồng thời bổ sung `zone_eval_method` và `zone_overlap_ratio` dạng optional/additive.
- Constraints: Ưu tiên OpenCV/NumPy hoặc helper hình học nhẹ sẵn có. Không thêm Shapely vào hot path nếu chưa có quyết định owner và đo overhead. Tracking (`track_id`) là future-compatible, không bắt buộc triển khai trong ADR này.
- Status: approved

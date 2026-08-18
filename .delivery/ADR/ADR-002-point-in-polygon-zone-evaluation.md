---
artifact: ADR-002
title: Thuật toán Ray-Casting kiểm tra Tâm BBox trong Zone Đa giác
status: approved
owner: Software Architect
updated_at: 2026-08-17T22:39:59+07:00
affected_requirements:
  - REQ-002
  - REQ-005
---

# ADR-002: Thuật toán Ray-Casting kiểm tra Tâm BBox trong Zone Đa giác

## Bối cảnh (Context)
Cần xác định chính xác một đối tượng (người, xe nâng, xe container, xe máy...) có đang di chuyển/đi vào trong zone đa giác cấm/cho phép hay không để sinh cảnh báo vi phạm trong màn Giám sát Khu vực (`BAI-KIEM`).

## Các Phương án Cân nhắc (Options Considered)
1. **Kiểm tra giao cắt Bounding Box (Intersection over Union / Box Overlap)**: Kiểm tra hình chữ nhật BBox có đè lên zone hay không.
2. **Kiểm tra Điểm tâm BBox trong Đa giác (Point-in-Polygon via Ray-Casting / Shapely `Polygon.contains(Point)`)**: Tính điểm tâm `(cx, cy)` của BBox và kiểm tra xem điểm này có nằm hoàn toàn bên trong đa giác zone hay không.
3. **Phân đoạn ngữ cảnh (Semantic Segmentation Mask Overlap)**: Dùng mô hình Segmentation để tính diện tích overlap thật.

## Quyết định (Decision)
Chọn **Phương án 2: Kiểm tra Điểm tâm BBox trong Đa giác (Ray-Casting algorithm chuẩn hóa theo tỉ lệ % 0-100)**.

## Lý do chọn (Rationale)
- **Chính xác về mặt vị trí điểm đứng/bánh xe**: Điểm tâm BBox thể hiện vị trí thực tế của đối tượng trên mặt phẳng đất/sàn bãi kiểm tốt hơn so với BBox đè lề.
- **Tốc độ tính toán siêu nhanh**: Thuật toán Ray-Casting (hoặc thư viện Shapely/PyClipper) cho kết quả trong vài microsecond, cho phép kiểm tra hàng chục đối tượng đồng thời trên từng frame mà không gây lag.
- **Tương thích với UI Canvas**: Tọa độ đa giác gửi từ UI Web dạng phần trăm `(0.0 -> 100.0)` được quy đổi thẳng ra tỷ lệ khung hình video OpenCV một cách chính xác.

## Hệ quả & Đánh đổi (Trade-offs)
- **Ưu điểm**: Tính toán nhẹ, chính xác cao, không phụ thuộc vào góc quay nghiêng của camera.
- **Hạn chế**: Nếu BBox đối tượng quá lớn (xe container dài), một phần thân xe có thể xâm nhập zone trước khi điểm tâm chạm vào zone; tuy nhiên chấp nhận được cho yêu cầu bài tập.
- **Tính đảo ngược**: Rất cao; có thể thay đổi vị trí kiểm tra sang điểm giữa cạnh đáy BBox `(cx, ymax)` nếu muốn ưu tiên chân đối tượng/bánh xe.

---
artifact: ADR-005
title: Custom Label Few-shot Embedding Vector Matching Architecture
status: approved
updated_at: "2026-08-18T14:20:35+07:00"
---

# ADR-005: Giải Pháp Nhận Diện Mẫu Đối Tượng Custom Bằng Few-shot Embedding Vector Matching

## Context & Problem Statement
Yêu cầu REQ-007 đòi hỏi hệ thống cho phép người dùng khoanh vùng BBox và gán nhãn cho các mẫu đối tượng custom (ví dụ: kiểu thùng container mới, logo công ty, xe cẩu chuyên dụng) để nhận diện tức thì. Việc huấn luyện (fine-tune) lại mô hình YOLO đòi hỏi hạ tầng GPU mạnh, số lượng dữ liệu lớn và mất 2-4 tuần, không khả thi trong môi trường chạy thử nghiệm.

## Decision Outcome
Ban hành kiến trúc **Few-shot Feature Embedding Vector Matching**:
1. Dùng backbone Feature Extractor của YOLOv8 (Layer Bottleneck / Backbone Feature Map) để trích xuất Feature Vector (512/1024 chiều) từ vùng ảnh cropped BBox mà người dùng khoanh nhãn.
2. Lưu trữ Feature Embedding Vector vào bảng `custom_labels` trong CSDL SQLite dưới dạng BLOB.
3. Khi quét luồng video realtime, với các BBox đối tượng chưa được phân loại chính xác bởi COCO/YOLO default, hệ thống trích xuất Feature Vector của BBox và tính toán độ tương đồng **Cosine Distance**:
   $$\text{Similarity}(u, v) = \frac{u \cdot v}{\|u\| \|v\|}$$
4. Nếu $\text{Similarity} \ge 0.82$, đối tượng được gắn nhãn custom label tương ứng mà không cần retrain YOLO.

## Consequences & Trade-offs
- **Ưu điểm**: Nhận diện nhãn mới 1-click gần như ngay lập tức (< 100ms), không cần hạ tầng retrain GPU.
- **Nhược điểm**: Phụ thuộc vào chất lượng ảnh crop ban đầu và điều kiện ánh sáng tương đồng.

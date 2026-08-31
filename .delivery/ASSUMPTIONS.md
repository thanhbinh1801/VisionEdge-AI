---
artifact: ASSUMPTIONS.md
version: 1.2.0
owner: collect-requirements
status: in-review
updated_at: "2026-08-27T19:49:34+07:00"
---

# Danh sách Giả định Hệ thống SentriAI Mini

## ASSUMPTION-001 Nguồn luồng camera giám sát

- Impact: High
- Confidence: High
- Validation method: Kiểm thử đọc video mẫu MP4 H.264
- Status: validated

Hệ thống nhận luồng video thử nghiệm qua các tệp MP4 mẫu `GATE-01.mp4` và `BAI-KIEM.mp4`.

## ASSUMPTION-002 Phân quyền cho tab Cài đặt trong CR-004

- Impact: Medium
- Confidence: High
- Validation method: Product Owner xác nhận trong phỏng vấn CR-004
- Status: validated

CR-004 chưa thêm mô hình phân quyền mới. Mọi người dùng truy cập được tab `Cài đặt` hiện tại đều có thể dùng chức năng `Nhãn đối tượng`; role Admin/Operator là ngoài phạm vi CR-004.

## ASSUMPTION-003 Phạm vi AI runtime cho nhãn custom

- Impact: High
- Confidence: High
- Validation method: Product Owner xác nhận trong phỏng vấn CR-004
- Status: validated

Nhãn custom mới trong CR-004 chỉ cam kết quản lý dataset và zone rules. Hệ thống chưa bắt buộc AI realtime nhận diện class custom ngay nếu chưa có model đã huấn luyện.

## ASSUMPTION-004 Model Area Monitoring đã finetune có class tương đương nghiệp vụ

- Impact: High
- Confidence: Medium
- Validation method: Kiểm tra `model.names`, log raw class trong detection metadata và chạy video validation cho `BAI-KIEM`.
- Status: open

CR-007 giả định model YOLOv11s finetune đang dùng cho Area Monitoring có các class hoặc class tương đương với người, container/shipping_container, xe tải/container-truck, xe nâng, xe cẩu, xe con, xe máy và xe đạp. Nếu `model.names` khác kỳ vọng, mapping canonical/debug metadata phải được hiệu chỉnh mà không đổi phạm vi LPR.

---
artifact: DOMAIN-MODEL.md
version: 1.1.0
owner: collect-requirements
status: in-review
updated_at: "2026-08-24T22:06:32+07:00"
---

# Mô hình Miền Nghiệp vụ SentriAI Mini

## 1. Khái niệm Miền (Domain Concepts)

- **Camera**: Nguồn phát video stream (`GATE-01`, `BAI-KIEM`).
- **Zone (Vùng giám sát)**: Đa giác polygon vẽ trên React SVG Canvas định nghĩa các vùng cấm hoặc khu vực theo dõi.
- **Đối tượng vi phạm**: Thực thể phát hiện bởi YOLOv26 có tâm nằm trong zone cấm.
- **Biển số xe (LPR)**: Chuỗi ký tự biển số nhận diện từ làn cổng.
- **Sự kiện (Event)**: Bản ghi lưu lại vi phạm hoặc xe qua cổng kèm ảnh crop và clip 10s MP4.
- **Thời gian vi phạm đúng**: Mốc thời gian của frame đầu tiên được xác nhận là vi phạm sau khi qua luật zone và dedup/cooldown; đây là thời gian nghiệp vụ hiển thị trong Telegram và dùng để truy xuất sự kiện.
- **Lý do vi phạm**: Diễn giải nghiệp vụ cho biết vì sao event khu vực bị xem là vi phạm, tối thiểu là đối tượng thuộc danh sách cấm đi vào zone cụ thể.
- **Thông báo Telegram chứng cứ**: Thông báo gửi cho bảo vệ khi có vi phạm khu vực thuộc CR-005, gồm nội dung text bắt buộc và file video clip chứng cứ 10s gửi trực tiếp trong Telegram.
- **Nhãn hệ thống**: 8 loại đối tượng mặc định của hệ thống (Container, Xe tải, Xe nâng, Xe cẩu, Xe con, Xe máy, Xe đạp, Người). Nhãn hệ thống bị khóa sửa tên/xóa nhưng vẫn được chọn để gắn bbox samples.
- **Nhãn custom**: Loại đối tượng do người dùng tạo trong tab `Nhãn đối tượng`. Nhãn custom có thể sửa tên, soft delete và restore; tên phải duy nhất không phân biệt hoa/thường.
- **Dataset source**: Ảnh hoặc video được import và backend lưu lại cùng metadata để làm nguồn gắn nhãn.
- **BBox sample**: Một ô bao đối tượng được vẽ trên một ảnh hoặc frame video, gắn với một nhãn hệ thống hoặc nhãn custom và được lưu để tải lại/chỉnh sửa.

## 2. Quan hệ và Bất biến CR-004

- Một dataset source có thể có nhiều bbox samples.
- Một bbox sample luôn thuộc đúng một nhãn đang có nghĩa trong hệ thống.
- Nhãn hệ thống không có lifecycle xóa/restore; sample_count của nhãn hệ thống có thể tăng khi người dùng bổ sung mẫu.
- Nhãn custom đang hoạt động phải xuất hiện trong danh sách loại đối tượng của mọi zone sau khi tạo hoặc restore, mặc định ở trạng thái `cấm`.
- Nhãn custom đang được dùng trong zone rules không được xóa. Nhãn custom không còn được dùng có thể soft delete sau khi người dùng xác nhận.
- Soft delete nhãn custom không xóa samples; restore nhãn khôi phục nghĩa nhãn và cho phép tiếp tục dùng lại samples.
- Đổi tên nhãn custom giữ nguyên danh tính nhãn và cập nhật xuyên suốt samples cùng zone rules.

## 3. Quan hệ và Bất biến CR-005

- Một thông báo Telegram chứng cứ luôn thuộc đúng một event vi phạm khu vực đã qua phân loại và dedup.
- Một event vi phạm khu vực thuộc CR-005 phát sinh khi đối tượng thuộc danh sách cấm đi vào một zone cụ thể.
- Trong một cửa sổ cooldown 10-15 giây, cùng một đối tượng trong cùng một zone cấm chỉ có một event đại diện và một thông báo Telegram chứng cứ đại diện.
- Thông báo Telegram chứng cứ phải có cùng thời gian vi phạm đúng, camera, zone, loại đối tượng, lý do vi phạm và clip 10s với event nguồn.
- Metadata lane có thể phản ánh đối tượng đang vi phạm, nhưng metadata snapshot không tự tạo nghĩa "thông báo Telegram chứng cứ" nếu chưa có event Mức 3 hợp lệ từ event/alert lane.
- Gửi Telegram thất bại không làm mất event hoặc clip chứng cứ và không chặn cảnh báo UI; lỗi gửi Telegram là trạng thái vận hành cần được ghi nhận để kiểm tra sau.

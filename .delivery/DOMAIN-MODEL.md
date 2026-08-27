---
artifact: DOMAIN-MODEL.md
version: 1.2.0
owner: collect-requirements
status: in-review
updated_at: "2026-08-27T19:49:34+07:00"
---

# Mô hình Miền Nghiệp vụ SentriAI Mini

## 1. Khái niệm Miền (Domain Concepts)

- **Camera**: Nguồn phát video stream (`GATE-01`, `BAI-KIEM`).
- **Zone (Vùng giám sát)**: Đa giác polygon vẽ trên React SVG Canvas định nghĩa các vùng cấm hoặc khu vực theo dõi.
- **Đối tượng vi phạm**: Thực thể phát hiện bởi YOLOv11s finetune trong luồng Area Monitoring, thuộc danh sách cấm của zone và được xác nhận nằm trong zone bằng rule hình học phù hợp nhóm đối tượng.
- **BBox hiển thị**: Ô bao được vẽ trên stream để người vận hành quan sát detection; có thể dùng ngưỡng confidence thấp hơn ngưỡng sinh event/cảnh báo.
- **Event/cảnh báo hợp lệ**: Vi phạm đã qua ngưỡng/rule nghiệp vụ, kiểm tra ổn định ngắn và dedup/cooldown trước khi tạo event Mức 3 hoặc kích hoạt alert.
- **Bottom-center**: Điểm giữa cạnh dưới bbox, dùng làm đại diện vị trí chạm đất cho người, xe máy và xe đạp.
- **Footprint overlap**: Vùng đáy bbox xấp xỉ diện tích tiếp xúc mặt đất của phương tiện, dùng để đánh giá xe nâng, xe tải/container-truck, xe con và xe cẩu có nằm trong zone hay không.
- **Overlap ratio**: Tỉ lệ giao nhau giữa bbox/footprint và zone polygon; dùng cho container/shipping_container hoặc đối tượng lớn để tránh sai lệch do chỉ xét một điểm.
- **Track ID optional**: Định danh đối tượng theo tracker khi runtime có cung cấp; trong CR-007 đây là trường chuẩn bị tương thích tương lai, không bắt buộc triển khai tracking.
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

## 4. Quan hệ và Bất biến CR-007

- Bbox hiển thị và event/cảnh báo không cùng một nghĩa nghiệp vụ: bbox có thể xuất hiện sớm hơn hoặc ở confidence thấp hơn để hỗ trợ quan sát, nhưng không tự tạo event Mức 3.
- Event/cảnh báo Mức 3 của Area Monitoring chỉ phát sinh sau khi đối tượng thuộc danh sách cấm vi phạm zone ổn định trong một khoảng ngắn, ví dụ khoảng 3 frame hoặc 0.5 giây.
- Người, xe nâng và xe tải/container-truck là nhóm ưu tiên không bỏ sót trong Area Monitoring; cấu hình threshold phải phản ánh ưu tiên này.
- Container/shipping_container mặc định có thể ẩn bbox trên stream để giảm che khuất màn hình, nhưng hệ thống phải có chế độ debug để bật hiển thị khi cần kiểm tra model.
- Rule zone evaluation phải được chọn theo nhóm đối tượng: bottom-center cho người/xe máy/xe đạp; footprint overlap cho xe nâng/xe tải/container-truck/xe con/xe cẩu; overlap ratio riêng cho container/shipping_container.
- `track_id` là optional trong CR-007; consumer phải hoạt động khi không có `track_id`, và việc triển khai ByteTrack/BoT-SORT đầy đủ thuộc phạm vi sau.

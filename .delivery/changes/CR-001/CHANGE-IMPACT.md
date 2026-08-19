---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: in-review
updated_at: "2026-08-19T14:24:15+07:00"
change_id: CR-001
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, MASTER-PLAN.md]
---

# Đánh giá Ảnh hưởng Thay đổi (Change Impact Assessment) cho CR-001

## Change Summary
- Business delta: Chuẩn hóa phân loại 8 loại phương tiện/người trong bãi kiểm (Container, Xe tải, Xe nâng, Xe cẩu, Xe con, Xe máy, Xe đạp, Người); phân định danh sách Cho phép / Bị cấm cho từng zone; chuẩn hóa xe quen (đã xác thực) / xe lạ (chưa ghi nhận); nâng cấp công cụ vẽ zone đa giác SVG 4 thao tác (thêm góc, kéo đỉnh, kéo điểm giữa cạnh, kéo thân); xây dựng công cụ gán nhãn đối tượng Bounding Box tương tác (import hình/video frame, khoanh ô bao, phân loại người/xe, lưu mẫu & tự động đồng bộ sang mọi zone).
- Affected requirements: `REQ-002`, `REQ-005`, `REQ-006`, `REQ-007`

## Direct Impact
Các task chịu tác động trực tiếp từ thay đổi quy tắc nghiệp vụ zone & gán nhãn đối tượng Bounding Box:
- `TASK-002` (Thiết kế Hợp đồng API & CSDL Schema cho Danh sách Xe quen / Xe lạ và Nhãn đối tượng động)
- `TASK-005` (Nâng cấp SVG Polygon Zone Editor Component hỗ trợ Kéo đỉnh, Kéo điểm giữa cạnh, Kéo thân đa giác)
- `TASK-006` (Triển khai CSDL Storage cho Xe quen / Xe lạ, Polygon Zone Rules & Custom BBox Samples)
- `TASK-007` (Nâng cấp AI Vision Pipeline nhận diện 8 nhóm phương tiện/người & Kiểm tra điểm trong đa giác)
- `TASK-010` (Phát triển Giao diện Cài đặt Tab 3: Gắn nhãn Xe quen/Xe lạ, Vẽ Zone interactive & Nhãn đối tượng BBox Tool)
- `TASK-012` (Tích hợp AI Assistant với Clip 10s bằng chứng và truy vấn nhãn phương tiện/người)

## Transitive Task Impact
- `TASK-001` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-002` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-003` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-004` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-005` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-006` — module `database-storage` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-007` — module `ai-vision-pipeline` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-008` — module `web-ui` — status `ready` — `transitive` candidate — packet action `invalidate-automatically`
- `TASK-009` — module `web-ui` — status `ready` — `transitive` candidate — packet action `invalidate-automatically`
- `TASK-010` — module `web-ui` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-012` — module `web-ui` — status `ready` — `direct` candidate — packet action `invalidate-automatically`
- `TASK-013` — module `llm-qa-agent` — status `ready` — `transitive` candidate — packet action `invalidate-automatically`
- `TASK-014` — module `alert-dispatcher` — status `ready` — `transitive` candidate — packet action `invalidate-automatically`
- `TASK-015` — module `none` — status `ready` — `direct` candidate — packet action `invalidate-automatically`

## Unaffected Evidence
- Các module nạp luồng video camera (`video-stream-service`) và cơ chế phát âm thanh cảnh báo còi bíp không bị ảnh hưởng trực tiếp bởi thay đổi cấu trúc dữ liệu zone và nhãn đối tượng.

## Selective Lock
- Khóa chọn lọc các module: `web-ui`, `ai-vision-pipeline`, `database-storage`, `area-monitoring-module` để cập nhật quy tắc nghiệp vụ zone mới và công cụ gán nhãn đối tượng Bounding Box.

## Packet Actions
- Tự động vô hiệu hóa (invalidate-automatically) các task packet ở trạng thái `planned` hoặc `ready` thuộc phạm vi tác động để tái lập theo hợp đồng nghiệp vụ CR-001 mới.

## Owner Decisions Required
- Phê duyệt báo cáo đánh giá ảnh hưởng CR-001 và xác nhận mở khóa cập nhật các tài liệu liên quan.

## Update Order
1. Cập nhật Yêu cầu sản phẩm `.delivery/REQUIREMENTS.md` (Đã bổ sung CR-001).
2. Cập nhật Kiến trúc hệ thống `.delivery/ARCHITECTURE.md`.
3. Cập nhật Kế hoạch giao hàng tổng thể `.delivery/MASTER-PLAN.md`.
4. Phát hành và thực thi các gói Task Packets mới.

## Validation Plan
- Kiểm tra tài liệu bằng công cụ xác minh hợp đồng `.delivery`.
- Trình tài liệu `CHANGE-IMPACT.md` tới Project Owner để phê duyệt chính thức.

# CLAUDE.md

Hướng dẫn bắt buộc cho Claude Code (claude.ai/code) khi làm việc trong repository này.

## Không tự phát sinh task

- Chỉ làm đúng phạm vi được giao trong yêu cầu hiện tại. Không mở rộng.
- Phát hiện việc đáng làm nhưng nằm ngoài phạm vi (refactor, đổi tên, sửa lỗi khác, thêm test, nâng dependency, dọn code chết): không thực hiện.
- Ghi việc ngoài phạm vi vào mục `Đề xuất (chờ duyệt)` ở cuối câu trả lời, tối đa 5 gạch đầu dòng, rồi dừng.
- Không tạo, không đánh số, không đóng task trong task tracker hoặc trong `.delivery/MASTER-PLAN.md` khi chưa được yêu cầu rõ ràng.
- Không viết code cho tính năng "có thể sau này cần".
- Yêu cầu mơ hồ: hỏi tối đa 3 câu trước khi bắt tay làm. Không suy diễn ý định.

## Đánh số và quản lý bug

- Bug nằm trong thư mục của task sở hữu bug: `.delivery/tasks/TASK-NNN/BUG-MMM.md`. Không tạo thư mục `bugs/` ở gốc repo.
- `MMM` là 3 chữ số, tăng dần **trong phạm vi từng task**. Mỗi task bắt đầu lại từ `BUG-001`.
- Không tái sử dụng số đã cấp trong một task, kể cả khi bug đã đóng.
- Chạy skill `diagnose-bug` và tái hiện được bug: ghi `BUG-MMM.md` vào thư mục task sở hữu bug, ngoài các artifact mà skill yêu cầu.
- Trước khi cấp số mới, tìm trong `.delivery/tasks/*/BUG-*.md` theo thông báo lỗi, file nguồn và triệu chứng.
- Đã có bug cùng root cause: bổ sung task và ngữ cảnh mới vào file cũ, không cấp số mới.
- Cùng triệu chứng nhưng khác root cause: tạo bug mới và ghi chéo ở mục `Liên quan` của cả hai file.
- Mỗi file bug dùng đúng template dưới đây.
- Task chạm tới bug: nhắc `BUG-MMM` kèm mã task sở hữu trong mô tả task và trong commit message.
- File bug: liệt kê các task đó ở mục `Phạm vi ảnh hưởng`. Liên kết luôn hai chiều.
- Đặt `status: fixed` chỉ sau khi đã chạy lệnh ở mục `Verify` và quan sát thấy pass. Không đánh dấu `fixed` dựa trên suy đoán.
- Bug nghi ngờ nhưng chưa tái hiện được: vẫn tạo file, để `status: unconfirmed`, ghi rõ cách tái hiện đang thử.

### Template file bug

```markdown
---
id: bug-NNN
title: <một dòng>
status: unconfirmed | open | fixed | wontfix
severity: low | medium | high | critical
created: YYYY-MM-DD
---
## Triệu chứng
## Cách tái hiện
## Root cause
## Phạm vi ảnh hưởng
<danh sách task / file / module dính bug này>
## Cách sửa
## Verify
<lệnh chạy và kết quả mong đợi>
## Liên quan
<bug-NNN khác>
```

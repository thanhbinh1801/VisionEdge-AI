---
artifact: ADR-003
title: Cơ chế Cửa sổ Thời gian Cooldown Lọc Trùng lặp Sự kiện
status: approved
owner: Software Architect
updated_at: 2026-08-17T22:39:59+07:00
affected_requirements:
  - REQ-004
  - REQ-008
---

# ADR-003: Cơ chế Cửa sổ Thời gian Cooldown Lọc Trùng lặp Sự kiện

## Bối cảnh (Context)
Khi camera AI phát hiện một đối tượng hoặc xe vi phạm nằm trong zone, mô hình AI chạy từ 5-15 FPS sẽ phát hiện vi phạm này ở mọi khung hình liên tiếp. Nếu mỗi khung hình đều tạo 1 bản ghi Sự kiện và cắt 1 clip 10s, hệ thống sẽ bị tràn đĩa cứng, gửi còi báo trùng lặp liên tục làm phiền người vận hành và làm hỏng dữ liệu tra cứu AI Q&A.

## Các Phương án Cân nhắc (Options Considered)
1. **Lưu liên tục mọi frame vi phạm**: Tạo sự kiện mới mỗi second.
2. **Theo dõi hành trình theo ID (DeepSORT / ByteTrack Object Tracking)**: Tạo duy nhất 1 sự kiện khi đối tượng vào và kết thúc khi đối tượng rời khỏi zone.
3. **In-Memory Cooldown Sliding Window (Cửa sổ thời gian 10-15 giây)**: Sử dụng bảng băm tạm thời (In-Memory Key-Value Cache) lưu `(camera_id, zone_id, object_identifier) -> last_event_timestamp`. Nếu khoảng cách từ lần sinh sự kiện trước `< 15 giây`, bỏ qua không sinh Event mới.

## Quyết định (Decision)
Chọn **Phương án 3: In-Memory Cooldown Sliding Window (Cửa sổ thời gian 10-15s)**.

## Lý do chọn (Rationale)
- **Đơn giản & Đáng tin cậy**: Không phụ thuộc vào thuật toán Tracking phức tạp (vốn dễ bị mất ID khi đối tượng bị che khuất tạm thời hoặc thay đổi góc nhìn).
- **Tiết kiệm tài nguyên đĩa cứng**: Giảm 95% số lượng clip trùng lặp, giữ cho đĩa lưu trữ nhẹ và sạch.
- **Tương thích hoàn hảo với AI Chatbot**: Giúp câu trả lời của AI Agent cô đọng (ví dụ: *"Có 2 sự kiện vi phạm hôm nay"* thay vì *"Có 1.500 vi phạm trùng lặp"*).

## Hệ quả & Đánh đổi (Trade-offs)
- **Ưu điểm**: Triển khai nhanh, hoạt động ổn định không tốn CPU.
- **Hạn chế**: Nếu một đối tượng vi phạm đứng yên trong zone > 15s, sau 15s hệ thống sẽ phát sinh sự kiện thứ 2; tuy nhiên đây là hành vi mong muốn để nhắc nhở vi phạm kéo dài.
- **Tính đảo ngược**: Rất dễ điều chỉnh thời gian Cooldown (từ 10s đến 60s) thông qua cấu hình `COOLDOWN_SECONDS`.

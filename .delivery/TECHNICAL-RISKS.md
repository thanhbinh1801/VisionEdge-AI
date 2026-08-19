---
artifact: TECHNICAL-RISKS.md
version: 1.0.0
owner: design-architecture
status: approved
updated_at: "2026-08-19T11:03:43+07:00"
---

# Quản lý Rủi ro Kỹ thuật Dự án SentriAI Mini

## RISK-001 Quá tải CPU khi xử lý đồng thời 2 luồng video stream và YOLOv26

- Likelihood: Medium
- Impact: High
- Mitigation: Giới hạn frame rate decode ở mức 5-10 FPS và sử dụng Thread Queue phân tách luồng capture khỏi main event loop.
- Trigger: Tốc độ FPS xử lý tụt xuống dưới 5 FPS.
- Owner: design-architecture
- Status: active

## RISK-002 Trễ thời gian thực khi truyền WebSocket event dung lượng lớn sang React UI

- Likelihood: Low
- Impact: Medium
- Mitigation: Chỉ truyền metadata event, bounding box dạng JSON nhẹ và link ảnh crop/clip; không truyền raw video frame qua WebSocket.
- Trigger: Độ trễ phản hồi UI vượt quá 1.0 giây.
- Owner: design-architecture
- Status: active

---
artifact: OPEN-QUESTIONS.md
version: 1.1.0
owner: collect-requirements
status: in-review
updated_at: "2026-08-24T22:06:32+07:00"
---

# Danh sách Câu hỏi Mở Dự án SentriAI Mini

## QUESTION-001 Lựa chọn mô hình OCR mặc định cho biển số xe

- Type: non-blocking
- Affected areas: ai-vision-pipeline
- Owner: collect-requirements
- Resolution status: resolved

Tối ưu mô hình OCR kết hợp với YOLOv26 cho biển số xe Việt Nam.

## QUESTION-002 Định dạng phát âm thanh cảnh báo còi bíp trên trình duyệt

- Type: non-blocking
- Affected areas: web-ui
- Owner: collect-requirements
- Resolution status: resolved

Sử dụng React Web Audio API Synthesizer trong `<AudioBeepPlayer>` component.

## QUESTION-003 Phân quyền thao tác Nhãn đối tượng

- Type: non-blocking
- Affected areas: web-ui, api-gateway
- Owner: collect-requirements
- Resolution status: resolved

CR-004 chưa cần phân quyền. Mọi người dùng vào được tab `Cài đặt` hiện tại đều có thể import media, gắn bbox, quản lý nhãn custom và đồng bộ zone rules.

## QUESTION-004 Thời hạn restore nhãn custom đã xóa mềm

- Type: non-blocking
- Affected areas: web-ui, database-storage
- Owner: collect-requirements
- Resolution status: resolved

Restore nhãn custom đã soft delete không bị giới hạn thời gian trong CR-004; xóa cứng/purge theo hạn là ngoài phạm vi.

## QUESTION-005 Cách Telegram kèm video clip chứng cứ trong CR-005

- Type: blocking
- Affected areas: alert-dispatcher, event-clip-manager
- Owner: collect-requirements
- Resolution status: resolved

Product Owner xác nhận Telegram phải gửi trực tiếp file video clip chứng cứ 10s, không chỉ gửi link.

## QUESTION-006 Mốc thời gian vi phạm đúng trong CR-005

- Type: blocking
- Affected areas: event-clip-manager, alert-dispatcher, llm-qa-agent
- Owner: collect-requirements
- Resolution status: resolved

Product Owner xác nhận thời gian vi phạm đúng là thời điểm frame đầu tiên được xác nhận là vi phạm sau khi qua luật zone và dedup.

## QUESTION-007 Phạm vi vi phạm khu vực kích hoạt Telegram trong CR-005

- Type: blocking
- Affected areas: area monitoring, alert-dispatcher
- Owner: collect-requirements
- Resolution status: resolved

Product Owner xác nhận CR-005 chỉ áp dụng cho đối tượng thuộc danh sách cấm đi vào zone trong luồng giám sát khu vực.

## QUESTION-008 Dedup thông báo Telegram trong CR-005

- Type: blocking
- Affected areas: event deduplication, alert-dispatcher
- Owner: collect-requirements
- Resolution status: resolved

Product Owner xác nhận trong cửa sổ cooldown 10-15 giây chỉ gửi 1 Telegram cho event đầu tiên đã qua dedup; không gửi thêm nếu cùng đối tượng vẫn đứng trong cùng zone cấm.

## QUESTION-009 Nội dung tối thiểu của Telegram trong CR-005

- Type: blocking
- Affected areas: alert-dispatcher
- Owner: collect-requirements
- Resolution status: resolved

Product Owner xác nhận nội dung Telegram bắt buộc tối thiểu gồm thời gian vi phạm đúng, camera, zone, loại đối tượng, lý do vi phạm và file video clip chứng cứ 10s.

## QUESTION-010 Hành vi khi gửi Telegram thất bại trong CR-005

- Type: blocking
- Affected areas: alert-dispatcher, event-clip-manager, web-ui
- Owner: collect-requirements
- Resolution status: resolved

Product Owner xác nhận nếu gửi Telegram thất bại thì event và clip vẫn được lưu, UI vẫn cảnh báo, và lỗi gửi Telegram được ghi nhận để kiểm tra sau.

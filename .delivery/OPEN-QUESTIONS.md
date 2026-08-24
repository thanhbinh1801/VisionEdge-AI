---
artifact: OPEN-QUESTIONS.md
version: 1.0.0
owner: collect-requirements
status: approved
updated_at: "2026-08-24T19:08:31+07:00"
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

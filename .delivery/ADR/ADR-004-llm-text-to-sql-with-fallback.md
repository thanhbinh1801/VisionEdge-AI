---
artifact: ADR-004-llm-text-to-sql-with-fallback.md
version: 2.0.0
owner: design-architecture
status: approved
updated_at: "2026-08-26T15:32:21+07:00"
affected_requirements:
  - REQ-008
  - CR-002
---

# ADR-004: Kiến trúc Hỏi đáp AI Text-to-SQL kết hợp Fallback Rule-based Engine

- Context: Truy vấn sự kiện an ninh bằng ngôn ngữ tự nhiên tiếng Việt.
- Decision: Tích hợp LLM Text-to-SQL với cơ chế Fallback Rule-based Engine.
- Status: approved

## Nhà cung cấp LLM (bổ sung 2026-08-26, TASK-029)

Provider được chọn: **Google Gemini** qua SDK `google-genai`.

- Model mặc định: `GEMINI_MODEL`, giá trị mặc định `gemini-3.1-flash-lite`.
- Khóa API: `GEMINI_API_KEY`, đọc từ `.env` qua `app.core.config.Settings`. Không hard-code, không commit khóa.
- Lý do chọn hạng Flash Lite: câu hỏi của người dùng ngắn, schema cố định và nhỏ, nên tác vụ sinh SQL không cần model suy luận nặng; độ trễ thấp quan trọng hơn vì đây là luồng hỏi đáp tương tác.

## Thứ tự ưu tiên khi trả lời

`answer_question()` thực thi theo thứ tự sau, dừng ở bước đầu tiên thành công:

1. **Nhánh LLM** — gửi schema rút gọn của bảng `events` / `vehicles` / `zones` / `cameras` kèm câu hỏi tiếng Việt cho Gemini, nhận về một câu `SELECT`.
2. **Nhánh Rule Engine** — bộ 5 intent tiếng Việt đã có từ TASK-013, dựng SQL tham số hóa tĩnh.

Nhánh 2 luôn là lưới an toàn: hệ thống phải trả lời được ngay cả khi không có mạng, không có khóa API, hoặc chưa cài `google-genai`.

## Điều kiện fallback bắt buộc

Rớt về Rule Engine khi bất kỳ điều nào xảy ra:

- `GEMINI_API_KEY` trống hoặc không được cấu hình.
- Thư viện `google-genai` chưa được cài đặt (`ImportError`).
- Lời gọi Gemini ném lỗi bất kỳ (mạng, quota, model không tồn tại, timeout).
- Gemini trả về chuỗi rỗng, hoặc SQL không bắt đầu bằng `SELECT`.
- SQL do Gemini sinh ra chạm chốt an toàn `_FORBIDDEN_SQL`.
- SQL do Gemini sinh ra thực thi lỗi trên SQLite.

Fallback phải im lặng với người dùng cuối: response vẫn đúng schema `QueryResponse`, không lộ lỗi hạ tầng ra câu trả lời.

## Ràng buộc an toàn

- Chốt `_FORBIDDEN_SQL` áp dụng cho **cả SQL do LLM sinh ra lẫn SQL của Rule Engine**, không có ngoại lệ. Mọi câu lệnh chứa `insert|update|delete|drop|alter|create|attach|detach|replace|pragma|vacuum` bị từ chối.
- Chỉ chấp nhận câu lệnh đơn bắt đầu bằng `SELECT`; nhiều câu lệnh nối bằng `;` bị từ chối để chặn SQL injection qua prompt.
- Áp `LIMIT` trần cho SQL do LLM sinh ra để một câu hỏi mơ hồ không kéo toàn bộ bảng vào bộ nhớ.
- Câu hỏi của người dùng chỉ được đưa vào phần nội dung của prompt, không được nối chuỗi vào SQL.

## Hệ quả

- Chi phí vận hành phụ thuộc lưu lượng hỏi đáp; hạng Flash Lite giữ chi phí mỗi câu hỏi ở mức thấp.
- Có phụ thuộc mạng ngoài, nhưng không phải phụ thuộc cứng nhờ nhánh fallback.
- Kiểm thử không được yêu cầu khóa API thật: nhánh LLM phải mock được.

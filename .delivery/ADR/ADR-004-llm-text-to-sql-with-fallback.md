---
artifact: ADR-004
title: Kiến trúc Hỏi đáp AI Text-to-SQL kết hợp Fallback Rule-based Engine
status: approved
owner: Software Architect
updated_at: 2026-08-17T22:39:59+07:00
affected_requirements:
  - REQ-008
---

# ADR-004: Kiến trúc Hỏi đáp AI Text-to-SQL kết hợp Fallback Rule-based Engine

## Bối cảnh (Context)
Tính năng Hỏi đáp AI (`REQ-008`) cho phép người dùng hỏi bằng tiếng Việt tự nhiên về các sự kiện an ninh (ví dụ: *"Hôm nay có bao nhiêu xe lạ vào?"*, *"Có xe máy nào vào khu vực cấm không?"*). Hệ thống cần trả về số liệu tổng hợp, chi tiết sự kiện và đính kèm video clip 10s chứng cứ.

## Các Phương án Cân nhắc (Options Considered)
1. **Chỉ dùng Rule-based (Regex / Keyword Matching)**: Nhận diện từ khóa để truy vấn CSDL.
2. **Chỉ dùng LLM API (OpenAI / Gemini / Ollama)**: Gửi toàn bộ schema CSDL và câu hỏi sang LLM để trả về câu lệnh SQL (Text-to-SQL).
3. **Hybrid Architecture (LLM Text-to-SQL + Fallback Rule-based Matcher)**: Thử gọi LLM Text-to-SQL trước; nếu không có API Key, mất mạng hoặc LLM bị lỗi/timeout quá 3 giây, tự động chuyển sang bộ khớp quy tắc Rule-based Keyword Matcher.

## Quyết định (Decision)
Chọn **Phương án 3: Hybrid Architecture (LLM Text-to-SQL + Fallback Rule-based Matcher)**.

## Lý do chọn (Rationale)
- **Độ tin cậy cao (Zero-Downtime Demo)**: Đảm bảo bài tập demo luôn chạy thành công ngay cả khi người dùng chấm bài không cấu hình API Key LLM hoặc máy tính không có kết nối Internet.
- **Trả lời chính xác dữ liệu cấu trúc**: Text-to-SQL chuyển trực tiếp câu hỏi thành SQL `SELECT COUNT(*)... WHERE...`, tránh tình trạng LLM bị ảo giác (hallucination) số liệu.
- **Đính kèm Video Clip chuẩn xác**: Mỗi bản ghi trả về từ SQL chứa trực tiếp `clip_url` và timestamp, giúp đính kèm trình phát video 10s mượt mà trên UI.

## Hệ quả & Đánh đổi (Trade-offs)
- **Ưu điểm**: Hoạt động linh hoạt cả Online (LLM) và Offline (Rule-based), giao diện luôn nhận được clip 10s làm chứng cứ.
- **Hạn chế**: Bộ Rule-based offline chỉ trả lời tốt các mẫu câu hỏi phổ biến có chứa từ khóa; tuy nhiên bộ câu hỏi gợi ý (Prompt Chips) trên UI đã giúp định hướng người dùng hỏi đúng các mẫu câu này.
- **Tính đảo ngược**: Rất cao; có thể dễ dàng thay đổi nhà cung cấp LLM (OpenAI, Gemini, Ollama) bằng cách sửa prompt template Text-to-SQL.

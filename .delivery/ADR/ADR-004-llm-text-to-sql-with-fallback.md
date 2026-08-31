---
artifact: ADR-004-llm-text-to-sql-with-fallback.md
version: 3.0.0
owner: design-architecture
status: approved
updated_at: "2026-08-27T18:05:00+07:00"
affected_requirements:
  - REQ-008
  - CR-002
  - CR-005
---

# ADR-004: Kiến trúc Hỏi đáp AI — LLM sinh QuerySpec, backend dựng SQL

- Context: Truy vấn sự kiện an ninh bằng ngôn ngữ tự nhiên tiếng Việt.
- Decision: LLM sinh **QuerySpec có kiểu**; backend biên dịch spec thành SQL tham số hóa. Rule Engine dự phòng sinh cùng một QuerySpec.
- Status: approved
- Thay thế: rev.2 (bản 2.0.0) cho LLM sinh thẳng SQL. Xem mục "Vì sao đổi trục".

## Vì sao đổi trục (rev.3, 2026-08-27)

Bản Text-to-SQL đặt lên vai mô hình những thứ nó không thể biết chắc: tên cột,
giá trị enum thật đang nằm trong CSDL, cách join `vehicles`. Khi dữ liệu lệch,
mô hình **sai im lặng** — SQL chạy được, trả 0 dòng, câu trả lời nghe vẫn trôi
chảy. Ba lỗi quan sát được trên môi trường thật:

1. `events.object_class` lưu tên tiếng Việt trong khi prompt dạy khoá tiếng Anh,
   nên `WHERE object_class = 'forklift'` luôn trả 0 dù có 302 sự kiện xe nâng.
2. Clip bằng chứng ở nhánh LLM lấy theo "sự kiện mới nhất có clip", không theo bộ
   lọc của câu hỏi — bằng chứng lạc đề so với câu trả lời.
3. Câu trả lời in thẳng giá trị cột thô (`clip vi pham: /videos/BAI_KIEM.mp4`) vì
   bộ diễn giải phải đoán ngữ nghĩa ngược từ bí danh cột.

Cả ba đều là hệ quả của việc để mô hình quyết định *hình dạng truy vấn*.

## Kiến trúc

```
Câu hỏi tiếng Việt
      ↓  chặn chitchat (không tốn lượt gọi LLM)
      ↓  Gemini structured output (response_schema cố định)
QuerySpec  ← Pydantic validate, enum ngoài danh sách bị loại
      ↓  compile_spec()  — code thuần, không LLM
SQL tham số hóa (+ truy vấn bằng chứng dùng CÙNG mệnh đề WHERE)
      ↓
render_answer(spec, rows) → câu trả lời tiếng Việt + clips[]
```

`QuerySpec` (`backend/app/services/query_spec.py`) là toàn bộ những gì LLM được
phép quyết định: `metric`, `event_type`, `object_class`, `tag_label`,
`min_severity`, `license_plate`, `camera_id`, `time_range`, `group_by`, `limit`,
`offset`, `want_clips`.

Backend là nơi **duy nhất** biết schema CSDL. Schema đổi thì chỉ sửa compiler.

## Nhà cung cấp LLM

Provider: **Google Gemini** qua SDK `google-genai`, chế độ structured output
(`response_mime_type="application/json"` + `response_schema`).

- Model mặc định: `GEMINI_MODEL`, giá trị mặc định `gemini-3.1-flash-lite`.
- Khóa API: `GEMINI_API_KEY`, đọc từ `.env` qua `app.core.config.Settings`.
- `time_range` nằm trong `required` của schema: khi để tùy chọn, mô hình hay bỏ
  trống và spec rơi về `all`, khiến câu hỏi "tháng này" bị trả lời bằng số liệu
  toàn bộ lịch sử.

## Thứ tự ưu tiên khi trả lời

1. **Chitchat** — câu chào / hỏi năng lực trả lời tĩnh, không mở session, không
   sinh spec, không kèm clip.
2. **Nhánh LLM** — Gemini sinh `QuerySpec`. Thử lại đúng **một lần** kèm mô tả lỗi
   khi output không dựng được spec.
3. **Nhánh Rule Engine** — từ khóa tiếng Việt sinh **cùng kiểu `QuerySpec`**, nên
   phần biên dịch, diễn giải và gắn clip chỉ có một đường chạy duy nhất.

## Điều kiện fallback bắt buộc

Rớt về Rule Engine khi bất kỳ điều nào xảy ra:

- `GEMINI_API_KEY` trống hoặc không được cấu hình (khi đó **không** thử lại lượt 2).
- Thư viện `google-genai` chưa được cài đặt (`ImportError`).
- Lời gọi Gemini ném lỗi bất kỳ (mạng, quota, model không tồn tại, timeout).
- Output không parse được thành JSON, hoặc không khớp `QuerySpec` sau cả lượt thử lại.

Fallback phải im lặng với người dùng cuối: response vẫn đúng schema
`QueryResponse`, không lộ lỗi hạ tầng ra câu trả lời.

## Ràng buộc an toàn

Chốt `_FORBIDDEN_SQL` và bộ kiểm duyệt "một câu SELECT đơn" đã **bị gỡ bỏ** — không
phải vì nới lỏng, mà vì không còn đối tượng để kiểm duyệt:

- LLM không sinh SQL. Không có trường nào trong `QuerySpec` chứa được câu lệnh.
- Mọi giá trị bộ lọc đi qua **bound parameter** của SQLAlchemy, không nối chuỗi.
- Chỉ 4 khung SELECT tĩnh do compiler dựng; không có nhánh nào sinh câu lệnh ghi.
- `limit` bị chặn trần ở `MAX_LIMIT = 50`; số clip chặn ở `MAX_CLIPS = 5`.
- Câu hỏi của người dùng chỉ nằm trong phần nội dung của prompt.

## Bằng chứng (clip)

- Truy vấn clip dùng **đúng mệnh đề WHERE** của truy vấn chính. Bằng chứng không
  thể lạc đề so với câu hỏi — đây là ràng buộc cấu trúc, không phải quy ước.
- `metric=list` lấy clip thẳng từ các dòng kết quả.
- Khử trùng lặp theo URL: nhiều sự kiện có thể trỏ về cùng một file video nguồn.
- Kết quả nghiệp vụ rỗng (`COUNT(*) = 0`) thì **không** đính kèm clip.

## Hội thoại nhiều lượt

`QueryRequest` nhận `history` (4 lượt cuối) và `previous_spec`. Câu hỏi tiếp nối
("còn nữa không", "lọc xe nâng thôi") được xử lý bằng cách **sửa đổi spec cũ**
thay vì dựng lại từ đầu. Rule Engine cũng hỗ trợ dạng này qua `offset`.

## Kết quả rỗng

Khi truy vấn có khung thời gian và trả về 0 dòng, hệ thống chạy một truy vấn đối
chứng `time_range=all` và gợi ý người dùng mở rộng khung thời gian nếu dữ liệu
thật sự tồn tại ngoài cửa sổ.

Cố ý **không** dùng LLM để tự nới bộ lọc khi kết quả rỗng: "không có vi phạm nào"
là một câu trả lời đúng, và để mô hình nới điều kiện sẽ biến nó thành câu trả lời
khác câu hỏi.

## Hệ quả

- Mất khả năng trả lời câu hỏi hoàn toàn tự do nằm ngoài tập `metric`. Đổi lại,
  mọi câu trả lời đều kiểm chứng được. Mở rộng = thêm giá trị vào enum.
- `sql_query` trả về cho UI vẫn là SQL thật đã chạy (do compiler dựng), nên giá
  trị minh bạch với người dùng không mất.
- Chi phí vận hành thấp hơn: prompt ngắn hơn, output là JSON ngắn thay vì SQL.
- Kiểm thử không cần khóa API thật: compiler và renderer test được thuần túy,
  nhánh LLM mock bằng stub trả `QuerySpec`.

---
artifact: TASK-RESULT.md
version: "1.0"
task_id: TASK-011
owner: implement-backend
status: approved
updated_at: "2026-08-25T11:30:54+07:00"
---

# Kết quả Task: TASK-011 - LLM Text-to-SQL QA Engine (Backend)

- Task ID: TASK-011
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-011/TASK-PACKET.md`, `.delivery/adr/ADR-004-llm-text-to-sql-with-fallback.md`, `.delivery/REQUIREMENTS.md` (REQ-008), `docs/contracts/db/schema.sql`, `backend/database/models.py`, `backend/database/repository.py`.
- Outputs produced: engine Text-to-SQL rule-based truy vấn dữ liệu thật trên bảng `events`, ranh giới chỉ đọc có kiểm chứng, câu trả lời kèm `event_id`/`clip_url` làm chứng cứ, và 19 test bao phủ.
- Changed files: `backend/app/services/qa_agent.py`, `backend/app/api/v1/assistant.py`, `backend/tests/test_chatbot.py`.
- Tests changed: thêm mới `backend/tests/test_chatbot.py` với 19 test.
- Commands run: `.venv/Scripts/python.exe -m pytest backend/tests/test_chatbot.py -q` (lượt 1: `1 failed, 18 passed`, exit 1; lượt 2: `19 passed`, exit 0); `.venv/Scripts/python.exe -m pytest backend/tests -q --ignore=backend/tests/test_live_detections.py --ignore=backend/tests/test_zone_geometry.py` (`3 failed, 79 passed`, exit 1 — đúng 3 lỗi có sẵn từ trước).
- Validation evidence: smoke test endpoint qua `TestClient` trên CSDL thật — `"Hôm nay có bao nhiêu vi phạm?"` trả 200 với `sql_query: SELECT COUNT(*) AS total FROM events WHERE timestamp >= :since AND severity_level = :severity_level` và câu trả lời "Không có sự kiện nào hôm nay vi phạm mức 3" (khớp thực tế CSDL chưa có sự kiện hôm nay); `"kể chuyện cười đi"` trả 200 fallback với `sql_query: null`, `event_id: null`. Số test pass toàn suite tăng 60 → 79, đúng bằng 19 test mới.
- Deviations: `backend/app/models/schemas/assistant.py` giữ nguyên vì nằm ngoài write scope; router chuyển sang khai báo `QueryRequest`/`QueryResponse` inline theo đúng quy ước của `events.py`, nên bản trùng lặp đó không còn được import. Trường `Write scope` trong TASK-PACKET.md ghi `.delivery/tasks/TASK-011/` do `prepare_task.py::render_packet` hard-code giá trị này và bỏ qua trường `Write scope` của MASTER-PLAN; đã dùng write scope chính tắc từ MASTER-PLAN và không sửa file nào ngoài 3 file đã liệt kê.
- Blockers: none
- Scope change requests: tầng LLM của ADR-004 chưa triển khai — xem mục "Scope change request" bên dưới.

## Chi tiết thay đổi

- `backend/app/services/qa_agent.py` — thay toàn bộ câu trả lời canned bằng engine thật: `RuleBasedTranslator` (dịch câu hỏi tiếng Việt sang `SQLPlan`), `assert_read_only` (chặn ghi dữ liệu và chặn bảng ngoài `events`), `LLMQAAgent.answer_question(user_query, db)` (thực thi truy vấn và sinh câu trả lời).
- `backend/app/api/v1/assistant.py` — inject `Session` qua `Depends(get_db)`, khai báo schema inline, bổ sung trường `event_id` vào response.

Bộ test chia 3 nhóm: ranh giới chỉ đọc (7 test, gồm ca câu hỏi chứa `'; DROP TABLE events;--` chỉ thành giá trị bind), dịch câu hỏi (4 test), và trả lời từ dữ liệu thật (8 test, khoá lại việc bỏ câu trả lời cứng "15 sự kiện" và việc không bịa clip chứng cứ khi không có sự kiện khớp).

## Vòng self-healing

Chạy 2 lượt. Lượt 1 hỏng ở `test_unmatched_question_returns_none_instead_of_guessing`: câu "thời tiết hôm nay thế nào" chứa "hôm nay" nên bộ lọc thời gian khớp và translator tưởng đã hiểu câu hỏi. Đây là lỗi thiết kế thật chứ không phải test sai, nên sửa translator (thêm cờ `has_subject` — mốc thời gian một mình không đủ để dịch) thay vì sửa test.

## Scope change request

**Tầng LLM của ADR-004 chưa được triển khai.** ADR-004 quy định "LLM Text-to-SQL kết hợp Fallback Rule-based Engine"; bản này mới làm tầng fallback rule-based. Lý do:

- `requirements.txt` không có LLM client nào (`openai`, `anthropic`, `langchain`, `ollama`, `google-genai` đều vắng). `ARCHITECTURE.md` nêu "OpenAI / Gemini API / Ollama" như lựa chọn nhưng chưa chốt.
- `requirements.txt` là shared file, theo `plan-delivery` không được nằm trong write scope của bất kỳ task nào; thêm dependency vượt write scope của TASK-011.
- Chọn nhà cung cấp LLM kéo theo API key, chi phí và ràng buộc bảo mật — thuộc quyết định kiến trúc, không phải quyết định của tầng triển khai.

Chỗ cắm đã sẵn sàng: giao thức `TextToSQLTranslator` và tham số `LLMQAAgent(translator=...)`, có test khoá lại (`test_custom_translator_seam_is_used`). Cắm tầng LLM về sau không phải sửa tầng thực thi hay ranh giới chỉ đọc.

## Hạn chế đã biết

Câu hỏi không dấu (`"Hom nay co bao nhieu vi pham"`) rơi vào fallback vì bộ luật khớp theo chuỗi có dấu, trong khi người dùng thật hay gõ không dấu. Không nằm trong completion gate nên chưa xử lý; nên đưa vào phạm vi tầng LLM hoặc một CR riêng.

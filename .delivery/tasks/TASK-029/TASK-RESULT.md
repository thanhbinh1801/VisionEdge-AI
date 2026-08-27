---
artifact: TASK-RESULT.md
version: "1.1"
task_id: TASK-029
owner: implement-backend
status: in-review
updated_at: "2026-08-26T16:40:50+07:00"
---

# Kết quả Task: TASK-029 — Tích hợp Google Gemini LLM Text-to-SQL cho AI Chatbot Assistant

- Task ID: TASK-029
- Outcome: completed
- Inputs used: `.delivery/tasks/TASK-029/TASK-PACKET.md`, `.delivery/MASTER-PLAN.md`, `.delivery/ADR/ADR-004-llm-text-to-sql-with-fallback.md`, `.delivery/tasks/TASK-013/TASK-RESULT.md`, `.delivery/tasks/TASK-013/BUG-001.md`, `backend/app/services/qa_agent.py`, `backend/app/core/config.py`, `backend/app/models/schemas/assistant.py`, `backend/database/models.py`.
- Outputs produced: revision 1.1 bổ sung bộ lọc chitchat, bộ diễn giải kết quả tiếng Việt, gate clip bằng chứng và `.delivery/tasks/TASK-029/BUG-001.md`; nhánh LLM Gemini trong `backend/app/services/qa_agent.py` với fallback về Rule Engine; cấu hình `GEMINI_API_KEY`/`GEMINI_MODEL` trong `backend/app/core/config.py` và `.env.example`; dependency `google-genai` trong `requirements.txt`; 26 test mock mới trong `backend/tests/test_chatbot.py`; `.delivery/tasks/TASK-029/TASK-PACKET.md`; cập nhật `.delivery/MASTER-PLAN.md` (v2.3.0, Phase 6) và `.delivery/ADR/ADR-004-llm-text-to-sql-with-fallback.md` (v2.0.0).
- Validation evidence: revision 1.1 — `python -m pytest backend/tests/test_chatbot.py -q -p no:warnings` → `76 passed in 64.23s` (exit 0); `python -m pytest backend/tests -q -p no:warnings --deselect backend/tests/test_model_real_call.py` → `156 passed, 1 deselected in 235.38s` (exit 0); `python .claude/skills/implement-backend/scripts/validate_backend_implementation.py VisionEdge-AI TASK-029` → `OK` (exit 0). Revision 1.0 — `python -m pytest backend/tests/test_chatbot.py -q -p no:warnings` → `42 passed in 58.85s` (16 test cũ của TASK-013 + 26 test mới). Regression: `test_alerts.py test_live_detections_event.py test_database.py test_database_config.py` → `32 passed`; `test_dataset_object_labeling.py test_dataset_zone_sync.py test_ai_engine.py test_websocket_connection_manager.py test_websocket_route_contract.py test_video_frame_api.py test_gate_zones.py test_area_metadata_runtime.py` → `45 passed`.
- Changed files: revision 1.1 — `backend/app/services/qa_agent.py` (+120/-24: `_is_chitchat`, `_CHITCHAT_EXACT`, `_CHITCHAT_PATTERN`, `_CHITCHAT_ANSWER`, `_rows_have_data`, `_render_llm_rows` viết lại, `_LLM_INSTRUCTIONS` mở rộng, gate clip ở cả hai nhánh), `backend/tests/test_chatbot.py` (+34 test), `.delivery/tasks/TASK-029/BUG-001.md` (mới), `.delivery/tasks/TASK-029/TASK-RESULT.md`. Revision 1.0 — `backend/app/services/qa_agent.py` (+561/-15), `backend/app/core/config.py` (+5), `.env.example` (+8/-1), `requirements.txt` (+1), `backend/tests/test_chatbot.py`, `.delivery/MASTER-PLAN.md`, `.delivery/ADR/ADR-004-llm-text-to-sql-with-fallback.md`, `.delivery/tasks/TASK-029/`.
- Tests changed: revision 1.1 — `backend/tests/test_chatbot.py` thêm 34 test cho TASK-029/BUG-001 (`test_chitchat_is_detected` 14 ca, `test_real_questions_are_not_treated_as_chitchat` 6 ca, `test_greeting_returns_friendly_answer_without_sql_or_clip` 5 ca, `test_greeting_never_reaches_the_llm_branch`, `test_greeting_works_without_any_session`, 3 test render, 3 test gate clip, `test_llm_prompt_teaches_zone_violation_filter`) và helper `_FakeRow`; không sửa test cũ nào. Revision 1.0 — thêm `StubLLM`, fixture autouse `disable_llm_by_default`, và 26 test cho nhánh LLM, bộ làm sạch SQL, guardrail của generator và bộ dựng câu trả lời.
- Commands run: revision 1.1 — `python -m pytest backend/tests/test_chatbot.py -q -p no:warnings` (76 passed, exit 0); `python -m pytest backend/tests -q -p no:warnings --deselect backend/tests/test_model_real_call.py` (156 passed, 1 deselected, exit 0); `python .claude/skills/framework/scripts/current_timestamp.py`; `python .claude/skills/implement-backend/scripts/validate_backend_implementation.py VisionEdge-AI TASK-029` (exit 0). Revision 1.0 — `python -m pytest backend/tests/test_chatbot.py -q -p no:warnings` (42 passed); hai lệnh pytest regression nêu trên (32 passed, 45 passed); kiểm tra cấu hình bằng `python -c` (xác nhận `available()`, nhánh `ImportError`); `git check-ignore -v .env`; `git ls-files --error-unmatch .env`.
- Deviations: model ID `gemini-3.1-flash-lite` chưa xác minh được; nhánh gọi Gemini thật chưa chạy lần nào — xem `Giới hạn kiểm chứng`.
- Blockers: none
- Scope change requests: none

## Kiến trúc đã triển khai

`answer_question()` giờ thử hai nhánh theo đúng thứ tự ADR-004:

1. **Nhánh LLM** — `GeminiSqlGenerator` gửi schema rút gọn (`events`, `vehicles`, `zones`, `cameras`) kèm ánh xạ nghĩa tiếng Việt và câu hỏi cho Gemini, nhận về một câu `SELECT`, rồi thực thi thật trên SQLite.
2. **Nhánh Rule Engine** — 5 intent tiếng Việt của TASK-013, giữ nguyên không đổi.

Session được mở một lần ở `answer_question()` và dùng chung cho cả hai nhánh, nên khi nhánh LLM hỏng thì nhánh Rule Engine tái sử dụng đúng session đó thay vì mở thêm kết nối.

## Chốt an toàn

`_sanitize_llm_sql()` áp cho **mọi** SQL do LLM sinh ra, trước khi chạm database:

- Gỡ khối markdown ```` ```sql ```` mà model hay bọc thêm dù prompt đã dặn không.
- Bắt buộc khớp `_SINGLE_SELECT_RE` — một câu `SELECT` đơn. Chuỗi kiểu `SELECT 1; DROP TABLE events` bị từ chối, chặn nối lệnh qua prompt injection.
- Vẫn đi qua `_FORBIDDEN_SQL` như yêu cầu của packet — chốt này không bị nới lỏng cho nhánh LLM.
- Tự chèn `LIMIT 50` nếu model quên, vì không thể tin model luôn tuân thủ hướng dẫn.
- Câu hỏi người dùng chỉ nằm trong phần nội dung của prompt, không bao giờ được nối chuỗi vào SQL.

Test `test_falls_back_to_rules_when_llm_returns_write_statement` kiểm chứng trực tiếp: cho model trả `DELETE FROM events`, sau lời gọi vẫn phải còn đúng 3 bản ghi trong bảng.

## Điều kiện fallback đã phủ test

| Tình huống | Test |
|---|---|
| Không có `GEMINI_API_KEY` | `test_falls_back_to_rules_when_no_api_key`, `test_generator_returns_none_without_key_and_never_calls_network` |
| Chưa cài `google-genai` | Xác minh thủ công — xem dưới |
| Generator ném lỗi | `test_falls_back_to_rules_when_generator_raises` |
| SDK ném lỗi mạng/quota | `test_generator_swallows_client_errors` |
| Model trả rỗng / văn xuôi / lệnh ghi | `test_sanitizer_rejects_unsafe_or_non_select` (9 tham số) |
| SQL sai cột, chạy lỗi trên SQLite | `test_falls_back_to_rules_when_generated_sql_is_invalid` |

Xác minh thủ công nhánh `ImportError`: máy hiện tại **chưa cài** `google-genai`, và `GeminiSqlGenerator().generate_sql('test')` trả `None` kèm log `Chưa cài google-genai; dùng Rule Engine thay thế`. Đây là bằng chứng chạy thật cho nhánh thiếu thư viện.

Fallback im lặng với người dùng cuối: `test_falls_back_to_rules_when_generator_raises` khẳng định chuỗi `"quota exceeded"` không lọt vào `answer`.

## Ghi chú về tính tất định của test

Thêm fixture autouse `disable_llm_by_default` ép `settings.GEMINI_API_KEY = None` cho toàn bộ file test. Không có nó, 16 test Rule Engine của TASK-013 sẽ lặng lẽ gọi mạng thật trên máy có khóa API trong `.env` — máy đang chạy chính là một máy như vậy. Test nào cần nhánh LLM thì tự truyền `StubLLM`, nên không test nào chạm mạng.

## Giới hạn kiểm chứng

- **Model ID `gemini-3.1-flash-lite` chưa được xác minh.** Đây là giá trị do project owner chỉ định; tôi không xác nhận được nó tồn tại trong danh mục model của Google. Nó được đặt làm mặc định của `GEMINI_MODEL` và ghi đè được qua `.env`, nên nếu sai thì hệ thống rơi xuống Rule Engine chứ không sập — nhưng nhánh LLM sẽ im lặng không bao giờ chạy. Cần xác nhận lại chuỗi model ID chính xác.
- **Chưa có lời gọi Gemini thật nào được thực hiện.** `google-genai` chưa cài trên máy này, và tôi không tự gọi API ngoài vì việc đó phát sinh chi phí và gửi dữ liệu ra dịch vụ bên ngoài. Toàn bộ nhánh LLM được kiểm bằng mock. Đường đi từ `client.models.generate_content(...)` tới response thật vì vậy **chưa được kiểm chứng end-to-end**.
- Để nghiệm thu đầy đủ cần: `pip install google-genai`, xác nhận model ID, rồi chạy một truy vấn thật và đối chiếu SQL sinh ra.

## Ghi chú độc lập

`backend/tests/test_video_feed_regression.py` vẫn có 3 test fail với `AttributeError: 'Query' object has no attribute 'replace'` tại `backend/app/services/frame_extractor.py:55`. Đã ghi nhận trong phụ lục backend của `TASK-013/TASK-RESULT.md`; nguyên nhân là đợt refactor `frame_extractor.py` từ bên ngoài, không liên quan tới TASK-029. Phạm vi ghi của TASK-029 không chạm file đó.

Ngoài ra `backend/tests/test_zz_probe.py` là file lạ xuất hiện trong working tree, không thuộc task nào.

## Revision 1.1 — sửa TASK-029/BUG-001

Sau khi bật `GEMINI_API_KEY` thật, nhánh LLM của revision 1.0 lộ ba khiếm khuyết làm hỏng trải nghiệm Tab 4: mọi câu hỏi, kể cả câu chào "hi", đều nhận `answer = "Kết quả: 839."` kèm clip 10s. Chi tiết root cause và cách tái hiện nằm trong `.delivery/tasks/TASK-029/BUG-001.md`.

Bốn thay đổi, chỉ chạm `backend/app/services/qa_agent.py` và `backend/tests/test_chatbot.py` — đúng implementation write scope của packet:

1. **Bộ lọc chitchat trước cả hai nhánh.** `_is_chitchat()` chặn ngay đầu `answer_question()`, trả `_CHITCHAT_ANSWER` với `sql_query = None`, `clip_url = None`, và `return` trước khi mở session. Câu chào không mở kết nối CSDL và không tiêu tốn lượt gọi Gemini. Khớp theo tập chính xác cộng regex có biên từ; `đ` được quy về `d` thủ công vì NFD không tách được ký tự này.
2. **`_render_llm_rows()` viết lại** thành bộ diễn giải tiếng Việt dựa trên hình dạng kết quả và bí danh cột, không dựa vào câu hỏi gốc. Tiền tố `"Kết quả: {số}."` bị loại bỏ.
3. **Gate clip bằng `_rows_have_data()`** — áp cho cả nhánh LLM lẫn nhánh Rule Engine. Một dòng aggregate toàn số 0 được coi là không có sự kiện, nên không kèm clip.
4. **`_LLM_INSTRUCTIONS` bổ sung** ngữ cảnh giám sát an ninh cổng/bãi và bảng ánh xạ ngữ nghĩa bắt buộc, trong đó vi phạm khu vực cấm phải lọc `event_type IN ('ZONE_VIOLATION', 'RESTRICTED_ACCESS')`.

Ràng buộc ADR-004 giữ nguyên không sửa một dòng nào: `_FORBIDDEN_SQL`, `_SINGLE_SELECT_RE`, cơ chế fallback êm về `_answer_with_rules()`, và schema response `{answer, sql_query, clip_url}` của `POST /api/v1/assistant/query`. Các test chốt những ràng buộc này vẫn xanh mà không phải chỉnh assertion.

Không có test cũ nào bị sửa assertion. `test_render_rows_handles_empty_result` (assert `"Không có dữ liệu"`) vẫn pass vì thông điệp rỗng mới giữ nguyên cụm từ đó.

### Giới hạn của revision 1.1

- Vẫn chưa có lời gọi Gemini thật nào — giới hạn kiểm chứng ở mục trên còn nguyên hiệu lực. Bộ lọc chitchat và bộ diễn giải được kiểm bằng `StubLLM`, nên hành vi thật của Gemini với prompt mới (đặc biệt là bảng ánh xạ ngữ nghĩa) **chưa được đo**. Cần một lượt chạy thật để xác nhận nó thôi sinh `SELECT COUNT(*) FROM events` trần.
- `_latest_clip_url()` ở nhánh LLM vẫn lấy clip mới nhất theo `scope` chứ không theo đúng tập sự kiện mà SQL của LLM trả về. Bug này đã chặn được ca tệ nhất (gắn clip cho câu trả lời rỗng), nhưng clip vẫn có thể lệch khỏi sự kiện được nói tới khi kết quả có dữ liệu. Sửa triệt để cần trích `event id` từ result set — nằm ngoài phạm vi bug này, đề xuất mở CR riêng.
- `backend/tests/test_model_real_call.py` bị deselect ở lệnh regression toàn bộ vì nó gọi model thật qua mạng.

---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-26T15:32:21+07:00"
task_id: TASK-029
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-029 Tích hợp Google Gemini LLM Text-to-SQL cho AI Chatbot Assistant

- Task ID: TASK-029
- Task type: implementation
- Scope: feature
- Module: llm-qa-agent
- Capability: backend-implementation
- Linked requirements: REQ-008, CR-002
- Dependencies: TASK-013
- Write scope: .delivery/tasks/TASK-029/
- Implementation write scope: backend/app/services/qa_agent.py, backend/app/core/config.py, backend/tests/test_chatbot.py, .env.example, requirements.txt (theo cột Write scope của TASK-029 trong .delivery/MASTER-PLAN.md)
- Inputs: .delivery/ADR/ADR-004-llm-text-to-sql-with-fallback.md, .delivery/tasks/TASK-013/TASK-RESULT.md, .delivery/tasks/TASK-013/BUG-001.md, backend/app/services/qa_agent.py, backend/app/core/config.py, backend/app/models/schemas/assistant.py, backend/database/models.py
- Expected outputs: cấu hình `GEMINI_API_KEY`/`GEMINI_MODEL`, dependency `google-genai`, nhánh LLM Text-to-SQL trong `qa_agent.py` với fallback về Rule Engine, test mock trong `backend/tests/test_chatbot.py`, .delivery/tasks/TASK-029/TASK-RESULT.md
- Completion gate: Gemini dịch câu hỏi tiếng Việt thành SQL và SQL đó được thực thi thật trên SQLite; chốt an toàn `_FORBIDDEN_SQL` vẫn chặn mọi câu lệnh không phải `SELECT`; khi thiếu key, thiếu thư viện, Gemini lỗi hoặc trả SQL không hợp lệ thì tự động fallback sang Rule Engine mà không làm hỏng response; toàn bộ test chạy được không cần khóa API thật.
- Verification method: python -m pytest backend/tests/test_chatbot.py -q
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

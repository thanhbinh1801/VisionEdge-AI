---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-25T11:12:32+07:00"
task_id: TASK-011
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-011 Triển khai LLM Text-to-SQL QA Engine (Backend)

- Task ID: TASK-011
- Task type: implementation
- Scope: feature
- Module: llm-qa-agent
- Capability: backend-implementation
- Linked requirements: REQ-008, CR-002
- Dependencies: TASK-006
- Write scope: .delivery/tasks/TASK-011/
- Inputs: docs/contracts/API-FOUNDATION.md, .delivery/adr/ADR-004-llm-text-to-sql-with-fallback.md, docs/contracts/db/schema.sql
- Expected outputs: backend/app/services/qa_agent.py, backend/app/api/v1/assistant.py, backend/tests/test_chatbot.py
- Completion gate: Engine dịch câu hỏi tiếng Việt sang truy vấn SQL chỉ đọc trên bảng `events`, trả về câu trả lời kèm `event_id` để tầng trên lấy clip 10s chứng cứ, và rơi về câu trả lời fallback khi không dịch được truy vấn theo ADR-004. Thay thế câu trả lời canned hiện có trong `LLMQAAgent` bằng truy vấn dữ liệu thật.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

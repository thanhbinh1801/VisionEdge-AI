---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-26T10:40:39+07:00"
task_id: TASK-013
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-013 Triển khai Tab 4 — AI Chatbot Assistant

- Task ID: TASK-013
- Task type: implementation
- Scope: feature
- Module: llm-qa-agent
- Capability: frontend-implementation
- Linked requirements: REQ-008, CR-002
- Dependencies: TASK-006, TASK-008
- Write scope: .delivery/tasks/TASK-013/
- Inputs: docs/contracts/API-FOUNDATION.md
- Expected outputs: frontend/src/pages/AIChatbotAssistant.tsx, backend/ai/text_to_sql.py
- Completion gate: Trang Chatbot tiếng Việt với thanh gợi ý Prompt Chips, trả lời Text-to-SQL đính kèm trình phát `<VideoModal>` clip 10s chứng cứ.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-25T11:31:43+07:00"
task_id: TASK-013
packet_revision: 2
supersedes: TASK-PACKET.r1.md
depends_on: [MASTER-PLAN.md]
---

# TASK-013 Triển khai Tab 4 — AI Chatbot Assistant (Frontend)

- Task ID: TASK-013
- Task type: implementation
- Scope: feature
- Module: llm-qa-agent
- Capability: frontend-implementation
- Linked requirements: REQ-008, CR-002
- Dependencies: TASK-008, TASK-011
- Write scope: .delivery/tasks/TASK-013/
- Inputs: docs/contracts/API-FOUNDATION.md
- Expected outputs: frontend/src/pages/AIChatbotAssistant.tsx
- Completion gate: Trang Chatbot tiếng Việt với thanh gợi ý Prompt Chips, hiển thị câu trả lời từ engine Text-to-SQL của TASK-011 và đính kèm trình phát `<VideoModal>` clip 10s chứng cứ.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

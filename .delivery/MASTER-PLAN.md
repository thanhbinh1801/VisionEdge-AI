---
artifact: MASTER-PLAN.md
version: 1.8.0
owner: plan-delivery
status: approved
updated_at: "2026-08-19T11:08:25+07:00"
depends_on: REQUIREMENTS.md, ARCHITECTURE.md, TECHNICAL-RISKS.md, ADR-001-monolithic-python-fastapi.md, ADR-002-point-in-polygon-zone-evaluation.md, ADR-003-event-cooldown-deduplication.md, ADR-004-llm-text-to-sql-with-fallback.md, ADR-005-Custom-Label-Matching-Architecture.md
---

Delivery scope: change-request

# Kế hoạch Triển khai Dự án Giám sát Camera AI (SentriAI Mini) - CR-002 React & YOLOv26

## 1. Tổng quan Chiến lược Triển khai CR-002

Hệ thống được tổ chức theo 3 Phase chính:
- **Phase 1: Project Initialization & Global Foundation Design**: Khởi tạo khung dự án (Backend & Frontend Scaffold), thiết kế hợp đồng toàn cục `API-FOUNDATION.md`, `DATABASE-DESIGN.md` và `UI-UX-FOUNDATION.md`.
- **Phase 2: Core Data Layer, Engines & Shared Components**: Phát triển CSDL SQLite, Core AI Engine (YOLOv26, Point-in-Polygon, Cooldown) và bộ Shared Components dùng chung (`Header`, `Sidebar`, `AudioBeepPlayer`, `VideoModal`).
- **Phase 3: Module Implementation & System Integration**: Triển khai 4 Trang/Tab chính, tích hợp thời gian thực WebSocket & Telegram Bot và kiểm thử E2E nghiệm thu.

Các trường `Outputs` được định nghĩa linh hoạt theo dạng mô tả hợp đồng đầu ra (như `docs/contracts/API-FOUNDATION.md`, `frontend/src/`, `backend/database/`) giúp các kỹ sư phát triển chủ động bổ sung tệp mã nguồn mới khi lập trình mà không bị ràng buộc cứng nhắc.

---

## 2. Các Giai đoạn Triển khai (Phases & Task Graph)

## Phase 1 — Project Initialization & Global Foundation Design

- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_foundation.py

### Wave 1 (AI Benchmark, API Foundation & Project Init)

#### TASK-001 Pretrained AI Benchmark & Model Selection
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, CR-002
- Capability: backend-implementation
- Dependencies: none
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: docs/reports/ai-model-benchmark.md
- Completion gate: Benchmark mô hình Ultralytics YOLOv26 kết hợp OCR đạt FPS >= 5 trên 2 tệp video mẫu.
- Verification method: python -m pytest backend/tests/test_model_benchmark.py
- Parallelizable: yes
- Write scope: docs/reports/
- Wave: 1
- Status: ready

#### TASK-002 Thiết kế Hợp đồng Global API Foundation
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-009, CR-002
- Capability: api-foundation-design
- Dependencies: TASK-001
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: .delivery/tasks/TASK-002/API-FOUNDATION.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Completion gate: Xuất bản tài liệu hợp đồng REST API (`API-FOUNDATION.md`) và WebSocket event payloads cho React Hooks.
- Verification method: python -m json.tool docs/contracts/api/api-schema.json
- Parallelizable: yes
- Write scope: docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Wave: 1
- Status: ready

#### TASK-005 Khởi tạo Cấu trúc Dự án Backend & Frontend Scaffolding
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, CR-002
- Capability: ui-ux-foundation-design
- Dependencies: TASK-002
- Inputs: .delivery/ARCHITECTURE.md
- Outputs: frontend/src/ (Vite + React SPA structure), backend/ (Python module structure)
- Completion gate: Khởi tạo khung thư mục React SPA (`frontend/src/`) tích hợp Tailwind CSS, Lucide React, Recharts và cấu trúc mô-đun Backend Python (`backend/`).
- Verification method: npm --prefix frontend run build
- Parallelizable: yes
- Write scope: frontend/src/App.tsx, frontend/src/main.tsx, backend/main.py
- Wave: 1
- Status: ready

### Wave 2 (Database Design & UI/UX Foundation)

#### TASK-003 Thiết kế CSDL & Database Schema Foundation
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-006, CR-002
- Capability: database-design
- Dependencies: TASK-002
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: .delivery/tasks/TASK-003/DATABASE-DESIGN.md, docs/contracts/db/schema.sql
- Completion gate: Xuất bản tài liệu thiết kế CSDL (`DATABASE-DESIGN.md`), định nghĩa các thực thể Camera, Zone, Event, Tag và Script khởi tạo `schema.sql`.
- Verification method: python -m pytest backend/tests/test_database_schema.py
- Parallelizable: yes
- Write scope: docs/contracts/db/schema.sql
- Wave: 2
- Status: ready

#### TASK-004 Thiết kế UI/UX Foundation & React Design System
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-005, CR-002
- Capability: ui-ux-foundation-design
- Dependencies: TASK-002
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: docs/contracts/UI-UX-FOUNDATION.md, frontend/src/assets/
- Completion gate: Xuất bản tài liệu hợp đồng giao diện (`UI-UX-FOUNDATION.md`) quy định màu sắc, bảng mã màu cảnh báo, bố cục 4 tab và hệ thống icon Lucide.
- Verification method: npm --prefix frontend run test
- Parallelizable: yes
- Write scope: frontend/src/assets/index.css
- Wave: 2
- Status: ready

---

## Phase 2 — Core Data Layer, Engines & Shared Components

- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_services.py

### Wave 1 (CSDL Engine, Core AI Engines & Shared Components)

#### TASK-006 Triển khai CSDL SQLite & Data Access Layer
- Task type: implementation
- Scope: feature
- Module: database-storage
- Linked requirements: REQ-001, REQ-006, CR-002
- Capability: backend-implementation
- Dependencies: TASK-003, TASK-005
- Inputs: docs/contracts/DATABASE-DESIGN.md
- Outputs: backend/database/ (SQLite Engine & ORM Models)
- Completion gate: Triển khai ORM/Data Access Layer lưu trữ camera, zone, biển số quen/lạ, dataset nhãn custom và bản ghi vi phạm.
- Verification method: python -m pytest backend/tests/test_database.py
- Parallelizable: yes
- Write scope: backend/database/
- Wave: 1
- Status: ready

#### TASK-007 Triển khai Core AI Engine & React Custom Hooks
- Task type: implementation
- Scope: feature
- Module: ai-vision-pipeline
- Linked requirements: REQ-004, REQ-007, CR-002
- Capability: backend-implementation
- Dependencies: TASK-001, TASK-006
- Inputs: .delivery/ARCHITECTURE.md, docs/contracts/API-FOUNDATION.md
- Outputs: backend/ai/ (Evaluator & Slicer), frontend/src/hooks/ (WebSocket & Sound Hooks)
- Completion gate: Triển khai thuật toán Point-in-Polygon, cửa sổ trượt lọc trùng lặp Cooldown 15s và custom hooks (`useWebSocket`, `useAudioAlert`).
- Verification method: python -m pytest backend/tests/test_engine.py
- Parallelizable: yes
- Write scope: backend/ai/, frontend/src/hooks/
- Wave: 1
- Status: ready

#### TASK-008 Phát triển Bộ Shared UI Components
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-003, REQ-009, CR-002
- Capability: frontend-implementation
- Dependencies: TASK-004, TASK-005
- Inputs: docs/contracts/UI-UX-FOUNDATION.md
- Outputs: frontend/src/components/ (Header, Sidebar, AudioBeepPlayer, VideoModal)
- Completion gate: Hoàn thiện 4 Shared Components chính (`Header`, `Sidebar`, `AudioBeepPlayer` phát còi bíp Mức 3, `VideoModal` xem clip 10s chứng cứ).
- Verification method: npm --prefix frontend run test
- Parallelizable: yes
- Write scope: frontend/src/components/
- Wave: 1
- Status: ready

---

## Phase 3 — Module Implementation & System Integration

- Gate: all-complete
- Integration commands: python -m pytest backend/tests/test_integration.py && npm --prefix frontend run build

### Wave 1 (Gate Dashboard & Area Dashboard)

#### TASK-009 Triển khai Tab 1 — Gate Dashboard (LPR Cổng)
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-001, CR-002
- Capability: frontend-implementation
- Dependencies: TASK-007, TASK-008
- Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md
- Outputs: frontend/src/pages/GateDashboard.tsx
- Completion gate: Trang Cổng Vấn render stream camera GATE-01, nhận diện LPR realtime bằng YOLOv26 và bộ 4 thẻ Recharts KPI visualizers.
- Verification method: npm --prefix frontend run build
- Parallelizable: yes
- Write scope: frontend/src/pages/GateDashboard.tsx
- Wave: 1
- Status: ready

#### TASK-010 Triển khai Tab 2 — Area Security Dashboard (Bãi kiểm)
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-002, CR-002
- Capability: frontend-implementation
- Dependencies: TASK-007, TASK-008
- Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md
- Outputs: frontend/src/pages/AreaSecurityDashboard.tsx
- Completion gate: Trang Bãi kiểm render stream BAI-KIEM, phát hiện vi phạm quy tắc zone bằng YOLOv26 và bộ 4 thẻ Recharts KPI visualizers.
- Verification method: npm --prefix frontend run build
- Parallelizable: yes
- Write scope: frontend/src/pages/AreaSecurityDashboard.tsx
- Wave: 1
- Status: ready

### Wave 2 (Zone Settings & AI Chatbot)

#### TASK-012 Triển khai Tab 3 — Zone & Tag Settings (SVG Canvas Editor)
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-005, REQ-006, REQ-007, CR-002
- Capability: frontend-implementation
- Dependencies: TASK-006, TASK-008
- Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md
- Outputs: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/
- Completion gate: Trang Cài đặt tích hợp SVG Canvas Polygon Editor, bảng gán nhãn xe 1-click và timeline scrubber gán nhãn dataset custom.
- Verification method: npm --prefix frontend run build
- Parallelizable: yes
- Write scope: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/
- Wave: 2
- Status: ready

#### TASK-013 Triển khai Tab 4 — AI Chatbot Assistant
- Task type: implementation
- Scope: feature
- Module: llm-qa-agent
- Linked requirements: REQ-008, CR-002
- Capability: frontend-implementation
- Dependencies: TASK-006, TASK-008
- Inputs: docs/contracts/API-FOUNDATION.md
- Outputs: frontend/src/pages/AIChatbotAssistant.tsx, backend/ai/text_to_sql.py
- Completion gate: Trang Chatbot tiếng Việt với thanh gợi ý Prompt Chips, trả lời Text-to-SQL đính kèm trình phát `<VideoModal>` clip 10s chứng cứ.
- Verification method: python -m pytest backend/tests/test_chatbot.py
- Parallelizable: yes
- Write scope: frontend/src/pages/AIChatbotAssistant.tsx, backend/ai/text_to_sql.py
- Wave: 2
- Status: ready

### Wave 3 (Realtime Integration & E2E Verification)

#### TASK-014 Tích hợp Realtime WebSocket Events & Multi-channel Alert
- Task type: implementation
- Scope: feature
- Module: alert-dispatcher
- Linked requirements: REQ-003, REQ-009, CR-002
- Capability: frontend-implementation
- Dependencies: TASK-007, TASK-008
- Inputs: docs/contracts/API-FOUNDATION.md
- Outputs: frontend/src/context/AlertContext.tsx, backend/api/websocket_gateway.py
- Completion gate: Phát còi bíp cảnh báo Mức 3 thời gian thực trên trình duyệt qua `<AudioBeepPlayer>` và gửi tin nhắn đính kèm ảnh crop sang Telegram Bot.
- Verification method: python -m pytest backend/tests/test_alerts.py
- Parallelizable: yes
- Write scope: frontend/src/context/, backend/api/
- Wave: 3
- Status: ready

#### TASK-015 Kiểm thử E2E & Nghiệm thu Toàn diện Hệ thống
- Task type: verification
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, CR-002
- Capability: verify-feature
- Dependencies: TASK-009, TASK-010, TASK-012, TASK-013, TASK-014
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: docs/reports/e2e-verification-report.md
- Completion gate: Nghiệm thu toàn bộ 4 tab chính, nhận diện mượt mà với YOLOv26, trích xuất đúng 10s MP4 clip và phát còi bíp Mức 3.
- Verification method: python -m pytest tests/e2e/test_full_system.py
- Parallelizable: no
- Write scope: docs/reports/
- Wave: 3
- Status: ready

---

## 3. Bản đồ Bao phủ Yêu cầu (Coverage Map)

## Coverage Map
- REQ-001 -> TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-009, TASK-015
- REQ-002 -> TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-010, TASK-015
- REQ-003 -> TASK-002, TASK-004, TASK-008, TASK-014, TASK-015
- REQ-004 -> TASK-007, TASK-015
- REQ-005 -> TASK-002, TASK-004, TASK-012, TASK-015
- REQ-006 -> TASK-003, TASK-006, TASK-012, TASK-015
- REQ-007 -> TASK-007, TASK-012, TASK-015
- REQ-008 -> TASK-002, TASK-013, TASK-015
- REQ-009 -> TASK-002, TASK-008, TASK-014, TASK-015
- CR-002 -> TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-012, TASK-013, TASK-014, TASK-015

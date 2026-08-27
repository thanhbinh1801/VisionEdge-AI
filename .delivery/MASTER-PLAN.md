---
artifact: MASTER-PLAN.md
version: 2.4.0
owner: plan-delivery
status: approved
updated_at: "2026-08-27T20:10:00+07:00"
depends_on: REQUIREMENTS.md, ARCHITECTURE.md, TECHNICAL-RISKS.md, ADR-001-monolithic-python-fastapi.md, ADR-002-point-in-polygon-zone-evaluation.md, ADR-003-event-cooldown-deduplication.md, ADR-004-llm-text-to-sql-with-fallback.md, ADR-005-Custom-Label-Matching-Architecture.md
---

Delivery scope: change-request

# Kế hoạch Triển khai Dự án Giám sát Camera AI (SentriAI Mini) - CR-001 đến CR-007

## 1. Tổng quan Chiến lược Triển khai

Phạm vi master plan hiện tại bao phủ 6 change request:
- `CR-001`: luồng giám sát cổng/khu vực, zone rules, whitelist/dataset nền tảng.
- `CR-002`: hoàn thiện UI dùng chung, alert flows, chatbot và nghiệm thu tích hợp.
- `CR-003`: tách `Area Zone Monitoring` thành `video stream lane`, `realtime metadata lane`, `event/alert lane`, đồng thời đưa zone rules vào cache in-memory để loại DB khỏi hot path mỗi frame.
- `CR-004`: chuyển tab `Cài đặt > Nhãn đối tượng` từ mock/local state sang flow dữ liệu thật gồm import ảnh/video, chọn frame, bbox samples persisted, CRUD nhãn custom mềm và đồng bộ zone rules.
- `CR-005`: gửi Telegram evidence notification cho vi phạm khu vực do đối tượng cấm đi vào zone, gồm thời gian vi phạm đúng, camera, zone, loại đối tượng, lý do vi phạm và file video clip chứng cứ 10s.
- `CR-007`: cải thiện độ tin cậy Area Monitoring trên `BAI-KIEM` bằng YOLOv11s finetune, tách display/debug threshold khỏi event/alert threshold, chuẩn hóa class-aware zone evaluation, bổ sung metadata debug additive và giữ tracking ở mức optional/future-compatible.

Hệ thống được tổ chức theo 7 Phase chính:
- **Phase 1: Project Initialization & Global Foundation Design**: Khởi tạo khung dự án (Backend & Frontend Scaffold), thiết kế hợp đồng toàn cục `API-FOUNDATION.md`, `DATABASE-DESIGN.md` và `UI-UX-FOUNDATION.md`.
- **Phase 2: Core Data Layer, Engines & Shared Components**: Phát triển CSDL SQLite (Xe quen/Xe lạ, Polygon zone rules, Custom BBox dataset samples), Core AI Engine (8 nhóm phương tiện/người, zone evaluation, Cooldown) và bộ Shared Components.
- **Phase 3: Module Implementation & System Integration**: Triển khai 4 Trang/Tab chính (Gate Dashboard LPR, Area Security Dashboard, Zone & Tag Settings với SVG Canvas 4 thao tác & BBox dataset tool, AI Chatbot Assistant với clip 10s bằng chứng), sau đó bổ sung refactor realtime area metadata cho `CR-003` và verification liên quan.
- **Phase 4: CR-004 Real Object Labeling Flow**: Thiết kế DB/storage, API và UI/UX cho object labeling thật, sau đó triển khai backend/frontend và nghiệm thu end-to-end.
- **Phase 5: CR-005 Telegram Evidence Notification**: Thiết kế contract event/alert evidence, triển khai backend Telegram gửi file video 10s trực tiếp kèm nội dung bắt buộc, kiểm tra nhất quán AI Assistant evidence và nghiệm thu end-to-end cho thông báo Telegram.
- **Phase 6: Gemini LLM Text-to-SQL cho AI Chatbot**: Tích hợp Gemini vào AI Assistant với fallback an toàn.
- **Phase 7: CR-007 Area Monitoring Detection & BBox Reliability**: Thiết kế/triển khai lại contract phát hiện khu vực theo YOLOv11s finetune, threshold layering, bbox renderer debug container, class-aware zone evaluation và verification regression không làm đổi LPR/GATE-01.

## 2. Tổng quan Task Inventory

- Tổng số task hiện có trong master plan: `32`
- Dải task hiện dùng: `TASK-001` đến `TASK-033`, trừ `TASK-011` hiện chưa được cấp phát
- Nhóm foundation/design: `TASK-001` đến `TASK-005`, `TASK-016`
- Nhóm feature design: `TASK-020`, `TASK-021`, `TASK-022`, `TASK-026`, `TASK-030`
- Nhóm implementation: `TASK-006` đến `TASK-010`, `TASK-012` đến `TASK-014`, `TASK-017`, `TASK-018`, `TASK-023`, `TASK-024`, `TASK-027`, `TASK-029`, `TASK-031`, `TASK-032`
- Nhóm verification/diagnosis: `TASK-015`, `TASK-019`, `TASK-025`, `TASK-028`, `TASK-033`

### Danh sách task hiện hữu

| Task | Capability | Mục tiêu ngắn |
|---|---|---|
| `TASK-001` | `backend-implementation` | Benchmark mô hình AI và chọn stack nhận diện |
| `TASK-002` | `api-foundation-design` | Thiết kế API foundation toàn cục |
| `TASK-003` | `database-design` | Thiết kế database/schema foundation |
| `TASK-004` | `ui-ux-foundation-design` | Thiết kế UI/UX foundation |
| `TASK-005` | `ui-ux-foundation-design` | Khởi tạo scaffold backend/frontend |
| `TASK-006` | `backend-implementation` | Triển khai SQLite và data access layer |
| `TASK-007` | `backend-implementation` | Triển khai core AI engine và custom hooks |
| `TASK-008` | `frontend-implementation` | Phát triển shared UI components |
| `TASK-009` | `frontend-implementation` | Gate Dashboard |
| `TASK-010` | `frontend-implementation` | Area Security Dashboard baseline |
| `TASK-012` | `frontend-implementation` | Zone & Tag Settings |
| `TASK-013` | `frontend-implementation` | AI Chatbot Assistant |
| `TASK-014` | `frontend-implementation` | Realtime alerts và multi-channel dispatch |
| `TASK-015` | `verify-feature` | E2E và nghiệm thu toàn hệ thống baseline |
| `TASK-016` | `api-design` | Thiết kế contract realtime metadata cho area monitoring |
| `TASK-017` | `backend-implementation` | Backend area metadata lane và zone cache |
| `TASK-018` | `frontend-implementation` | Frontend area dashboard consume metadata lane riêng |
| `TASK-019` | `verify-feature` | Verification cho CR-003 realtime area metadata |
| `TASK-020` | `database-design` | Thiết kế DB/storage cho object labeling thật |
| `TASK-021` | `api-design` | Thiết kế API upload/source/label/sample/frame/sync |
| `TASK-022` | `ui-ux-design` | Thiết kế UI/UX cho Cài đặt > Nhãn đối tượng |
| `TASK-023` | `backend-implementation` | Backend object labeling theo design đã duyệt |
| `TASK-024` | `frontend-implementation` | Frontend object labeling theo design đã duyệt |
| `TASK-025` | `verify-feature` | Verification end-to-end cho CR-004 |
| `TASK-026` | `api-design` | Thiết kế contract event/alert evidence cho Telegram CR-005 |
| `TASK-027` | `backend-implementation` | Backend Telegram evidence notification cho vi phạm khu vực |
| `TASK-028` | `verify-feature` | Verification end-to-end cho CR-005 Telegram evidence |
| `TASK-029` | `backend-implementation` | Tích hợp Google Gemini LLM Text-to-SQL cho AI Chatbot |
| `TASK-030` | `api-design` | CR-007 contract cho Area detection, bbox debug và zone evaluation |
| `TASK-031` | `backend-implementation` | CR-007 backend detection threshold, class mapping và zone evaluator |
| `TASK-032` | `frontend-implementation` | CR-007 frontend debug controls/type surface cho Area Dashboard |
| `TASK-033` | `verify-feature` | CR-007 verification và regression không đổi LPR/GATE-01 |

---

## 3. Các Giai đoạn Triển khai (Phases & Task Graph)

## Phase 1 — Project Initialization & Global Foundation Design

- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_foundation.py

### Wave 1 (AI Benchmark, API Foundation & Project Init)

#### TASK-001 Pretrained AI Benchmark & Model Selection
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, CR-002, CR-007
- Capability: backend-implementation
- Dependencies: none
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: docs/reports/ai-model-benchmark.md
- Completion gate: Benchmark mô hình LPR hiện hữu cho `GATE-01` và YOLOv11s finetune cho Area Monitoring `BAI-KIEM` đạt FPS >= 5 trên 2 tệp video mẫu; ghi rõ inference threshold thấp và application threshold riêng cho CR-007.
- Verification method: python -m pytest backend/tests/test_model_benchmark.py
- Parallelizable: yes
- Write scope: docs/reports/
- Wave: 1
- Status: in-review

#### TASK-002 Thiết kế Hợp đồng Global API Foundation
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-009, CR-001, CR-002, CR-007
- Capability: api-foundation-design
- Dependencies: TASK-001
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: .delivery/tasks/TASK-002/API-FOUNDATION.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Completion gate: Xuất bản tài liệu hợp đồng REST API (`API-FOUNDATION.md`, `API-CONTRACT.md`) quy định rõ 8 loại đối tượng, nhãn Xe quen/Xe lạ, quy tắc Zone và BBox Dataset samples.
- Verification method: python -m json.tool docs/contracts/api/api-schema.json
- Parallelizable: yes
- Write scope: docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Wave: 1
- Status: needs-revision

#### TASK-005 Khởi tạo Cấu trúc Dự án Backend & Frontend Scaffolding
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-005, CR-001, CR-002
- Capability: ui-ux-foundation-design
- Dependencies: TASK-002
- Inputs: .delivery/ARCHITECTURE.md
- Outputs: frontend/src/ (Vite + React SPA structure), backend/ (Python module structure)
- Completion gate: Khởi tạo khung thư mục React SPA (`frontend/src/`) tích hợp Tailwind CSS, Lucide React, Recharts, SVG Canvas Editor và cấu trúc mô-đun Backend Python (`backend/`).
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
- Completion gate: Xuất bản tài liệu thiết kế CSDL (`DATABASE-DESIGN.md`), định nghĩa các thực thể Camera, Zone, Event, Xe quen/Xe lạ và Script khởi tạo `schema.sql`.
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
- Linked requirements: REQ-001, REQ-006, CR-001, CR-002
- Capability: backend-implementation
- Dependencies: TASK-003, TASK-005
- Inputs: docs/contracts/DATABASE-DESIGN.md
- Outputs: backend/database/ (SQLite Engine & ORM Models)
- Completion gate: Triển khai ORM/Data Access Layer lưu trữ camera, zone, biển số quen/lạ, dataset nhãn custom BBox và bản ghi vi phạm.
- Verification method: python -m pytest backend/tests/test_database.py
- Parallelizable: yes
- Write scope: backend/database/
- Wave: 1
- Status: ready

#### TASK-007 Triển khai Core AI Engine & React Custom Hooks
- Task type: implementation
- Scope: feature
- Module: ai-vision-pipeline
- Linked requirements: REQ-004, REQ-007, CR-001, CR-002
- Capability: backend-implementation
- Dependencies: TASK-001, TASK-006
- Inputs: .delivery/ARCHITECTURE.md, docs/contracts/API-FOUNDATION.md
- Outputs: backend/ai/ (Evaluator & Slicer), frontend/src/hooks/ (WebSocket & Sound Hooks)
- Completion gate: Triển khai phân loại nhóm đối tượng, class-aware zone evaluation, cửa sổ trượt lọc trùng lặp Cooldown 15s và custom hooks (`useWebSocket`, `useAudioAlert`).
- Verification method: python -m pytest backend/tests/test_engine.py
- Parallelizable: yes
- Write scope: backend/ai/, frontend/src/hooks/
- Wave: 1
- Status: needs-revision

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
- Linked requirements: REQ-002, CR-001, CR-002, CR-007
- Capability: frontend-implementation
- Dependencies: TASK-007, TASK-008
- Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md
- Outputs: frontend/src/pages/AreaSecurityDashboard.tsx
- Completion gate: Trang Bãi kiểm render stream BAI-KIEM, consume metadata lane, hỗ trợ debug bbox/threshold CR-007 khi cần và giữ event/alert lane tách biệt.
- Verification method: npm --prefix frontend run build
- Parallelizable: yes
- Write scope: frontend/src/pages/AreaSecurityDashboard.tsx
- Wave: 1
- Status: in-review

### Wave 2 (Zone Settings & AI Chatbot)

#### TASK-012 Triển khai Tab 3 — Zone & Tag Settings (SVG Canvas & BBox Tool)
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-005, REQ-006, REQ-007, CR-001, CR-002
- Capability: frontend-implementation
- Dependencies: TASK-006, TASK-008
- Inputs: docs/contracts/API-FOUNDATION.md, docs/contracts/UI-UX-FOUNDATION.md
- Outputs: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/components/zone/
- Completion gate: Trang Cài đặt tích hợp SVG Canvas Polygon Editor 4 thao tác kéo thả, bảng gán nhãn Xe quen/Xe lạ 1-click và Dataset BBox Labeling Tool kèm video scrubber.
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
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, CR-001, CR-002, CR-007
- Capability: verify-feature
- Dependencies: TASK-009, TASK-010, TASK-012, TASK-013, TASK-014
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md
- Outputs: docs/reports/e2e-verification-report.md
- Completion gate: Nghiệm thu toàn bộ 4 tab chính, nhận diện mượt mà với 8 loại đối tượng và nhãn Xe quen/Xe lạ, trích xuất đúng 10s MP4 clip và phát còi bíp Mức 3.
- Verification method: python -m pytest tests/e2e/test_full_system.py
- Parallelizable: no
- Write scope: docs/reports/
- Wave: 3
- Status: needs-revision

### Wave 4 (CR-003 Area Metadata Refactor)

#### TASK-016 Thiết kế Contract Realtime Metadata cho Area Monitoring
- Task type: feature-design
- Scope: feature
- Module: api-gateway
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Capability: api-design
- Dependencies: TASK-010, TASK-014
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Outputs: .delivery/tasks/TASK-016/API-CONTRACT.md, .delivery/tasks/TASK-016/TASK-RESULT.md
- Completion gate: Xác định được contract metadata lane tách biệt với event lane, payload schema, versioning zone cache, và kỳ vọng tương thích ngược.
- Verification method: python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-016 --scope feature
- Parallelizable: yes
- Write scope: .delivery/tasks/TASK-016/
- Wave: 4
- Status: complete

#### TASK-017 Backend Area Metadata Lane và Zone Cache
- Task type: implementation
- Scope: feature
- Module: ai-vision-pipeline
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Capability: backend-implementation
- Dependencies: TASK-016
- Inputs: .delivery/ARCHITECTURE.md, .delivery/tasks/TASK-016/API-CONTRACT.md, backend/app/api/v1/events.py, backend/app/api/v1/zones.py, backend/app/api/v1/websocket.py, backend/app/services/video_stream.py, backend/app/services/vision_pipeline.py, backend/database/repository.py
- Outputs: backend/app/services/zone_cache.py, backend/app/services/area_metadata.py, backend runtime updates under backend/app/api/v1/ and backend/app/services/, backend tests, .delivery/tasks/TASK-017/TASK-RESULT.md
- Completion gate: Frame loop area monitoring không đọc DB mỗi frame; zone rules được lấy từ in-memory cache theo `camera_id`; metadata realtime và event persistence được tách lane rõ ràng.
- Verification method: python -m pytest backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py backend/tests/test_gate_zones.py -q
- Parallelizable: yes
- Write scope: backend/app/, backend/tests/, .delivery/tasks/TASK-017/
- Wave: 4
- Status: needs-revision

#### TASK-018 Frontend Area Dashboard consume Realtime Metadata Riêng
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-002, REQ-005, REQ-009, CR-003
- Capability: frontend-implementation
- Dependencies: TASK-016, TASK-017
- Inputs: .delivery/tasks/TASK-016/API-CONTRACT.md, .delivery/tasks/TASK-017/TASK-RESULT.md, frontend/src/pages/AreaSecurityDashboard.tsx, frontend/src/services/api.ts, frontend/src/services/websocket.ts, frontend/src/hooks/useWebSocket.ts, frontend/src/types/index.ts, frontend/src/context/AppContext.tsx
- Outputs: frontend metadata-lane integration updates under frontend/src/, production verification evidence, .delivery/tasks/TASK-018/TASK-RESULT.md
- Completion gate: UI area monitoring không cần polling detections/events để cập nhật metadata mỗi frame; video stream renderer vẫn là lane tách biệt.
- Verification method: npm --prefix frontend run lint && npx --prefix frontend tsc --noEmit
- Parallelizable: yes
- Write scope: frontend/src/, .delivery/tasks/TASK-018/
- Wave: 4
- Status: complete

### Wave 5 (CR-003 Verification & Bug Follow-up)

#### TASK-019 Verification cho CR-003 Realtime Area Metadata
- Task type: verification
- Scope: global
- Module: none
- Linked requirements: REQ-002, REQ-004, REQ-005, REQ-009, CR-003
- Capability: verify-feature
- Dependencies: TASK-016, TASK-017, TASK-018
- Inputs: .delivery/tasks/TASK-016/API-CONTRACT.md, .delivery/tasks/TASK-017/TASK-RESULT.md, .delivery/tasks/TASK-018/TASK-RESULT.md, backend/frontend implementation under backend/app/ and frontend/src/
- Outputs: .delivery/tasks/TASK-019/TEST-REPORT.md, .delivery/tasks/TASK-019/TASK-RESULT.md, bug records if verification fails
- Completion gate: Xác minh area metadata stream cập nhật realtime, hot path không đọc DB mỗi frame, và compatibility với event/alert flows được giữ vững.
- Verification method: python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-019
- Parallelizable: no
- Write scope: .delivery/tasks/TASK-019/
- Wave: 5
- Status: needs-revision

## Phase 4 — CR-004 Real Object Labeling Flow

- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_dataset_object_labeling.py backend/tests/test_dataset_zone_sync.py -q && npm --prefix frontend run build

### Wave 1 (Database & Storage Design)

#### TASK-020 Thiết kế DB/Storage cho Object Labeling Thật
- Task type: feature-design
- Scope: feature
- Module: database-storage
- Linked requirements: REQ-005, REQ-007, CR-004
- Capability: database-design
- Dependencies: TASK-019
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/changes/CR-004/CHANGE-IMPACT.md, docs/contracts/db/schema.sql, backend/database/models.py, backend/database/repository.py
- Outputs: .delivery/tasks/TASK-020/DATABASE-DESIGN.md, .delivery/tasks/TASK-020/TASK-RESULT.md
- Completion gate: Xác định contract dữ liệu và storage business-level cho media import thật, metadata source/frame, bbox samples, nhãn hệ thống, nhãn custom, soft delete/restore, uniqueness tên nhãn và sample_count mà chưa sửa schema production.
- Verification method: python D:\Skill\SKILLs\design-database\scripts\validate_database_design.py D:\Hilab\Project34 TASK-020
- Parallelizable: no
- Parallel-safety notes: Wave 1 tuần tự vì mọi quyết định DB/storage và migration direction phải chốt trước API/backend; không task nào khác trong phase được sửa schema ở wave này.
- Write scope: .delivery/tasks/TASK-020/
- Wave: 1
- Status: planned

### Wave 2 (API & UI/UX Feature Contracts)

#### TASK-021 Thiết kế API Upload/Source/Label/Sample/Frame/Sync
- Task type: feature-design
- Scope: feature
- Module: api-gateway
- Linked requirements: REQ-005, REQ-007, CR-004
- Capability: api-design
- Dependencies: TASK-020
- Inputs: .delivery/REQUIREMENTS.md, .delivery/tasks/TASK-020/DATABASE-DESIGN.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, backend/app/api/v1/dataset.py, frontend/src/services/api.ts
- Outputs: .delivery/tasks/TASK-021/API-CONTRACT.md, .delivery/tasks/TASK-021/TASK-RESULT.md
- Completion gate: Thiết kế xong API feature contract cho upload/import media, dataset sources, custom label CRUD/soft delete/restore, bbox sample CRUD, video frame retrieval và sync zone rules, gồm schema request/response đủ để backend/frontend triển khai sau.
- Verification method: python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-021 --scope feature
- Parallelizable: yes
- Parallel-safety notes: Chỉ ghi artifact design riêng của TASK-021; không cập nhật `.delivery/API-CONTRACT.md` hoặc docs/contracts/api trong bước này.
- Write scope: .delivery/tasks/TASK-021/
- Wave: 2
- Status: planned

#### TASK-022 Thiết kế UI/UX cho Cài đặt > Nhãn đối tượng
- Task type: feature-design
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-005, REQ-007, CR-004
- Capability: ui-ux-design
- Dependencies: TASK-020
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/tasks/TASK-020/DATABASE-DESIGN.md, frontend/src/pages/ZoneTagSettings.tsx, frontend/src/context/AppContext.tsx, frontend/src/components/zone/PolygonZoneEditor.tsx
- Outputs: .delivery/tasks/TASK-022/UI-UX-CONTRACT.md, .delivery/tasks/TASK-022/TASK-RESULT.md
- Completion gate: Thiết kế xong workflow UI cho import media thật, scrub frame video, bbox create/edit/delete, label system/custom states, confirm delete, restore, batch validation errors và sync feedback mà chưa sửa frontend production.
- Verification method: python D:\Skill\SKILLs\design-ui-ux\scripts\validate_ui_ux_design.py D:\Hilab\Project34 TASK-022
- Parallelizable: yes
- Parallel-safety notes: Có thể chạy song song với TASK-021 vì chỉ ghi artifact riêng và dùng cùng DATABASE-DESIGN làm input.
- Write scope: .delivery/tasks/TASK-022/
- Wave: 2
- Status: planned

### Wave 3 (Backend Implementation)

#### TASK-023 Backend Object Labeling Thật theo Design đã Duyệt
- Task type: implementation
- Scope: feature
- Module: api-gateway
- Linked requirements: REQ-005, REQ-007, CR-004
- Capability: backend-implementation
- Dependencies: TASK-020, TASK-021
- Inputs: .delivery/tasks/TASK-020/DATABASE-DESIGN.md, .delivery/tasks/TASK-021/API-CONTRACT.md, backend/app/api/v1/dataset.py, backend/database/models.py, backend/database/repository.py
- Outputs: backend dataset API/storage implementation, backend tests, .delivery/tasks/TASK-023/TASK-RESULT.md
- Completion gate: Backend lưu được media import và metadata, quản lý nhãn hệ thống/custom, lưu/tải/sửa/xóa bbox samples, soft delete/restore nhãn custom, validate batch atomically, sync custom labels vào zone rules mặc định `cấm`, và không yêu cầu AI realtime nhận diện class custom mới.
- Verification method: python -m pytest backend/tests/test_dataset_object_labeling.py backend/tests/test_dataset_zone_sync.py -q
- Parallelizable: no
- Parallel-safety notes: Chạy sau design DB/API đã duyệt; trong phase này không có task backend song song ghi cùng `backend/app/` hoặc `backend/database/`.
- Write scope: backend/app/api/v1/dataset.py, backend/database/, backend/tests/, .delivery/tasks/TASK-023/
- Wave: 3
- Status: planned

### Wave 4 (Frontend Implementation)

#### TASK-024 Frontend Cài đặt > Nhãn đối tượng theo Design đã Duyệt
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-005, REQ-007, CR-004
- Capability: frontend-implementation
- Dependencies: TASK-021, TASK-022, TASK-023
- Inputs: .delivery/tasks/TASK-021/API-CONTRACT.md, .delivery/tasks/TASK-022/UI-UX-CONTRACT.md, .delivery/tasks/TASK-023/TASK-RESULT.md, frontend/src/pages/ZoneTagSettings.tsx, frontend/src/context/AppContext.tsx, frontend/src/services/api.ts, frontend/src/types/index.ts
- Outputs: frontend object-labeling integration updates, frontend tests/build evidence, .delivery/tasks/TASK-024/TASK-RESULT.md
- Completion gate: UI `Nhãn đối tượng` dùng API thật thay mock/local state cho media source, labels và bbox samples; reload thấy dữ liệu persisted; xử lý confirm delete, restore, batch validation, sample edit và sync trạng thái zone rules theo acceptance CR-004.
- Verification method: npm --prefix frontend run build
- Parallelizable: no
- Parallel-safety notes: Chạy sau backend để kiểm thử flow thật; không song song với task khác ghi `frontend/src/`.
- Write scope: frontend/src/pages/ZoneTagSettings.tsx, frontend/src/context/AppContext.tsx, frontend/src/services/api.ts, frontend/src/types/, frontend/src/components/zone/, .delivery/tasks/TASK-024/
- Wave: 4
- Status: planned

### Wave 5 (CR-004 End-to-End Verification)

#### TASK-025 Verification End-to-End cho CR-004 Object Labeling
- Task type: verification
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-005, REQ-007, CR-004
- Capability: verify-feature
- Dependencies: TASK-020, TASK-021, TASK-022, TASK-023, TASK-024
- Inputs: .delivery/REQUIREMENTS.md, .delivery/tasks/TASK-020/DATABASE-DESIGN.md, .delivery/tasks/TASK-021/API-CONTRACT.md, .delivery/tasks/TASK-022/UI-UX-CONTRACT.md, .delivery/tasks/TASK-023/TASK-RESULT.md, .delivery/tasks/TASK-024/TASK-RESULT.md, backend/frontend implementation under backend/ and frontend/src/
- Outputs: .delivery/tasks/TASK-025/TEST-REPORT.md, .delivery/tasks/TASK-025/TASK-RESULT.md, bug records if verification fails
- Completion gate: Xác minh end-to-end import ảnh/video thật, chọn frame video, vẽ/sửa/xóa bbox, tạo/sửa/soft delete/restore nhãn custom, khóa nhãn hệ thống, reload persisted samples từ DB và sync zone rules mặc định `cấm`.
- Verification method: python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-025
- Parallelizable: no
- Parallel-safety notes: Verification chạy sau toàn bộ design và implementation của CR-004; không sửa production code.
- Write scope: .delivery/tasks/TASK-025/
- Wave: 5
- Status: planned

## Phase 5 — CR-005 Telegram Evidence Notification

- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py -q

### Wave 1 (Evidence Contract)

#### TASK-026 Thiết kế Contract Event/Alert Evidence cho Telegram CR-005
- Task type: feature-design
- Scope: feature
- Module: api-gateway
- Linked requirements: REQ-002, REQ-003, REQ-004, REQ-008, REQ-009, CR-005
- Capability: api-design
- Dependencies: TASK-016
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/changes/CR-005/CHANGE-IMPACT.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Outputs: .delivery/tasks/TASK-026/API-CONTRACT.md, .delivery/tasks/TASK-026/TASK-RESULT.md
- Completion gate: Thiết kế xong contract nghiệp vụ/API cho event vi phạm khu vực dùng chung giữa Event Feed, AI Assistant và Telegram, gồm thời gian vi phạm đúng, camera, zone, loại đối tượng, lý do vi phạm, clip 10s và trạng thái lỗi gửi Telegram mà chưa sửa production code.
- Verification method: python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-026 --scope feature
- Parallelizable: no
- Parallel-safety notes: Chạy sau TASK-016 để kế thừa metadata/event lane semantics; không cập nhật `.delivery/API-CONTRACT.md` hoặc docs/contracts/api trong task design riêng nếu chưa được phê duyệt.
- Write scope: .delivery/tasks/TASK-026/
- Wave: 1
- Status: planned

### Wave 2 (Backend Evidence Notification)

#### TASK-027 Backend Telegram Evidence Notification cho Vi phạm Khu vực
- Task type: implementation
- Scope: feature
- Module: alert-dispatcher
- Linked requirements: REQ-002, REQ-003, REQ-004, REQ-009, CR-005
- Capability: backend-implementation
- Dependencies: TASK-017, TASK-026
- Inputs: .delivery/tasks/TASK-026/API-CONTRACT.md, backend/app/services/event_manager.py, backend/app/services/alert_dispatcher.py, backend/app/services/vision_pipeline.py, backend/app/api/v1/websocket.py
- Outputs: backend alert/event implementation updates, backend tests, .delivery/tasks/TASK-027/TASK-RESULT.md
- Completion gate: Khi đối tượng thuộc danh sách cấm đi vào zone khu vực, backend chỉ gửi 1 Telegram cho event đầu tiên đã qua dedup/cooldown, gửi trực tiếp file video clip chứng cứ 10s kèm thời gian vi phạm đúng, camera, zone, loại đối tượng và lý do vi phạm; nếu Telegram lỗi thì event/clip vẫn lưu, UI vẫn cảnh báo và lỗi được ghi nhận.
- Verification method: python -m pytest backend/tests/test_alerts.py backend/tests/test_live_detections_event.py -q
- Parallelizable: no
- Parallel-safety notes: Không chạy song song với task khác ghi `backend/app/services/event_manager.py` hoặc `backend/app/services/alert_dispatcher.py`.
- Write scope: backend/app/services/, backend/app/api/v1/, backend/tests/, .delivery/tasks/TASK-027/
- Wave: 2
- Status: planned

### Wave 3 (CR-005 Verification)

#### TASK-028 Verification End-to-End cho CR-005 Telegram Evidence
- Task type: verification
- Scope: feature
- Module: alert-dispatcher
- Linked requirements: REQ-002, REQ-003, REQ-004, REQ-008, REQ-009, CR-005
- Capability: verify-feature
- Dependencies: TASK-026, TASK-027
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/tasks/TASK-026/API-CONTRACT.md, .delivery/tasks/TASK-027/TASK-RESULT.md, backend implementation under backend/app/
- Outputs: .delivery/tasks/TASK-028/TEST-REPORT.md, .delivery/tasks/TASK-028/TASK-RESULT.md, bug records if verification fails
- Completion gate: Xác minh end-to-end một vi phạm khu vực do đối tượng cấm đi vào zone tạo đúng 1 event/clip/Telegram trong cooldown; Telegram có đủ nội dung bắt buộc và gửi trực tiếp video 10s; metadata lane không tự kích hoạt Telegram; lỗi Telegram không chặn lưu event/clip hoặc cảnh báo UI.
- Verification method: python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-028
- Parallelizable: no
- Parallel-safety notes: Verification chạy sau toàn bộ design và implementation CR-005; không sửa production code.
- Write scope: .delivery/tasks/TASK-028/
- Wave: 3
- Status: planned

## Phase 6 — Gemini LLM Text-to-SQL cho AI Chatbot

- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_chatbot.py -q

### Wave 1 (Gemini Integration)

#### TASK-029 Tích hợp Google Gemini LLM Text-to-SQL cho AI Chatbot Assistant
- Task type: implementation
- Scope: feature
- Module: llm-qa-agent
- Linked requirements: REQ-008, CR-002
- Capability: backend-implementation
- Dependencies: TASK-013
- Inputs: .delivery/ADR/ADR-004-llm-text-to-sql-with-fallback.md, .delivery/tasks/TASK-013/TASK-RESULT.md, .delivery/tasks/TASK-013/BUG-001.md, backend/app/services/qa_agent.py, backend/app/core/config.py, backend/app/models/schemas/assistant.py, backend/database/models.py
- Outputs: backend/app/services/qa_agent.py (nhánh LLM), backend/app/core/config.py, backend/tests/test_chatbot.py, .env.example, requirements.txt, .delivery/tasks/TASK-029/TASK-RESULT.md
- Completion gate: Gemini dịch câu hỏi tiếng Việt thành SQL và SQL đó được thực thi thật trên SQLite; chốt an toàn `_FORBIDDEN_SQL` vẫn chặn mọi câu lệnh không phải `SELECT`; khi thiếu key, thiếu thư viện, Gemini lỗi hoặc trả SQL không hợp lệ thì tự động fallback sang Rule Engine; toàn bộ test chạy được không cần khóa API thật.
- Verification method: python -m pytest backend/tests/test_chatbot.py -q
- Parallelizable: no
- Parallel-safety notes: Ghi cùng `backend/app/services/qa_agent.py` và `backend/tests/test_chatbot.py` với TASK-013; chạy sau khi TASK-013 đã approved.
- Write scope: backend/app/services/qa_agent.py, backend/app/core/config.py, backend/tests/test_chatbot.py, .env.example, requirements.txt, .delivery/tasks/TASK-029/
- Wave: 1
- Status: planned

## Phase 7 — CR-007 Area Monitoring Detection & BBox Reliability

- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py -q && npm --prefix frontend run build

### Wave 1 (Contract and Runtime Semantics)

#### TASK-030 CR-007 Contract cho Area Detection, BBox Debug và Zone Evaluation
- Task type: feature-design
- Scope: feature
- Module: api-gateway
- Linked requirements: REQ-002, REQ-004, REQ-009, CR-007
- Capability: api-design
- Dependencies: TASK-016
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md, .delivery/API-CONTRACT.md, .delivery/changes/CR-007/CHANGE-IMPACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Outputs: .delivery/tasks/TASK-030/API-CONTRACT.md, .delivery/tasks/TASK-030/TASK-RESULT.md
- Completion gate: Contract xác định rõ YOLOv11s finetune cho `BAI-KIEM`, display/debug threshold tách khỏi event/alert threshold, `show_static_containers`, metadata fields additive, class-aware zone evaluation method/ratio và `track_id` optional/future-compatible.
- Verification method: python -m json.tool docs/contracts/api/api-schema.json && python -m json.tool docs/contracts/api/websocket-events.json
- Parallelizable: no
- Parallel-safety notes: Thiết kế này cập nhật contract runtime khu vực; không thay đổi LPR/GATE-01 ngoài regression boundary.
- Write scope: .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json, .delivery/tasks/TASK-030/
- Wave: 1
- Status: planned

### Wave 2 (Backend and Frontend Implementation)

#### TASK-031 CR-007 Backend Detection Threshold, Class Mapping và Zone Evaluator
- Task type: implementation
- Scope: feature
- Module: ai-vision-pipeline
- Linked requirements: REQ-002, REQ-004, REQ-009, CR-007
- Capability: backend-implementation
- Dependencies: TASK-030, TASK-017
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md, .delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md, .delivery/API-CONTRACT.md, backend/app/services/vision_pipeline.py, backend/app/services/video_stream.py, backend/app/services/area_metadata.py, backend/app/api/v1/events.py
- Outputs: backend area detection runtime updates, backend tests, .delivery/tasks/TASK-031/TASK-RESULT.md
- Completion gate: Area Monitoring dùng YOLOv11s finetune, inference threshold thấp và application/per-class threshold tách biệt; class mapping giữ `raw_class`/`canonical_class`; zone evaluation dùng bottom-center/footprint overlap/container overlap ratio; MJPEG có `show_static_containers`; metadata giữ backward compatibility.
- Verification method: python -m pytest backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py -q
- Parallelizable: no
- Parallel-safety notes: Không triển khai ByteTrack/BoT-SORT đầy đủ trong CR-007; chỉ trả/giữ `track_id` khi runtime đã có. Không sửa business flow LPR/GATE-01 ngoài regression.
- Write scope: backend/app/services/vision_pipeline.py, backend/app/services/video_stream.py, backend/app/services/area_metadata.py, backend/app/api/v1/events.py, backend/tests/, .delivery/tasks/TASK-031/
- Wave: 2
- Status: planned

#### TASK-032 CR-007 Frontend Debug Controls và Type Surface cho Area Dashboard
- Task type: implementation
- Scope: feature
- Module: web-ui
- Linked requirements: REQ-002, REQ-004, REQ-009, CR-007
- Capability: frontend-implementation
- Dependencies: TASK-030, TASK-031
- Inputs: .delivery/API-CONTRACT.md, frontend/src/pages/AreaSecurityDashboard.tsx, frontend/src/services/api.ts, frontend/src/types/
- Outputs: frontend Area Dashboard/type updates, .delivery/tasks/TASK-032/TASK-RESULT.md
- Completion gate: Frontend type surface chấp nhận metadata additive CR-007; Area Dashboard có thể truyền `conf_threshold` và `show_static_containers` cho debug mà không đổi layout nghiệp vụ chính hoặc event/alert behavior.
- Verification method: npx --prefix frontend tsc --noEmit && npm --prefix frontend run build
- Parallelizable: no
- Parallel-safety notes: Không thay đổi Gate Dashboard hoặc LPR flow; debug controls chỉ áp dụng Area Dashboard.
- Write scope: frontend/src/pages/AreaSecurityDashboard.tsx, frontend/src/services/api.ts, frontend/src/types/, .delivery/tasks/TASK-032/
- Wave: 2
- Status: planned

### Wave 3 (CR-007 Verification)

#### TASK-033 CR-007 Verification và Regression Không đổi LPR/GATE-01
- Task type: verification
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-004, REQ-009, CR-007
- Capability: verify-feature
- Dependencies: TASK-031, TASK-032
- Inputs: .delivery/REQUIREMENTS.md, .delivery/API-CONTRACT.md, .delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md, .delivery/changes/CR-007/CHANGE-IMPACT.md, backend/frontend implementation under backend/app/ and frontend/src/
- Outputs: .delivery/tasks/TASK-033/TEST-REPORT.md, .delivery/tasks/TASK-033/TASK-RESULT.md, bug records if verification fails
- Completion gate: Xác minh bbox display threshold không tự sinh event/alert, class-aware zone evaluation đúng theo nhóm đối tượng, container bbox debug bật/tắt được, metadata additive tương thích ngược, stream vẫn đạt FPS >= 5 và LPR/GATE-01 không đổi ngoài regression evidence.
- Verification method: python -m pytest backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py -q && npm --prefix frontend run build
- Parallelizable: no
- Parallel-safety notes: Verification không sửa production code và không mở rộng tracking persistence.
- Write scope: .delivery/tasks/TASK-033/
- Wave: 3
- Status: planned


---

## 4. Bản đồ Bao phủ Yêu cầu (Coverage Map)

## Coverage Map
- REQ-001 -> TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-009, TASK-015, TASK-033
- REQ-002 -> TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-010, TASK-015, TASK-016, TASK-017, TASK-018, TASK-019, TASK-026, TASK-027, TASK-028, TASK-030, TASK-031, TASK-032, TASK-033
- REQ-003 -> TASK-002, TASK-004, TASK-008, TASK-014, TASK-015, TASK-026, TASK-027, TASK-028
- REQ-004 -> TASK-007, TASK-015, TASK-016, TASK-017, TASK-019, TASK-026, TASK-027, TASK-028, TASK-030, TASK-031, TASK-032, TASK-033
- REQ-005 -> TASK-002, TASK-004, TASK-005, TASK-012, TASK-015, TASK-016, TASK-017, TASK-018, TASK-019, TASK-020, TASK-021, TASK-022, TASK-023, TASK-024, TASK-025
- REQ-006 -> TASK-003, TASK-006, TASK-012, TASK-015
- REQ-007 -> TASK-007, TASK-012, TASK-015, TASK-020, TASK-021, TASK-022, TASK-023, TASK-024, TASK-025
- REQ-008 -> TASK-002, TASK-013, TASK-015, TASK-026, TASK-028, TASK-029
- REQ-009 -> TASK-002, TASK-008, TASK-014, TASK-015, TASK-016, TASK-017, TASK-018, TASK-019, TASK-026, TASK-027, TASK-028, TASK-030, TASK-031, TASK-032, TASK-033
- CR-001 -> TASK-002, TASK-005, TASK-006, TASK-007, TASK-010, TASK-012, TASK-015
- CR-002 -> TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-012, TASK-013, TASK-014, TASK-015, TASK-029
- CR-003 -> TASK-016, TASK-017, TASK-018, TASK-019
- CR-004 -> TASK-020, TASK-021, TASK-022, TASK-023, TASK-024, TASK-025
- CR-005 -> TASK-026, TASK-027, TASK-028
- CR-007 -> TASK-001, TASK-002, TASK-010, TASK-015, TASK-030, TASK-031, TASK-032, TASK-033
- Gemini LLM (REQ-008) -> TASK-029

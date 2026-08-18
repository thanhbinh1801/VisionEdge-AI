---
artifact: MASTER-PLAN
version: 1.6.0
owner: Delivery Lead & Product Owner
status: approved
updated_at: "2026-08-18T14:16:00+07:00"
depends_on:
  - REQUIREMENTS.md
  - ARCHITECTURE.md
  - TECHNICAL-RISKS.md
  - ADR-001
  - ADR-002
  - ADR-003
  - ADR-004
  - ADR-005
---

# Kế hoạch Triển khai Dự án Giám sát Camera AI (SentriAI Mini)

## 1. Phân chia Nhóm & Chiến lược Triển khai Theo Phân hệ Nghiệp vụ (Feature-Module Stream Strategy)

Dự án được phân chia trách nhiệm theo **Phân hệ Nghiệp vụ (Feature Modules)** kết hợp phân công người phụ trách cụ thể (`Assigned to`) ở từng nhiệm vụ. Giai đoạn **Nền tảng dùng chung (Shared Core & Foundation Design)** được thực hiện tại Phase 1 để đảm bảo tính độc lập và khả năng phát triển song song tối đa giữa 2 Lập trình viên ngay từ ngày đầu tiên:

- **Giai đoạn Shared Core + Foundation Design (Phase 1 Wave 1 & Wave 2)**:
  - `TASK-001` (Benchmark AI Model - Person A) và `TASK-005` (UI/UX Design System Contract - Person B) cùng được xếp tại Wave 1 của Phase 1, chạy song song tuyệt đối ngay từ ngày bắt đầu dự án.
  - `TASK-002` & `TASK-003` (API Contracts, DB Schema & Seed Data Foundation): Person A phụ trách thiết kế các hợp đồng spec trong `docs/contracts/`.
  - `TASK-004` (Custom Label Embedding Architecture & ADR-005): Person B phụ trách thiết kế văn bản ADR-005 trong `.delivery/`.
  - `TASK-006` (Shared Database Access Layer): Person A phụ trách triển khai CSDL backend SQLite tại Wave 2 từ các hợp đồng SQL đã duyệt.
  - `TASK-007` (Zone Evaluator, Configurable Cooldown & Clip Slicer): Person B phụ trách các tiện ích engine dùng chung.
  - `TASK-008` (Cross-Cutting Settings UI): Person B phụ trách trọn gói module Settings UI (`zone_editor.js`, `vehicle_tagger.js`, `custom_labeler.js`).

- **Phân hệ 1 — Module Cổng LPR (Person A phụ trách)**:
  - **Phạm vi ghi file**: `backend/ai/gate_stream.py`, `backend/ai/lpr_ocr.py`, `backend/api/gate_routes.py`, `frontend/src/monitoring/gate_dashboard.js`, `frontend/src/monitoring/plate_correction_modal.js`.
  - **Nhiệm vụ chính**: Luồng stream video Cổng (`GATE-01`), nhận diện LPR biển số xe, fallback sửa tay biển số khi confidence < 85%, API Cổng và Màn hình Giám sát Cổng & KPI LPR.

- **Phân hệ 2 — Module Giám sát Khu vực / Bãi kiểm (Person B phụ trách)**:
  - **Phạm vi ghi file**: `backend/ai/area_stream.py`, `backend/ai/object_classifier.py`, `backend/api/area_routes.py`, `frontend/src/monitoring/area_dashboard.js`.
  - **Nhiệm vụ chính**: Luồng stream video Bãi kiểm (`BAI-KIEM`), phân loại đối tượng đa lớp (người, container, xe tải, xe nâng, xe cẩu, xe con, xe máy, xe đạp) theo vị trí tâm trong Zone, so khớp quy tắc cấm/cho phép, API Bãi kiểm và Màn hình Giám sát Khu vực & KPI Bãi kiểm.

- **Phân hệ 3 — AI Assistant Q&A & Web Chat Integration (Phát triển song song tại Wave 1 Phase 2)**:
  - **Phân chia Task**: Tách thành `TASK-011a` (Backend Text-to-SQL Engine), `TASK-011b` (Chatbot UI Frontend) và `TASK-011c` (Multi-channel Alert Dispatcher).
  - **Người phụ trách**: Person A phụ trách `TASK-011a` và `TASK-011b`; Person B phụ trách `TASK-011c`.
  - **Lưu ý Tiến độ**: Sử dụng dữ liệu seed/mock event sẵn có trong CSDL từ Phase 1 (`seed_events.sql`) để lập trình và test Text-to-SQL / Chat UI ngay tại Wave 1 của Phase 2 mà không phải chờ 2 module Cổng & Khu vực hoàn thành 100%.

- **Chiến lược UI & Tiêu chí Hoàn thành theo RFP**:
  - Giao diện xây dựng đúng luồng nghiệp vụ và bố cục chính theo Prototype `Intern-LPR-Gate.dc.html`, không bắt buộc sao chép pixel-perfect theo đúng tinh thần hướng dẫn của RFP bài tập.

---

## 2. Danh sách Phase & Các Nhóm Nhiệm vụ (Phases & Task Graph)

## Phase 1 — Shared Core + Foundation Design
- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_model_benchmark.py && python -m pytest backend/tests/test_foundation.py

### Wave 1 (Contracts, DB Schema, AI Model Benchmark & UI Foundation)

#### TASK-001: Pretrained AI Model Benchmarking
- Task type: ai-model-benchmark
- Scope: global
- Module: ai-vision-pipeline
- Linked requirements: REQ-001, REQ-002
- Linked change requests: none
- Dependencies: none
- Assigned to: Person A
- Required capability: backend-implementation
- Inputs: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`, `data/sample_videos/GATE-01.mp4`, `data/sample_videos/BAI-KIEM.mp4`
- Outputs: `docs/reports/ai-model-benchmark.md`
- Write scope: docs/reports/
- Wave: 1
- Completion gate: Chốt bộ mô hình YOLOv8 + EasyOCR/PaddleOCR đạt FPS >= 5 trên 2 video mẫu được cung cấp sẵn tại `data/sample_videos/`.
- Verification method: Chạy script benchmark `python -m pytest backend/tests/test_model_benchmark.py` thành công.
- Parallel-safety notes: Chạy song song độc lập tại Wave 1 cùng TASK-005 (Person B).
- Status: ready

#### TASK-002: Global REST API & WebSocket Event Schemas Foundation
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-009
- Linked change requests: none
- Dependencies: TASK-001
- Assigned to: Person A
- Required capability: api-foundation-design
- Inputs: `.delivery/REQUIREMENTS.md`, `.delivery/ARCHITECTURE.md`
- Outputs: `docs/contracts/api-schema.json`, `docs/contracts/websocket-events.json`
- Write scope: docs/contracts/api-schema.json, docs/contracts/websocket-events.json
- Wave: 1
- Completion gate: Định nghĩa hoàn chỉnh OpenAPI Spec (gồm endpoint `PATCH /api/events/{id}/correct-plate`) và JSON WebSocket Event Schemas dưới dạng contract artifacts trong `docs/contracts/`.
- Verification method: Kiểm tra hợp lệ JSON Schema bằng `python -m json.tool docs/contracts/api-schema.json`.
- Parallel-safety notes: Cần giữ dependency với TASK-001 để chốt cấu trúc trường dữ liệu output từ AI Model vào hợp đồng.
- Status: ready

#### TASK-003: Shared Database Schema, Seed Data & Migration Foundation
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-006, REQ-007, REQ-008, REQ-009
- Linked change requests: none
- Dependencies: TASK-001
- Assigned to: Person A
- Required capability: database-design
- Inputs: `.delivery/DOMAIN-MODEL.md`, `.delivery/ARCHITECTURE.md`
- Outputs: `docs/contracts/db-schema.sql`, `docs/contracts/seed_events.sql`, `docs/contracts/db-contract.md`
- Write scope: docs/contracts/db-schema.sql, docs/contracts/seed_events.sql, docs/contracts/db-contract.md
- Wave: 1
- Completion gate: DDL đầy đủ CSDL SQLite (Camera, Zone, Vehicle, Event, CustomLabel) và bộ dữ liệu seed_events mẫu cho QA Agent tại folder hợp đồng thiết kế.
- Verification method: Kiểm tra hợp lệ file DDL và Seed SQL bằng `sqlite3 :memory: < docs/contracts/db-schema.sql`.
- Parallel-safety notes: Cần giữ dependency với TASK-001. Chỉ tạo contract artifacts, không ghi mã nguồn `backend/db/`.
- Status: ready

#### TASK-004: Custom Label Embedding Architecture & ADR-005 Decision
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-007
- Linked change requests: none
- Dependencies: TASK-001
- Assigned to: Person B
- Required capability: architecture-design
- Inputs: `.delivery/ARCHITECTURE.md`
- Outputs: `.delivery/ADR-005-Custom-Label-Matching-Architecture.md`
- Write scope: .delivery/ADR-005-Custom-Label-Matching-Architecture.md
- Wave: 1
- Completion gate: Thống nhất và ban hành ADR-005 quy định cơ chế Few-shot Embedding Vector Matching (dùng Cosine Distance threshold) để phân loại mẫu custom label mà không cần fine-tune YOLO.
- Verification method: Kiểm tra sự tồn tại và nội dung của văn bản ADR-005.
- Parallel-safety notes: Cần giữ dependency với TASK-001 để chọn backbone feature map thích hợp trong ADR-005.
- Status: ready

#### TASK-005: UI/UX Design System Contract & Component Layout Standard
- Task type: foundation-design
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-005, REQ-006, REQ-007, REQ-008
- Linked change requests: none
- Dependencies: none
- Assigned to: Person B
- Required capability: ui-ux-foundation-design
- Inputs: `Prototype/Intern-LPR-Gate.dc.html`, `.delivery/REQUIREMENTS.md`
- Outputs: `docs/contracts/ui-design-contract.md`
- Write scope: docs/contracts/ui-design-contract.md
- Wave: 1
- Completion gate: Quy định token UI, bố cục 4 tab chính và quy tắc thiết kế UI (đúng luồng nghiệp vụ theo Prototype, không bắt buộc pixel-perfect).
- Verification method: Kiểm tra văn bản thiết kế UI contract.
- Parallel-safety notes: Không phụ thuộc TASK-001. Chạy song song độc lập ngay tại Wave 1 cùng TASK-001.
- Status: ready

### Wave 2 (Shared Core Implementation & Cross-Cutting Settings UI)

#### TASK-006: Shared Database Access Layer & Base Storage Initializer
- Task type: backend-implementation
- Scope: module
- Module: database-storage
- Linked requirements: REQ-001, REQ-002, REQ-006, REQ-007
- Linked change requests: none
- Dependencies: TASK-003
- Assigned to: Person A
- Required capability: backend-implementation
- Inputs: `docs/contracts/db-schema.sql`, `docs/contracts/seed_events.sql`
- Outputs: `backend/db/schema.sql`, `backend/db/seed_events.sql`, `backend/db/connection.py`, `backend/db/models.py`, `backend/db/crud.py`
- Write scope: backend/db/
- Wave: 2
- Completion gate: Khởi tạo ORM/CRUD kết nối SQLite, chuyển giao schema.sql và seed_events.sql từ docs/contracts/ sang backend/db/, nạp dữ liệu thử nghiệm.
- Verification method: Chạy unit test `python -m pytest backend/tests/test_db_crud.py` thành công.
- Parallel-safety notes: Cơ sở DB chung dùng cho cả Person A & Person B.
- Status: ready

#### TASK-007: Shared Vision & Event Utilities Engine (Zone Evaluator, Configurable Cooldown & 10s Slicer)
- Task type: backend-implementation
- Scope: module
- Module: shared-engine-utils
- Linked requirements: REQ-002, REQ-003, REQ-004, REQ-008
- Linked change requests: none
- Dependencies: TASK-002, TASK-003
- Assigned to: Person B
- Required capability: backend-implementation
- Inputs: `docs/contracts/api-schema.json`
- Outputs: `backend/ai/zone_evaluator.py`, `backend/events/cooldown_manager.py`, `backend/events/clip_slicer.py`
- Write scope: backend/ai/zone_evaluator.py, backend/events/cooldown_manager.py, backend/events/clip_slicer.py
- Wave: 2
- Completion gate: Hàm Point-in-Polygon xử lý tâm BBox, Cooldown Engine dạng tham số cấu hình linh hoạt (đọc từ `config.py` / `.env`, giá trị khởi điểm 10-15s, đề xuất update backend/config.py qua proposed shared file changes) và Clip Slicer 10s cứng theo RFP.
- Verification method: Chạy unit test `python -m pytest backend/tests/test_shared_utils.py` đạt 100% pass.
- Parallel-safety notes: Đóng gói tiện ích core dùng chung trước khi chia module. Shared config được merge bởi Orchestrator.
- Status: ready

#### TASK-008: Cross-Cutting Settings UI (Interactive Zone Polygon Editor & Custom Dataset Labeling Tool)
- Task type: frontend-implementation
- Scope: module
- Module: web-ui
- Linked requirements: REQ-005, REQ-006, REQ-007
- Linked change requests: none
- Dependencies: TASK-002, TASK-004, TASK-005
- Assigned to: Person B
- Required capability: frontend-implementation
- Inputs: `docs/contracts/ui-design-contract.md`, `Prototype/Intern-LPR-Gate.dc.html`
- Outputs: `frontend/src/settings/zone_editor.js`, `frontend/src/settings/vehicle_tagger.js`, `frontend/src/settings/custom_labeler.js`
- Write scope: frontend/src/settings/
- Wave: 2
- Completion gate: Vẽ zone đa giác SVG 2 chế độ Chọn/Vẽ kéo thả đỉnh mượt mà, gán nhãn xe quen/lạ 1-click và tool khoanh BBox custom dataset có timeline scrubber.
- Verification method: Mở trình duyệt kiểm tra thao tác vẽ zone và gán nhãn dataset.
- Parallel-safety notes: Module frontend settings độc lập với các module backend cùng wave, tránh tranh chấp write scope.
- Status: ready

---

## Phase 2 — Parallel Feature Modules Implementation
- Gate: integration-check
- Integration commands: python -m pytest backend/tests/test_modules_integration.py

### Wave 1 (Parallel Feature Modules & QA Agent Development)

#### TASK-009: LPR Gate Monitoring Module (Person A)
- Task type: feature-implementation
- Scope: module
- Module: lpr-gate-module
- Linked requirements: REQ-001, REQ-003
- Linked change requests: none
- Dependencies: TASK-006, TASK-007
- Assigned to: Person A
- Required capability: backend-implementation, frontend-implementation
- Inputs: `backend/db/crud.py`, `backend/events/cooldown_manager.py`, `docs/contracts/ui-design-contract.md`
- Outputs: `backend/ai/gate_stream.py`, `backend/ai/lpr_ocr.py`, `backend/api/gate_routes.py`, `frontend/src/monitoring/gate_dashboard.js`, `frontend/src/monitoring/plate_correction_modal.js`
- Write scope: backend/ai/gate_stream.py, backend/ai/lpr_ocr.py, backend/api/gate_routes.py, frontend/src/monitoring/gate_dashboard.js, frontend/src/monitoring/plate_correction_modal.js
- Wave: 1
- Completion gate: Xử lý video stream `GATE-01`, LPR OCR đọc biển số xe, REST API Cổng, Popover sửa tay biển số khi confidence < 85%, và Giao diện Giám sát Cổng kèm 4 thẻ KPI LPR (đúng luồng nghiệp vụ Prototype).
- Verification method: Chạy stream test Cổng, kiểm tra gọi API `PATCH /api/events/{id}/correct-plate` và hiển thị UI Cổng.
- Parallel-safety notes: Person A chịu trách nhiệm trọn gói Module Cổng (từ capture, OCR, API đến UI Cổng).
- Status: ready

#### TASK-010: Area Zone Security Monitoring Module (Person B)
- Task type: feature-implementation
- Scope: module
- Module: area-monitoring-module
- Linked requirements: REQ-002, REQ-003
- Linked change requests: none
- Dependencies: TASK-004, TASK-006, TASK-007
- Assigned to: Person B
- Required capability: backend-implementation, frontend-implementation
- Inputs: `backend/db/crud.py`, `backend/ai/zone_evaluator.py`, `.delivery/ADR-005-Custom-Label-Matching-Architecture.md`
- Outputs: `backend/ai/area_stream.py`, `backend/ai/object_classifier.py`, `backend/api/area_routes.py`, `frontend/src/monitoring/area_dashboard.js`
- Write scope: backend/ai/area_stream.py, backend/ai/object_classifier.py, backend/api/area_routes.py, frontend/src/monitoring/area_dashboard.js
- Wave: 1
- Completion gate: Xử lý video stream `BAI-KIEM`, phân loại đối tượng đa lớp (người, container, xe tải, xe nâng, xe cẩu...) so khớp với quy tắc zone đa giác, REST API Bãi kiểm và Giao diện Giám sát Khu vực kèm 4 thẻ KPI Bãi kiểm (đúng luồng nghiệp vụ Prototype).
- Verification method: Chạy stream test Bãi kiểm, xác nhận phát hiện vi phạm quy tắc zone và hiển thị UI Bãi kiểm.
- Parallel-safety notes: Person B chịu trách nhiệm trọn gói Module Khu vực (từ capture, phân loại, API đến UI Bãi kiểm).
- Status: ready

#### TASK-011a: AI Event Q&A Backend Engine (Text-to-SQL + Fallback Rule Matcher)
- Task type: feature-implementation
- Scope: module
- Module: llm-qa-agent
- Linked requirements: REQ-008
- Linked change requests: none
- Dependencies: TASK-006, TASK-007
- Assigned to: Person A
- Required capability: backend-implementation
- Inputs: `docs/contracts/api-schema.json`, `backend/db/crud.py`, `docs/contracts/seed_events.sql`
- Outputs: `backend/api/qa_agent.py`, `backend/api/qa_routes.py`, `backend/api/websocket_qa.py`
- Write scope: backend/api/qa_agent.py, backend/api/qa_routes.py, backend/api/websocket_qa.py
- Wave: 1
- Completion gate: Xử lý câu hỏi tự nhiên tiếng Việt bằng Text-to-SQL trên CSDL events (dùng seed data hoặc event thật), trả về câu trả lời tự nhiên đính kèm link clip 10s. Tích hợp app entrypoints (backend/main.py, backend/api/routes.py) qua proposed shared file changes.
- Verification method: Chạy pytest test các câu hỏi mẫu ("Hôm nay có xe lạ nào vào không?", "Cho tôi xem video xe vi phạm zone bãi kiểm").
- Parallel-safety notes: Chạy song song ngay tại Wave 1 của Phase 2 cùng TASK-009 và TASK-010 bằng cách truy vấn trên `seed_events.sql` từ Phase 1.
- Status: ready

#### TASK-011b: AI Chatbot Web UI & WebSocket Integration
- Task type: feature-implementation
- Scope: module
- Module: web-ui
- Linked requirements: REQ-008
- Linked change requests: none
- Dependencies: TASK-005, TASK-006, TASK-007
- Assigned to: Person A
- Required capability: frontend-implementation
- Inputs: `docs/contracts/api-schema.json`, `docs/contracts/websocket-events.json`, `Prototype/Intern-LPR-Gate.dc.html`
- Outputs: `frontend/src/chat/ai_chatbot.js`, `frontend/src/chat/video_modal.js`
- Write scope: frontend/src/chat/
- Wave: 1
- Completion gate: Giao diện Chatbot AI đính kèm trình phát video MP4 10s (có nút tải clip) và Prompt Chips gợi ý (dùng mock response dựa trên API contract TASK-002 trước khi API thật sẵn sàng). Tích hợp UI entrypoint (frontend/src/app.js) qua proposed shared file changes.
- Verification method: Mở Web UI gửi câu hỏi chat thử nghiệm và kiểm tra video player 10s hoạt động.
- Parallel-safety notes: Chạy song song tại Wave 1 của Phase 2 với TASK-011a bằng cách sử dụng mock response dựa trên API schema hợp đồng.
- Status: ready

#### TASK-011c: Real-time Multi-channel Alert Dispatcher (Web Sound Beep & Telegram Bot)
- Task type: feature-implementation
- Scope: module
- Module: alert-dispatcher
- Linked requirements: REQ-003, REQ-009
- Linked change requests: none
- Dependencies: TASK-002, TASK-006, TASK-007
- Assigned to: Person B
- Required capability: backend-implementation, frontend-implementation
- Inputs: `docs/contracts/websocket-events.json`, `backend/db/crud.py`
- Outputs: `backend/alerts/telegram_bot.py`, `backend/alerts/dispatcher.py`, `frontend/src/alerts/sound_alert.js`
- Write scope: backend/alerts/, frontend/src/alerts/
- Wave: 1
- Completion gate: Phát còi hiệu báo động âm thanh (audio alert beep) trên Web UI khi nhận WebSocket event Mức 3 và đẩy thông báo vi phạm kèm ảnh crop/chi tiết sang Telegram Bot trong < 2 giây.
- Verification method: Chạy unit test `python -m pytest backend/tests/test_alert_dispatcher.py` và kiểm tra nhận tin nhắn Telegram thử nghiệm + phát âm thanh Web.
- Parallel-safety notes: Module độc lập không tranh chấp write scope với stream hay chatbot modules.
- Status: ready

### Wave 2 (Mid-Project Integration Checkpoint)

#### TASK-012: Core Feature Integration Checkpoint
- Task type: integration-checkpoint
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009
- Linked change requests: none
- Dependencies: TASK-009, TASK-010, TASK-011a, TASK-011b, TASK-011c
- Assigned to: Person B
- Required capability: verify-feature
- Inputs: Toàn bộ mã nguồn `backend/` và `frontend/` đã hoàn thành tại Wave 1.
- Outputs: `docs/reports/integration-checkpoint-report.md`
- Write scope: docs/reports/
- Wave: 2
- Completion gate: Khởi chạy tích hợp Module Cổng + Module Khu vực + FastAPI WebServer + Web UI Frontend + QA Chatbot, xác nhận luồng dữ liệu event chảy mượt mà từ video stream đến DB, Dashboard và Chatbot AI.
- Verification method: Chạy `python -m pytest backend/tests/test_modules_integration.py` đạt 100% pass trước khi bước vào Phase 3.
- Parallel-safety notes: Điểm kiểm soát tích hợp sớm nhằm phát hiện rủi ro giao tiếp giữa các phân hệ.
- Status: ready

---

## Phase 3 — E2E Verification & Packaging
- Gate: user-approval
- Integration commands: python backend/tests/test_e2e.py

### Wave 1 (System Verification & Documentation Packaging)

#### TASK-013: Documentation & Deployment Packaging (README & Docker Compose)
- Task type: project-deliverable
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-008
- Linked change requests: none
- Dependencies: TASK-012
- Assigned to: Person A
- Required capability: backend-implementation
- Inputs: Cấu trúc dự án `backend/`, `frontend/`, `data/`
- Outputs: `docs/deployment-guide.md`
- Write scope: docs/deployment-guide.md
- Wave: 1
- Completion gate: Xây dựng tài liệu hướng dẫn cài đặt, cấu hình môi trường, chạy ứng dụng bằng lệnh local/docker-compose theo đúng Mục 4 của RFP bài tập. Đề xuất cập nhật README.md và docker-compose.yml qua proposed shared file changes.
- Verification method: Thử nghiệm chạy lệnh khởi tạo hệ thống theo đúng các bước trong `README.md`.
- Parallel-safety notes: Chạy song song tại Wave 1 Phase 3 với TASK-014 (không phụ thuộc lẫn nhau).
- Status: ready

#### TASK-014: Full System E2E Feature Verification
- Task type: feature-verification
- Scope: global
- Module: none
- Linked requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009
- Linked change requests: none
- Dependencies: TASK-012
- Assigned to: Person B
- Required capability: verify-feature
- Inputs: Toàn bộ hệ thống `backend/`, `frontend/`, 2 video mẫu `GATE-01.mp4` & `BAI-KIEM.mp4`
- Outputs: `docs/reports/e2e-verification-report.md`
- Write scope: docs/reports/
- Wave: 1
- Completion gate: Kiểm thử E2E toàn bộ 8 Yêu cầu bắt buộc của RFP trên cả 4 tab giao diện, xác nhận FPS >= 5 trên 2 video stream, trích xuất clip 10s quanh thời điểm sự kiện, fallback sửa tay biển số OCR và hỏi đáp AI Chatbot chính xác.
- Verification method: Chạy bộ kịch bản test E2E `python backend/tests/test_e2e.py` và kiểm tra trực quan trên Web Browser.
- Parallel-safety notes: Chạy song song tại Wave 1 Phase 3 với TASK-013, kiểm thử nghiệm thu tổng thể dự án.
- Status: ready

---

## 3. Phụ lục: Mô-đun Mở rộng Tùy chọn (Optional Extensions)

Các tính năng hoặc cải tiến bổ sung ngoài luồng chính (chỉ thực hiện thêm nếu hoàn thành sớm toàn bộ 9 Yêu cầu cơ bản):

- **OPTIONAL-001: Tối ưu AI Engine với TensorRT / ONNX Acceleration**:
  - Export mô hình YOLOv8 sang TensorRT / OpenVINO để tăng tốc độ quét FPS > 25 FPS trên phần cứng có GPU.

---

## 4. Bản đồ Vết Yêu cầu (Requirements Traceability Map)

| Requirement ID | Tên Yêu cầu | Danh sách Nhiệm vụ Phụ trách (Task IDs) |
|---|---|---|
| **REQ-001** | Nhận diện biển số xe tại Cổng (LPR Gate & Manual Fallback) | `TASK-001`, `TASK-002`, `TASK-003`, `TASK-005`, `TASK-006`, `TASK-009`, `TASK-012`, `TASK-013`, `TASK-014` |
| **REQ-002** | Giám sát Khu vực & Quy tắc Zone (Area Zone Violations) | `TASK-001`, `TASK-002`, `TASK-003`, `TASK-005`, `TASK-006`, `TASK-007`, `TASK-010`, `TASK-012`, `TASK-013`, `TASK-014` |
| **REQ-003** | Phân cấp Mức độ Cảnh báo (Alert Severity Level 1/2/3) | `TASK-002`, `TASK-003`, `TASK-007`, `TASK-009`, `TASK-010`, `TASK-011c`, `TASK-012`, `TASK-014` |
| **REQ-004** | Khử trùng lặp sự kiện (Deduplication Cooldown Config) | `TASK-007`, `TASK-012`, `TASK-014` |
| **REQ-005** | Cấu hình Zone Đa giác tương tác (Polygon Zone) | `TASK-002`, `TASK-005`, `TASK-008`, `TASK-012`, `TASK-014` |
| **REQ-006** | Quản lý Biển số Quen / Lạ (Whitelist/Blacklist) | `TASK-003`, `TASK-005`, `TASK-006`, `TASK-008`, `TASK-012`, `TASK-014` |
| **REQ-007** | Tool Gắn nhãn Mẫu Đối tượng Custom (Custom Labels) | `TASK-003`, `TASK-004`, `TASK-005`, `TASK-006`, `TASK-008`, `TASK-012`, `TASK-014` |
| **REQ-008** | AI Assistant Hỏi đáp Sự kiện kèm Clip 10s | `TASK-002`, `TASK-003`, `TASK-005`, `TASK-007`, `TASK-011a`, `TASK-011b`, `TASK-012`, `TASK-013`, `TASK-014` |
| **REQ-009** | Cảnh báo Tức thì Đa kênh (Web Sound Beep & Telegram Bot) | `TASK-002`, `TASK-003`, `TASK-011c`, `TASK-012`, `TASK-014` |

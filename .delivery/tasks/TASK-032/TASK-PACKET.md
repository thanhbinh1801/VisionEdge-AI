---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-27T20:34:39+07:00"
task_id: TASK-032
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-032 CR-007 Frontend Debug Controls và Type Surface cho Area Dashboard

- Task ID: TASK-032
- Task type: implementation
- Scope: feature
- Module: web-ui
- Capability: frontend-implementation
- Linked requirements: REQ-002, REQ-004, REQ-009, CR-007
- Dependencies: TASK-030, TASK-031
- Write scope: .delivery/tasks/TASK-032/
- Inputs: .delivery/API-CONTRACT.md, frontend/src/pages/AreaSecurityDashboard.tsx, frontend/src/services/api.ts, frontend/src/types/
- Expected outputs: frontend Area Dashboard/type updates, .delivery/tasks/TASK-032/TASK-RESULT.md
- Completion gate: Frontend type surface chấp nhận metadata additive CR-007; Area Dashboard có thể truyền `conf_threshold` và `show_static_containers` cho debug mà không đổi layout nghiệp vụ chính hoặc event/alert behavior.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, thực hiện migration phá hủy dữ liệu, mở rộng phạm vi hoặc ảnh hưởng tới công việc đang triển khai/đã hoàn thành.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Triển khai frontend CR-007 cho Area Dashboard: mở rộng type surface để chấp nhận metadata additive từ backend, truyền được `conf_threshold` và `show_static_containers` vào video feed khi debug, hiển thị/giữ được thông tin debug bbox/class/zone evaluation khi có dữ liệu, nhưng không làm thay đổi layout nghiệp vụ chính, hành vi event/alert, Gate Dashboard hoặc luồng LPR/GATE-01.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-032/TASK-PACKET.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/API-CONTRACT.md`
- `.delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md`
- `.delivery/changes/CR-007/CHANGE-IMPACT.md`
- `.delivery/tasks/TASK-030/API-CONTRACT.md`
- `.delivery/tasks/TASK-030/TASK-RESULT.md`
- `.delivery/tasks/TASK-031/TASK-RESULT.md`
- `frontend/src/pages/AreaSecurityDashboard.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/types/`
- Code/evidence backend liên quan nếu cần đối chiếu field runtime: `backend/app/api/v1/events.py`, `backend/app/services/area_metadata.py`, `backend/app/services/vision_pipeline.py`
- Phần `TASK-032 CR-007 Frontend Debug Controls và Type Surface cho Area Dashboard` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- `frontend/src/pages/AreaSecurityDashboard.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/types/`
- `.delivery/tasks/TASK-032/TASK-RESULT.md`
- `.delivery/tasks/TASK-032/BUG-NNN.md` nếu phát hiện lỗi/blocker liên quan trực tiếp

### Phạm vi cấm (Forbidden scope)
- Không sửa backend trong TASK-032.
- Không sửa `.delivery/MASTER-PLAN.md`, requirements, architecture, ADR, aggregate API contract hoặc JSON schema.
- Không sửa database schema/migration hoặc persistence model.
- Không thay đổi Gate Dashboard, LPR/GATE-01 flow, OCR, vehicle tag hoặc gate event semantics.
- Không đổi event/alert behavior, audio/popup/Telegram trigger hoặc cooldown/dedup.
- Không triển khai tracking đầy đủ; `track_id` chỉ là optional/future-compatible field.
- Không tự chuyển `TASK-RESULT.md` hoặc artifact thành `approved` trước review.

### Tiêu chí nghiệm thu (Acceptance criteria)
- Frontend type surface chấp nhận các field additive CR-007: `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`, `track_id`.
- Các field mới là optional/backward-compatible; dữ liệu cũ từ TASK-016 vẫn render được.
- Area Dashboard có cơ chế truyền `conf_threshold` cho `/api/v1/events/video-feed` như display/debug threshold, không diễn giải nó là event threshold.
- Area Dashboard có cơ chế truyền `show_static_containers=true|false`; default không làm rối UI vận hành bằng bbox container tĩnh.
- Debug controls chỉ áp dụng Area Dashboard/video feed khu vực, không ảnh hưởng Gate Dashboard hoặc LPR.
- UI không tạo event/alert/audio/popup/Telegram từ metadata hoặc bbox debug lane.
- Nếu hiển thị metadata debug, nhãn class ưu tiên tên tiếng Việt/`canonical_class`, vẫn giữ raw class phục vụ debug khi có.
- TypeScript/build frontend pass theo verification method của master plan.
- `TASK-RESULT.md` ghi đủ inputs used, outputs produced, validation evidence, deviations, blockers và scope change requests.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- Backend có thể trả thiếu field mới trong một số frame; frontend phải xử lý `null`/absent an toàn.
- `track_id` có thể không có vì tracking đầy đủ chưa thuộc CR-007; không được bắt buộc field này trong UI/type.
- `zone_overlap_ratio` có thể bằng `0`, `null` hoặc absent tùy method; UI/type không được nhầm với lỗi.
- Lower `conf_threshold` có thể làm stream hiển thị thêm bbox debug nhưng không được làm thay đổi alert state.
- Container/static container có thể bị ẩn khỏi MJPEG theo default backend; UI debug phải bật được mà không đổi default vận hành.
- Nếu hiện không có thư mục `frontend/src/types/`, task có thể tạo file type trong phạm vi đó hoặc mở rộng type hiện hữu theo pattern repo.

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh xác minh theo MASTER-PLAN: `npx --prefix frontend tsc --noEmit && npm --prefix frontend run build`.
- Nếu repo có linter/test frontend scoped, chạy thêm theo pattern hiện hữu sau khi đọc `package.json`.
- Validator chuyên biệt nên chạy sau implementation nếu có: dùng validator của `$implement-frontend` cho `TASK-032`.
- Kiểm tra thủ công: đối chiếu request video feed có query `conf_threshold` và `show_static_containers`, type frontend với contract `AREA_FRAME_METADATA`, và regression boundary không đổi Gate Dashboard/LPR.

### Điều kiện leo thang (Escalation conditions)
- Dừng lại và báo cáo trong `TASK-RESULT.md` nếu cần sửa backend/API contract đã duyệt, đổi hành vi event/alert, thay đổi Gate/LPR flow, thêm dependency UI lớn, mở rộng scope sang tracking implementation, hoặc nếu thiếu fixture/build setup khiến không thể chứng minh completion gate.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Task ID: TASK-032
- Outcome: completed | blocked
- Inputs used: Danh sách các tệp/artifact đã đọc.
- Outputs produced: Danh sách file frontend/types và `.delivery/tasks/TASK-032/TASK-RESULT.md`.
- Validation evidence: Exact commands, exit codes và kết quả thực thi.
- Deviations: none hoặc sai lệch phát hiện được.
- Blockers: none hoặc mô tả điểm chặn.
- Scope change requests: none hoặc yêu cầu thay đổi phạm vi.

### Skill/capability cần chạy (Skill/capability to run)
- Capability: frontend-implementation
- Next skill: `$implement-frontend`

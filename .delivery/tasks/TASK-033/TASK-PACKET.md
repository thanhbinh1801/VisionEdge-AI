---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-27T20:38:58+07:00"
task_id: TASK-033
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-033 CR-007 Verification và Regression Không đổi LPR/GATE-01

- Task ID: TASK-033
- Task type: verification
- Scope: global
- Module: none
- Capability: verify-feature
- Linked requirements: REQ-001, REQ-002, REQ-004, REQ-009, CR-007
- Dependencies: TASK-031, TASK-032
- Write scope: .delivery/tasks/TASK-033/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/API-CONTRACT.md, .delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md, .delivery/changes/CR-007/CHANGE-IMPACT.md, backend/frontend implementation under backend/app/ and frontend/src/
- Expected outputs: .delivery/tasks/TASK-033/TEST-REPORT.md, .delivery/tasks/TASK-033/TASK-RESULT.md, bug records if verification fails
- Completion gate: Xác minh bbox display threshold không tự sinh event/alert, class-aware zone evaluation đúng theo nhóm đối tượng, container bbox debug bật/tắt được, metadata additive tương thích ngược, stream vẫn đạt FPS >= 5 và LPR/GATE-01 không đổi ngoài regression evidence.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, thực hiện migration phá hủy dữ liệu, mở rộng phạm vi hoặc ảnh hưởng tới công việc đang triển khai/đã hoàn thành.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Xác minh CR-007 end-to-end và regression boundary: bbox display/debug threshold không tự sinh event/alert, class-aware zone evaluation đúng theo từng nhóm đối tượng, bật/tắt bbox container tĩnh hoạt động đúng, metadata additive tương thích ngược với TASK-016/TASK-030, stream Area Monitoring vẫn đạt FPS tối thiểu, và LPR/GATE-01 không đổi ngoài bằng chứng regression.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-033/TASK-PACKET.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/API-CONTRACT.md`
- `.delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md`
- `.delivery/changes/CR-007/CHANGE-IMPACT.md`
- `.delivery/tasks/TASK-030/API-CONTRACT.md`
- `.delivery/tasks/TASK-030/TASK-RESULT.md`
- `.delivery/tasks/TASK-031/TASK-RESULT.md`
- `.delivery/tasks/TASK-032/TASK-RESULT.md`
- Backend implementation evidence under `backend/app/` and `backend/tests/`
- Frontend implementation evidence under `frontend/src/` and `frontend/package.json`
- Phần `TASK-033 CR-007 Verification và Regression Không đổi LPR/GATE-01` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- `.delivery/tasks/TASK-033/TEST-REPORT.md`
- `.delivery/tasks/TASK-033/TASK-RESULT.md`
- `.delivery/tasks/TASK-033/BUG-NNN.md` nếu verification phát hiện lỗi cần ghi nhận

### Phạm vi cấm (Forbidden scope)
- Không sửa production code backend/frontend trong TASK-033.
- Không sửa `.delivery/MASTER-PLAN.md`, requirements, architecture, ADR, aggregate API contract hoặc JSON schema.
- Không sửa database schema/migration hoặc persistence model.
- Không thay đổi Gate Dashboard, LPR/GATE-01 flow, OCR, vehicle tag, event/alert semantics, Telegram hoặc cooldown/dedup.
- Không mở rộng tracking persistence hoặc triển khai ByteTrack/BoT-SORT.
- Không tự sửa lỗi phát hiện trong verification; ghi `BUG-NNN.md` và báo trong `TASK-RESULT.md`.
- Không tự chuyển `TEST-REPORT.md`/`TASK-RESULT.md` thành `approved` trước review.

### Tiêu chí nghiệm thu (Acceptance criteria)
- Có bằng chứng display/debug threshold chỉ ảnh hưởng bbox/metadata/debug lane, không tự tạo event/alert/audio/popup/Telegram.
- Có bằng chứng class-aware zone evaluation dùng đúng method theo nhóm: `bottom_center`, `footprint_overlap`, `bbox_overlap_ratio`, và fallback nếu có được ghi rõ.
- Có bằng chứng `show_static_containers=false` mặc định không làm rối MJPEG, và `show_static_containers=true` bật được bbox `container`/`shipping_container` khi debug.
- Có bằng chứng metadata additive tương thích ngược: dữ liệu cũ vẫn dùng được, field mới optional/null an toàn.
- Có bằng chứng frontend type/build chấp nhận field CR-007 và không làm đổi Gate Dashboard/LPR flow.
- Có bằng chứng backend scoped tests pass theo master plan.
- Có bằng chứng frontend build pass theo master plan.
- Có đánh giá FPS hoặc bằng chứng tương đương cho stream Area Monitoring đạt tối thiểu `FPS >= 5`; nếu không đo được trong môi trường test, ghi rõ lý do và rủi ro.
- Có regression evidence rằng LPR/GATE-01 không đổi ở route/test liên quan.
- `TEST-REPORT.md` và `TASK-RESULT.md` ghi đủ commands, kết quả, lỗi nếu có, deviations, blockers và bug records.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- Môi trường local có thể không có camera/video source thật hoặc model weights; nếu không đo trực tiếp được FPS/model runtime, phải ghi rõ giới hạn bằng chứng và dùng test seam hiện hữu.
- Build frontend có thể cần chạy ngoài sandbox nếu Vite/esbuild gặp `spawn EPERM`; ghi lại exact command/result.
- Một số warnings hiện hữu như Pydantic/FastAPI deprecation hoặc Vite chunk-size warning không nhất thiết là blocker, nhưng phải ghi nếu xuất hiện.
- `track_id` là optional/future-compatible; verification không được coi thiếu `track_id` là lỗi nếu contract cho phép absent/null.
- Nếu phát hiện event/alert behavior đổi ngoài phạm vi CR-007 hoặc LPR/GATE-01 regression, phải tạo bug record thay vì sửa code.

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh xác minh theo MASTER-PLAN: `python -m pytest backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py -q && npm --prefix frontend run build`.
- Nên dùng Python/venv phù hợp với repo nếu Python hệ thống thiếu dependency, nhưng phải ghi rõ command thực tế.
- Chạy thêm các test scoped liên quan nếu có: video feed regression, area metadata runtime, frontend lint/typecheck theo `frontend/package.json`.
- Validator chuyên biệt nên chạy sau verification: `python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-033` nếu script tồn tại.
- Kiểm tra thủ công/report: đối chiếu `TEST-REPORT.md` với TASK-030 contract, TASK-031/TASK-032 result và regression boundary LPR/GATE-01.

### Điều kiện leo thang (Escalation conditions)
- Dừng lại và báo cáo trong `TASK-RESULT.md` nếu verification cần sửa production code, đổi approved contract, thêm dependency lớn, truy cập thiết bị/nguồn dữ liệu không có quyền, thay đổi security posture, hoặc không thể thu bằng chứng tối thiểu sau khi đã ghi rõ lệnh và lỗi.

### Định dạng TEST-REPORT kỳ vọng (Expected TEST-REPORT format)
- Task ID: TASK-033
- Scope verified: CR-007 Area Monitoring detection/debug/metadata/frontend/regression boundary.
- Requirements covered: REQ-001, REQ-002, REQ-004, REQ-009, CR-007.
- Test matrix: Danh sách case, mục tiêu, lệnh/bằng chứng, kết quả pass/fail.
- Regression evidence: LPR/GATE-01, event/alert lane, metadata backward compatibility, stream/debug controls.
- Bugs found: none hoặc danh sách `BUG-NNN.md`.
- Residual risks: none hoặc giới hạn bằng chứng còn lại.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Task ID: TASK-033
- Outcome: completed | blocked
- Inputs used: Danh sách các tệp/artifact đã đọc.
- Outputs produced: `.delivery/tasks/TASK-033/TEST-REPORT.md`, `.delivery/tasks/TASK-033/TASK-RESULT.md`, bug records nếu có.
- Validation evidence: Exact commands, exit codes và kết quả thực thi.
- Deviations: none hoặc sai lệch phát hiện được.
- Blockers: none hoặc mô tả điểm chặn.
- Scope change requests: none hoặc yêu cầu thay đổi phạm vi.

### Skill/capability cần chạy (Skill/capability to run)
- Capability: feature-verification
- Next skill: `$verify-feature`

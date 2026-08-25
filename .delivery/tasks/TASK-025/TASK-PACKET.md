---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-24T22:20:47+07:00"
task_id: TASK-025
packet_revision: 1
supersedes: none
depends_on: [REQUIREMENTS.md, ARCHITECTURE.md, TASK-020, TASK-021, TASK-022, TASK-023, TASK-024]
---

# Gói Task: TASK-025 — Verification End-to-End cho CR-004 Object Labeling

- Mã task: TASK-025
- Loại task: verification
- Phạm vi: feature
- Module: web-ui
- Năng lực: feature-verification
- Yêu cầu liên kết: REQ-005, REQ-007, CR-004
- Phụ thuộc: TASK-020, TASK-021, TASK-022, TASK-023, TASK-024
- Phạm vi ghi: .delivery/tasks/TASK-025/
- Đầu vào: `.delivery/REQUIREMENTS.md`, `.delivery/tasks/TASK-020/DATABASE-DESIGN.md`, `.delivery/tasks/TASK-020/TASK-RESULT.md`, `.delivery/tasks/TASK-021/API-CONTRACT.md`, `.delivery/tasks/TASK-021/TASK-RESULT.md`, `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md`, `.delivery/tasks/TASK-022/UI-SPEC.md`, `.delivery/tasks/TASK-022/UX-FLOW.md`, `.delivery/tasks/TASK-022/TASK-RESULT.md`, `.delivery/tasks/TASK-023/TASK-RESULT.md`, `.delivery/tasks/TASK-024/TASK-RESULT.md`, backend/frontend implementation under `backend/` and `frontend/src/`.
- Đầu ra dự kiến: `.delivery/tasks/TASK-025/TEST-REPORT.md`, `.delivery/tasks/TASK-025/TASK-RESULT.md`, bug records if verification fails.
- Điều kiện hoàn thành: Xác minh end-to-end import ảnh/video thật, chọn frame video, vẽ/sửa/xóa bbox, tạo/sửa/soft delete/restore nhãn custom, khóa nhãn hệ thống, reload persisted samples từ DB và sync zone rules mặc định `cấm`.
- Chính sách phê duyệt: Project owner review required before promoting verification artifacts from `in-review` to `approved`.
- Chính sách leo thang: Escalate only if verification requires repairing production code, changing approved contracts, changing database schema/migrations, deleting data, or running unavailable external infrastructure.

## Contract Fields

- Task ID: TASK-025
- Task type: verification
- Scope: feature
- Module: web-ui
- Capability: feature-verification
- Linked requirements: REQ-005, REQ-007, CR-004
- Dependencies: TASK-020, TASK-021, TASK-022, TASK-023, TASK-024
- Write scope: .delivery/tasks/TASK-025/
- Inputs: `.delivery/REQUIREMENTS.md`, `.delivery/tasks/TASK-020/DATABASE-DESIGN.md`, `.delivery/tasks/TASK-020/TASK-RESULT.md`, `.delivery/tasks/TASK-021/API-CONTRACT.md`, `.delivery/tasks/TASK-021/TASK-RESULT.md`, `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md`, `.delivery/tasks/TASK-022/UI-SPEC.md`, `.delivery/tasks/TASK-022/UX-FLOW.md`, `.delivery/tasks/TASK-022/TASK-RESULT.md`, `.delivery/tasks/TASK-023/TASK-RESULT.md`, `.delivery/tasks/TASK-024/TASK-RESULT.md`, backend/frontend implementation under `backend/` and `frontend/src/`.
- Expected outputs: `.delivery/tasks/TASK-025/TEST-REPORT.md`, `.delivery/tasks/TASK-025/TASK-RESULT.md`, bug records if verification fails.
- Completion gate: Verify end-to-end real image/video import, video frame selection, bbox create/update/delete, custom label create/update/soft delete/restore, locked system labels, persisted sample reload from DB, and default `forbidden` zone-rule sync.
- Approval policy: Project owner review required before promoting verification artifacts from `in-review` to `approved`.
- Escalation policy: Escalate only if verification requires repairing production code, changing approved contracts, changing database schema/migrations, deleting data, or running unavailable external infrastructure.

## Execution Brief

### Objective
Xác minh CR-004 object labeling chạy đúng end-to-end trên backend/frontend đã triển khai: media source thật, frame selection, bbox samples persisted, CRUD nhãn custom, khóa nhãn hệ thống, reload dữ liệu từ DB và đồng bộ zone rules theo hợp đồng đã duyệt.

### Source-of-truth artifacts to read
- `.delivery/tasks/TASK-025/TASK-PACKET.md`
- `.delivery/MASTER-PLAN.md` section `TASK-025 Verification End-to-End cho CR-004 Object Labeling`
- `.delivery/REQUIREMENTS.md`
- `.delivery/DOMAIN-MODEL.md`
- `.delivery/tasks/TASK-020/DATABASE-DESIGN.md`
- `.delivery/tasks/TASK-020/TASK-RESULT.md`
- `.delivery/tasks/TASK-021/API-CONTRACT.md`
- `.delivery/tasks/TASK-021/TASK-RESULT.md`
- `.delivery/tasks/TASK-022/UI-UX-CONTRACT.md`
- `.delivery/tasks/TASK-022/UI-SPEC.md`
- `.delivery/tasks/TASK-022/UX-FLOW.md`
- `.delivery/tasks/TASK-022/TASK-RESULT.md`
- `.delivery/tasks/TASK-023/TASK-RESULT.md`
- `.delivery/tasks/TASK-024/TASK-RESULT.md`
- Backend/frontend implementation under `backend/` and `frontend/src/`

### Allowed write scope
- `.delivery/tasks/TASK-025/TEST-REPORT.md`
- `.delivery/tasks/TASK-025/TASK-RESULT.md`
- `.delivery/tasks/TASK-025/BUG-NNN.md` nếu verification phát hiện lỗi

### Forbidden scope
- Không sửa `.delivery/MASTER-PLAN.md`, requirements, architecture, approved task contracts, production backend/frontend code, database schema/migrations, runtime DB files, hoặc artifact task khác.
- Không tự fix bug trong task verification; ghi bug record/scope-change request nếu cần sửa production code.
- Không promote artifact sang `approved`; việc phê duyệt thuộc project owner/main-agent sau review.

### Acceptance criteria
- Import được ảnh/video thật qua API/storage đã triển khai và UI hiển thị source thật thay mock/local state.
- Với video source, chọn/scrub frame đúng và bbox sample được tạo trên frame đã chọn.
- Vẽ, sửa, xóa bbox sample hoạt động đúng, validate batch atomically, và reload vẫn thấy persisted samples từ DB.
- Tạo/sửa/soft delete/restore nhãn custom hoạt động đúng, không cho trùng tên không phân biệt hoa/thường, và `sample_count` phản ánh dữ liệu persisted.
- Nhãn hệ thống bị khóa đúng: không sửa/xóa như nhãn custom.
- Sync zone rules mặc định `cấm` cho nhãn custom mới đúng theo CR-004 và không để stale label key trong zone rules sau delete/restore flows.
- Frontend tab `Nhãn đối tượng` không còn phụ thuộc mock/local-only state cho media source, labels hoặc bbox samples.
- Verification ghi rõ pass/fail, command evidence, manual/automated coverage, bug records nếu có, deviations, blockers và scope-change requests.

### Edge cases / risks
- Cần kiểm tra cả ảnh và video vì frame index của ảnh phải normalize về `0`, còn video cần endpoint/frame retrieval riêng.
- Cần kiểm tra reload thật từ backend/DB, không chỉ state trong memory của phiên UI hiện tại.
- Cần kiểm tra label custom bị xóa mềm khi còn được zone reference: chỉ chặn khi thật sự referenced theo semantics đã fix ở TASK-024.
- Cần phân biệt lỗi verification với scope implementation; verification task không sửa production code.
- Nếu môi trường sandbox chặn build/dev server/browser hoặc thiếu external media tooling, ghi rõ evidence và blocker thay vì giả định pass.

### Verification commands or validation method
- Planned verification command from MASTER-PLAN: `python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-025`.
- Suggested scoped checks:
  - `python -m pytest backend/tests/test_dataset_object_labeling.py backend/tests/test_dataset_zone_sync.py -q`
  - `npm --prefix frontend run build`
  - Additional manual/browser or API probes as needed to verify import, frame selection, bbox edit/delete, label CRUD, persisted reload and zone sync behavior.

### Escalation conditions
- Escalate if verification requires repairing backend/frontend production code, changing approved DB/API/UI contracts, changing schema/migrations, deleting runtime data, using unavailable external infrastructure, or expanding acceptance beyond CR-004.

### Expected TASK-RESULT format
- Frontmatter with `owner: verify-feature`, `task_id: TASK-025`, and `status: in-review` for completed verification awaiting review.
- `Outcome: completed | blocked`
- Inputs used.
- Outputs produced.
- Validation evidence with commands, exit codes and high-signal results.
- Verification matrix mapped to acceptance criteria.
- Bugs filed or revalidated.
- Deviations and caveats.
- Blockers and owner.
- Scope change requests.

### Skill/capability to run
- `verify-feature`.

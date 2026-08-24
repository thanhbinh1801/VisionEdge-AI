---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T20:17:18+07:00"
task_id: TASK-023
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-023 Backend Object Labeling Thật theo Design đã Duyệt

- Task ID: TASK-023
- Task type: implementation
- Scope: feature
- Module: api-gateway
- Capability: backend-implementation
- Linked requirements: REQ-005, REQ-007, CR-004
- Dependencies: TASK-020, TASK-021
- Write scope: .delivery/tasks/TASK-023/
- Inputs: .delivery/tasks/TASK-020/DATABASE-DESIGN.md, .delivery/tasks/TASK-021/API-CONTRACT.md, backend/app/api/v1/dataset.py, backend/database/models.py, backend/database/repository.py
- Expected outputs: backend dataset API/storage implementation, backend tests, .delivery/tasks/TASK-023/TASK-RESULT.md
- Completion gate: Backend lưu được media import và metadata, quản lý nhãn hệ thống/custom, lưu/tải/sửa/xóa bbox samples, soft delete/restore nhãn custom, validate batch atomically, sync custom labels vào zone rules mặc định `cấm`, và không yêu cầu AI realtime nhận diện class custom mới.
- Approval policy: Chủ dự án là người duyệt duy nhất.
- Escalation policy: Dừng lại khi có thay đổi phá tương thích, ảnh hưởng bảo mật, phát sinh chi phí đáng kể, migration phá hủy/khó đảo ngược, mở rộng phạm vi, hoặc tác động tới work đang in-progress/completed.

## Execution Brief

### Objective

Triển khai backend object labeling thật theo design đã duyệt của CR-004: media import được lưu trong managed storage, metadata source/frame persisted, labels hệ thống/custom được quản lý đúng lifecycle, BBox samples CRUD được lưu DB, batch validation atomic, và custom labels được sync vào zone rules mặc định `cấm`.

### Source-of-truth artifacts to read

- `.delivery/tasks/TASK-023/TASK-PACKET.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/DOMAIN-MODEL.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/tasks/TASK-020/DATABASE-DESIGN.md`
- `.delivery/tasks/TASK-020/TASK-RESULT.md`
- `.delivery/tasks/TASK-021/API-CONTRACT.md`
- `.delivery/tasks/TASK-021/TASK-RESULT.md`
- `backend/app/api/v1/dataset.py`
- `backend/database/models.py`
- `backend/database/repository.py`
- `backend/database/engine.py`
- `backend/app/api/router.py`
- `backend/app/api/v1/zones.py`
- `backend/tests/test_database.py`
- `.delivery/MASTER-PLAN.md` section `TASK-023 Backend Object Labeling Thật theo Design đã Duyệt`

### Allowed write scope

- `backend/app/api/v1/dataset.py`
- `backend/database/`
- `backend/tests/`
- `.delivery/tasks/TASK-023/`

### Forbidden scope

- Không sửa `.delivery/MASTER-PLAN.md`, `.delivery/REQUIREMENTS.md`, `.delivery/DOMAIN-MODEL.md`, `.delivery/ARCHITECTURE.md`, `.delivery/tasks/TASK-020/`, `.delivery/tasks/TASK-021/`, frontend production code, runtime database files ngoài migration/test control được task yêu cầu, hoặc artifact của task khác.
- Không triển khai realtime AI inference cho custom class mới trong phạm vi TASK-023.
- Không thay đổi UI/UX hoặc API contract đã duyệt; nếu contract mâu thuẫn với code hiện tại thì ghi deviation/scope-change request trong `TASK-RESULT.md`.

### Acceptance criteria

- Endpoint CR-004 dưới `/api/v1/dataset` tuân thủ `.delivery/tasks/TASK-021/API-CONTRACT.md`, gồm envelope JSON chuẩn, multipart upload, binary frame retrieval, label CRUD/soft delete/restore, sample list/batch create/update/delete, và sync zones.
- DB/model/repository tuân thủ `.delivery/tasks/TASK-020/DATABASE-DESIGN.md`, bao gồm `object_labels` semantics hoặc migration tương thích từ `custom_labels`, `dataset_sources` metadata thật, FK/constraints cho `bbox_samples`, `sample_count` nhất quán, và uniqueness label không phân biệt hoa/thường.
- 8 nhãn hệ thống được khóa rename/delete/restore nhưng vẫn chọn được để gắn BBox samples.
- Nhãn custom hỗ trợ create, rename, soft delete, restore; soft delete bị chặn nếu label còn trong zone rules; restore/create sync vào mọi zone với trạng thái mặc định `cấm`.
- Batch save BBox samples là all-or-nothing; một item invalid thì không item nào được persist.
- Media upload lưu file vào managed backend storage, không dùng absolute path từ browser, và frame retrieval trả JPEG cùng headers contract yêu cầu.
- Không yêu cầu hoặc tuyên bố custom label mới được YOLO realtime nhận diện khi chưa có model đã huấn luyện.

### Edge cases / risks

- Migration từ schema hiện tại có thể gặp orphan `bbox_samples`, duplicate label khác hoa/thường, hoặc `label_id` chưa có FK rõ ràng.
- File media lớn/codec không hỗ trợ cần trả lỗi đúng contract, không để path traversal hoặc unmanaged path lọt vào DB.
- `sample_count` dễ lệch nếu create/update/delete sample không recompute affected labels trong cùng transaction.
- Cache refresh zone có thể fail sau DB commit; phải trả trạng thái recoverable theo API contract thay vì rollback ẩn nếu design quy định DB là source of truth.
- Not specified in source artifacts: cơ chế auth runtime thực tế, vị trí managed media root chính thức nếu repo chưa có setting, chiến lược cleanup file orphan sau upload fail, và quy trình rollback migration chi tiết ở code.

### Verification commands or validation method

- Chạy tối thiểu: `python -m pytest backend/tests/test_dataset_object_labeling.py backend/tests/test_dataset_zone_sync.py -q`.
- Chạy thêm các test backend liên quan nếu bị ảnh hưởng, đặc biệt test database/repository hiện hữu.
- Nếu thêm schema/migration, verify migration trên DB test hoặc temporary DB, không dùng runtime DB local như bằng chứng duy nhất.
- Implementation specialist phải tự sửa lỗi compile/import/test trong scope trước khi đánh dấu completed.

### Escalation conditions

- Dừng và báo trong `TASK-RESULT.md` nếu cần phá tương thích API/DB đã duyệt, thay đổi security posture, thêm dependency/dịch vụ phát sinh chi phí, thực hiện migration phá hủy/khó rollback, sửa frontend, sửa aggregate artifacts, hoặc mở rộng sang AI realtime custom-class inference.

### Expected TASK-RESULT format

- Task ID: TASK-023
- Outcome: completed | blocked
- Inputs used: danh sách artifact/code đã đọc.
- Outputs produced: file backend/database/test đã tạo hoặc sửa, và `.delivery/tasks/TASK-023/TASK-RESULT.md`.
- Validation evidence: exact commands và kết quả.
- Deviations: none hoặc mô tả sai lệch so với TASK-020/TASK-021/MASTER-PLAN.
- Blockers: none hoặc bằng chứng + quyết định cần owner xử lý.
- Scope change requests: none hoặc phạm vi/rationale.

### Skill/capability to run

- Capability: backend-implementation
- Next skill: `$implement-backend`

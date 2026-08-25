---
artifact: TEST-REPORT.md
version: "1.0"
owner: verify-feature
status: in-review
updated_at: "2026-08-24T22:35:14+07:00"
task_id: TASK-025
depends_on: [TASK-PACKET.md, TASK-020, TASK-021, TASK-022, TASK-023, TASK-024]
---

# TASK-025 Test Report - Verification CR-004 Object Labeling

## Traceability

- Task: TASK-025 Verification End-to-End cho CR-004 Object Labeling.
- Linked requirements: REQ-005, REQ-007, CR-004.
- Packet: `.delivery/tasks/TASK-025/TASK-PACKET.md` status ready.
- Design inputs: TASK-020 database design approved, TASK-021 API contract approved, TASK-022 UI/UX outputs consumed through approved TASK-022 result.
- Implementation inputs: TASK-023 backend result approved, TASK-024 frontend result approved.
- Main acceptance target: import ảnh/video thật, chọn frame video, vẽ/sửa/xóa bbox, label CRUD + soft delete/restore, system label lock, persisted reload từ DB, và sync zone rules mặc định `cấm`.

## Test Environment

- Project root: `D:\Hilab\Project34`.
- Date/time: `2026-08-24T22:35:14+07:00`.
- Shell: PowerShell.
- Backend test runner: `.\venv\Scripts\python.exe -m pytest`.
- Frontend checks: `npm --prefix frontend run lint`, `npx --prefix frontend tsc -p frontend/tsconfig.json --noEmit`, `npm --prefix frontend run build`.
- Sandbox note: `npm --prefix frontend run build` failed in sandbox with Vite/esbuild `spawn EPERM`; rerun ngoài sandbox được phép và pass.

## Acceptance Results

| Acceptance criterion | Result | Evidence |
|---|---|---|
| Import ảnh/video thật qua API/storage và UI hiển thị source thật thay mock/local state | Partial pass | Code review thấy `ObjectLabelingTab` dùng `uploadDatasetSource()` và `fetchDatasetSources()`. Backend source upload endpoint có managed storage. Chưa chạy browser/manual upload vì verification không khởi động UI trong turn này. |
| Video source chọn/scrub frame đúng và bbox sample tạo trên frame đã chọn | Partial pass | `ObjectLabelingTab` dùng `fetchDatasetFrame()` và `frameIndex`; backend frame endpoint có header frame metadata. Chưa có automated/browser E2E cho video source. |
| Vẽ, sửa, xóa bbox sample, batch atomic, reload persisted samples từ DB | Passed | `python -m pytest backend/tests/test_dataset_object_labeling.py backend/tests/test_dataset_zone_sync.py -q` pass 6 tests; code review thấy UI dùng `batchCreateDatasetSamples`, `updateDatasetSample`, `deleteDatasetSample`, `fetchDatasetSamples`. |
| Tạo/sửa/soft delete/restore label custom, uniqueness không phân biệt hoa/thường, sample_count persisted | Passed | Backend scoped tests pass; TASK-024 evidence ghi label CRUD frontend pass type/build. |
| System labels bị khóa | Passed | `test_system_labels_are_seeded_and_locked` pass. |
| Sync zone rules mặc định `cấm` và không để stale label key sau delete/restore flows | Passed with caveat | Backend zone sync tests pass; TASK-024 fix evidence cleanup stale forbidden classes ở frontend. |
| Frontend tab `Nhãn đối tượng` không còn phụ thuộc mock/local-only state cho media source, labels, bbox samples | Passed for active tab | Active render `subTab === 'obj'` dùng `<ObjectLabelingTab />`; legacy block local state nằm sau `{false && subTab === 'obj'}` nên không render. |
| Strict schema contract adherence giữa backend API và frontend consumers | Failed | BUG-001: frontend chỉ có TypeScript interfaces, không có Zod/runtime parser; `npm --prefix frontend ls zod` empty. |

## Integration and E2E

- Backend scoped integration: `python -m pytest backend/tests/test_dataset_object_labeling.py backend/tests/test_dataset_zone_sync.py -q`
  - Exit code: 0.
  - Result: `6 passed, 1 warning in 0.83s`.
- Full backend regression: `.\venv\Scripts\python.exe -m pytest backend/tests -q`
  - Exit code: 0.
  - Result: `55 passed, 21 warnings in 94.25s`.
- Frontend type/lint: `npm --prefix frontend run lint`
  - Exit code: 0.
  - Output chính: `tsc --noEmit`.
- Frontend explicit TypeScript check: `npx --prefix frontend tsc -p frontend/tsconfig.json --noEmit`
  - Exit code: 0.
- Frontend production build in sandbox: `npm --prefix frontend run build`
  - Exit code: 1.
  - Environment failure: `Error: spawn EPERM` khi Vite/esbuild load config.
- Frontend production build ngoài sandbox: `npm --prefix frontend run build`
  - Exit code: 0.
  - Result: `41 modules transformed`, `built in 1.39s`.
- Verification artifact validator: `python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-025`
  - Exit code: 1.
  - Result: `ERROR: requires approved upstream artifact: REQUIREMENTS.md`.
  - Note: `.delivery/REQUIREMENTS.md` hiện có frontmatter `status: in-review`; verification task không promote upstream artifacts.

## Edge Cases

- Batch atomic validation: covered by backend test; invalid bbox làm batch fail và không persist sample.
- Image source frame normalization: covered by backend test; image sample không truyền frame được normalize về `0`.
- Inactive/deleted label cannot be used for samples: covered by backend test; error code `LABEL_INACTIVE`.
- Duplicate label names case-insensitive: covered by backend zone sync test; error code `DUPLICATE_LABEL_NAME`.
- Custom label in zone rules cannot be soft deleted: covered by backend test; error code `LABEL_IN_USE_BY_ZONE`.
- Video frame out-of-range and binary frame headers: code review only; chưa có automated E2E evidence trong task này.

## Regression

- Dataset backend scoped regression passed.
- Full backend suite passed: `55 passed`.
- Frontend typecheck and build passed ngoài sandbox.
- No production code was changed by verification.
- Static boundary scan did not find frontend imports of backend DB clients or Node-native modules for the active CR-004 object labeling component. API base URL uses `import.meta.env.VITE_API_BASE_URL`, not backend secrets.

## Evidence

- `backend/tests/test_dataset_object_labeling.py`: system label lock, atomic batch, sample_count recompute, inactive label guard.
- `backend/tests/test_dataset_zone_sync.py`: zone sync default forbidden, rename propagation, duplicate label guard.
- `frontend/src/components/zone/ObjectLabelingTab.tsx`: active object-labeling UI consumes dataset API services for labels, sources, frames, samples and zone sync.
- `frontend/src/services/api.ts`: dataset endpoints use response envelope helper but only cast JSON response types.
- `frontend/src/contracts/api/dataset.schema.ts`: TypeScript interfaces only; no Zod/runtime validators.
- `npm --prefix frontend ls zod`: no `zod` dependency installed.
- `rg -n "zod|parse\\(|safeParse|dataset\\.schema|readDatasetJson|ApiResponse" frontend\\src`: no dataset runtime parser found.
- `python D:\Skill\SKILLs\verify-feature\scripts\validate_feature_verification.py D:\Hilab\Project34 TASK-025`: validator format/output checks pass far enough to expose only upstream approval blocker, `REQUIREMENTS.md` status in-review.

## Defects

- `BUG-001.md`: Strict schema contract chưa được enforce bằng Zod/runtime parser.

## Verdict

failed

Feature behavior has strong automated regression evidence and build evidence, but verification fails overall because strict machine-verifiable schema contract adherence is not implemented in the frontend consumer layer.

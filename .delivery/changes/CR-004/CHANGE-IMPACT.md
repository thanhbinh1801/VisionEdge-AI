---
artifact: CHANGE-IMPACT.md
version: "1.0"
owner: assess-change-impact
status: approved
updated_at: "2026-08-24T18:30:00+07:00"
change_id: CR-004
depends_on: [REQUIREMENTS.md, MASTER-PLAN.md, docs/contracts/db/schema.sql]
---

# Đánh giá Ảnh hưởng Thay đổi (Change Impact Assessment) cho CR-004

## Ghi chú thực thi skill
- Requested skill: `assess-change-impact`
- Status: không có trong danh sách skill của workspace hiện tại vào ngày 2026-08-24.
- Fallback executed: đọc nhanh context được yêu cầu và tạo artifact đánh giá ảnh hưởng trong `.delivery/changes/CR-004`; không design chi tiết và không sửa code production.

## Tóm tắt thay đổi
- Business delta: Tab `Cài đặt` phần `Nhãn đối tượng` phải chuyển từ mock/local state sang flow thật end-to-end: import ảnh/video, chọn frame video, vẽ bbox, tạo/sửa/xóa nhãn custom, lưu/tải lại bbox samples từ DB, và đồng bộ nhãn custom vào danh sách loại đối tượng của zone rules.
- Phạm vi focus: `Zone & Tag Settings` sub-tab `Nhãn đối tượng`, dataset/custom-label APIs, DB persistence cho `custom_labels`, `dataset_sources`, `bbox_samples`, và đồng bộ danh sách nhãn vào cấu hình zone.
- Affected requirements: `REQ-005`, `REQ-007`
- Related existing scope: CR-001 đã mô tả BBox Dataset Tool ở mức nghiệp vụ; CR-004 làm rõ yêu cầu hiện thực hóa luồng thật thay vì minh họa bằng dữ liệu giả.

## Bằng chứng baseline
- RFP/Prototype mục `2.3. Cài đặt` yêu cầu `Nhãn đối tượng`: import hình hoặc video, chọn khung hình, vẽ ô bao, chọn loại người/hình dáng xe, đặt tên nhãn, lưu mẫu, và nhãn đã lưu xuất hiện trong danh sách loại của mọi zone.
- `.delivery/REQUIREMENTS.md` `REQ-007` đã phê duyệt behavior tương tự, gồm batch nhiều bbox trên cùng frame, timeline scrubber video, và đồng bộ nhãn mới vào danh sách phân loại đối tượng cho tất cả zone.
- `.delivery/MASTER-PLAN.md` `TASK-012` completion gate có `Dataset BBox Labeling Tool kèm video scrubber`, nhưng task hiện chưa tách riêng phần chuyển mock/local sang API/DB thật.
- `frontend/src/pages/ZoneTagSettings.tsx` hiện có UI bbox drawing, video frame scrubber dùng `fetchZoneFrame`, thêm/sửa/xóa nhãn trong danh sách, và nút lưu mẫu.
- `frontend/src/context/AppContext.tsx` hiện giữ `objLabels`, `annSources`, `annSamples` bằng `useState` với `defaultObjLabels`, `defaultAnnSources`, `defaultAnnSamples`; `addObjLabel`, `renameObjLabel`, `deleteObjLabel`, `addAnnSource`, `addAnnSample`, `updateAnnSampleLabel`, `deleteAnnSample`, `saveAnnSamples` đều là local state, chưa gọi dataset API.
- `frontend/src/services/api.ts` chưa có client functions cho `/dataset/labels`, `/dataset/sources`, `/dataset/samples`, `/dataset/sync-zones`; chỉ có zone/vehicle/event/kpi/frame APIs.
- `backend/app/api/v1/dataset.py` đã có endpoint nền tảng: `GET /labels`, `GET/POST /sources`, `GET/POST/DELETE /samples`, `POST /sync-zones`.
- `backend/database/models.py`, `backend/database/repository.py`, và `docs/contracts/db/schema.sql` đã có các bảng/model `custom_labels`, `dataset_sources`, `bbox_samples`, cùng repository lưu batch sample và sync custom labels vào zones.

## Tác động trực tiếp
- `REQ-007` cần được cập nhật nghĩa từ "React state hook" sang "UI state có persistence qua API/DB"; import media phải tạo `dataset_sources` thật, bbox samples phải lưu/tải lại từ `bbox_samples`, và thao tác sửa/xóa nhãn custom phải đi qua contract rõ ràng.
- `REQ-005` cần làm rõ danh sách loại đối tượng trong zone rules gồm 8 loại mặc định cộng nhãn custom đã đồng bộ; zone cache/invalidation của CR-003 cần nhận được thay đổi khi custom label làm đổi `allowed_classes` hoặc `forbidden_classes`.
- `.delivery/API-CONTRACT.md` và `docs/contracts/api/api-schema.json` cần chuẩn hóa dataset API envelope, endpoint upload/import media, CRUD custom labels, batch save/update/delete bbox samples, và response đồng bộ zone rules.
- `docs/contracts/db/schema.sql` có thể cần migration bổ sung nếu design quyết định lưu file thật trong managed media storage, cần trạng thái import, MIME type, checksum, frame metadata, hoặc quan hệ FK chặt giữa `bbox_samples.label_id` và `custom_labels.id`.
- `backend/app/api/v1/dataset.py` cần được nâng từ API nền tảng sang flow hoàn chỉnh: xử lý upload file ảnh/video, lấy frame preview cho video source đã import, CRUD nhãn custom đầy đủ, validation bbox, và đảm bảo save sample cập nhật sample_count nhất quán.
- `backend/database/repository.py` cần kiểm tra lại tính đúng đắn của `sample_count`, rename/delete label, delete sample decrement/recompute count, và sync labels-to-zones không làm mất cấu hình zone hiện hữu.
- `frontend/src/services/api.ts` cần thêm dataset service client và type mapping giữa UI ids/kind (`nguoi`, `xe`) với backend category (`person`, `vehicle_shape`).
- `frontend/src/pages/ZoneTagSettings.tsx` và `frontend/src/context/AppContext.tsx` cần thay local/mock flow bằng load/save thật, optimistic state có rollback hoặc reload, loading/error states, và reload samples khi đổi source/frame/label.

## Tác động task bắc cầu
- `TASK-002` — module `none` — status `ready` — `transitive` candidate — packet action `supplement-contract`
- `TASK-003` — module `none` — status `ready` — `transitive` candidate — packet action `schema-review`
- `TASK-006` — module `database-storage` — status `ready` — `direct` candidate — packet action `create-follow-up`
- `TASK-012` — module `web-ui` — status `ready` — `direct` candidate — packet action `split-or-supersede`
- `TASK-015` — module `none` — status `ready` — `transitive` candidate — packet action `extend-verification`
- Proposed new task range: create CR-004 follow-up tasks after approval, likely `TASK-020` through `TASK-023` for API/DB design supplement, backend dataset implementation, frontend dataset integration, and verification.

## Bằng chứng không ảnh hưởng
- `REQ-001` luồng LPR cổng không đổi trực tiếp; chỉ có thể bị ảnh hưởng gián tiếp nếu object type enum dùng chung được mở rộng.
- `REQ-002`, `REQ-003`, `REQ-004`, `REQ-009` không đổi behavior cảnh báo/event realtime trực tiếp; chúng chỉ cần tương thích với danh sách object class mở rộng do custom labels.
- `TASK-016` đến `TASK-019` của CR-003 không cần mở lại nếu zone cache đã có cơ chế refresh sau zone CRUD; CR-004 chỉ cần gọi đúng cơ chế đó khi sync labels thay đổi zone rules.
- AI assistant `REQ-008` không cần đổi ngay trong CR-004; dataset labels không phải event evidence/history cho text-to-SQL ở phạm vi này.

## Tác động contract và artifact

### Impact on `.delivery/REQUIREMENTS.md`
- Cần thêm audit trail `CR-004`.
- Cần cập nhật `REQ-007` để ràng buộc API/DB thật cho import media, chọn frame video, bbox samples, CRUD nhãn custom, reload persisted data, và sync vào zone rules.
- Cần cập nhật `REQ-005` để danh sách loại đối tượng của zone lấy từ object taxonomy mở rộng gồm nhãn custom, không chỉ 8 loại mặc định.

### Impact on `.delivery/MASTER-PLAN.md`
- Không sửa trong bước này.
- Sau khi CR-004 được duyệt, nên bổ sung wave mới sau CR-003 verification hoặc tạo supplemental plan riêng để tránh rewrite các task đã hoàn tất.
- `TASK-012` nên có follow-up thay vì chỉnh lịch sử completion gate cũ.

### Impact on API contracts
- Cần xác định endpoint upload/import media thật: có thể là `POST /dataset/sources` multipart upload hoặc tách `POST /dataset/uploads` rồi `POST /dataset/sources`.
- Cần chuẩn hóa CRUD nhãn custom: list/create/update/delete label theo id, category, sample_count, timestamps.
- Cần chuẩn hóa sample contract: create batch, update sample label/bbox/frame/source, delete sample, list theo `label_id`, `source_id`, `frame_index`.
- Cần xác định response sau `sync-zones`: zone ids affected, cache version hoặc invalidation result, và danh sách class mới đưa vào zone rules.

### Impact on DB contracts
- Hiện schema đã đủ bảng nền tảng cho custom labels, dataset sources, bbox samples.
- Cần review bổ sung FK `bbox_samples.label_id -> custom_labels.id`, chính sách delete/rename label, và metadata file upload nếu source URL không còn là mock path.
- Cần quy định rõ tọa độ bbox là phần trăm canvas hay pixel gốc; frontend hiện dùng phần trăm 0-100.

### Impact on frontend implementation scope
- Thay `defaultObjLabels/defaultAnnSources/defaultAnnSamples` bằng dữ liệu load từ backend, vẫn có fallback rỗng hoặc seed nếu API lỗi.
- Import ảnh/video phải dùng file picker thật và tạo dataset source thật thay vì tạo `src${Date.now()}` với tint giả.
- Video frame selector phải lấy frame từ source đã import, không suy từ `BAI-KIEM/GATE-01` theo tên file.
- Save mẫu phải gọi API batch save rồi reload sample/label counts; delete sample và đổi label sample phải persist.
- Create/rename/delete label phải persist và cập nhật zone rule options sau sync.

## Khóa chọn lọc
- Khóa chọn lọc các module/artifact: `web-ui`, `api-gateway`, `database-storage`, `docs/contracts/api`, `docs/contracts/db`, `zone-rules`.
- Không khóa luồng LPR, chatbot, alert dispatcher, hoặc area metadata runtime ngoài yêu cầu tương thích object class/custom label.

## Hành động packet
- Tạo change request artifact `CR-004/CHANGE-IMPACT.md` ở trạng thái `in-review`.
- Không cập nhật `REQUIREMENTS.md`, `MASTER-PLAN.md`, API contract, DB schema, hoặc production code trong bước này.
- Sau khi duyệt CR-004, tạo task packets mới:
  - `TASK-020`: design supplement cho dataset/custom-label API + DB migration decision.
  - `TASK-021`: backend implementation cho upload/import, custom label CRUD, bbox sample persistence, zone sync/cache invalidation.
  - `TASK-022`: frontend implementation nối `ZoneTagSettings` với API thật và reload persisted samples.
  - `TASK-023`: verification cho import media, video frame selection, bbox CRUD, label CRUD, DB reload, và zone rule synchronization.

## Quyết định cần owner xác nhận
- Media import sẽ lưu file vào local managed storage của backend, đường dẫn public `/media/...`, hay chỉ lưu URL/source path do người dùng cung cấp?
- Với nhãn custom mới, mặc định sync vào zone rules ở trạng thái `forbidden`, `allowed`, hay chỉ thêm option chưa chọn?
- Có cho phép xóa label khi label đang có samples hoặc đang xuất hiện trong zone rules không; nếu có thì cascade, archive, hay block?
- Cần hỗ trợ update bbox geometry sau khi đã lưu DB trong CR-004 hay chỉ delete/recreate sample?
- Object taxonomy runtime của AI pipeline sẽ dùng nhãn custom như class inference thật, hay CR-004 chỉ quản lý dataset/rules UI và lưu mẫu huấn luyện?

## Thứ tự cập nhật đề xuất
1. Phê duyệt `.delivery/changes/CR-004/CHANGE-IMPACT.md`.
2. Tạo supplemental plan/task packets cho CR-004, không sửa production code trong bước đánh giá.
3. Cập nhật `REQUIREMENTS.md` audit trail và refine `REQ-005`, `REQ-007`.
4. Thiết kế chi tiết API/DB/UI cho CR-004.
5. Sau khi design được duyệt mới triển khai backend, frontend và verification.

## Kế hoạch xác minh
- Traceability: CR-004 phải map tối thiểu tới `REQ-005`, `REQ-007`, `TASK-012`, `TASK-006`, và task follow-up mới.
- Contract validation: schema API/DB phải mô tả được import media, label CRUD, sample CRUD, reload persisted samples, và zone sync.
- Frontend acceptance: reload trang vẫn thấy labels/sources/samples đã lưu; samples theo frame video hiển thị đúng; tạo/sửa/xóa nhãn phản ánh trong zone type list.
- Backend acceptance: sample_count nhất quán sau create/delete/update; sync zones không mất allowed/forbidden hiện hữu; DB là source of truth cho dataset labels/samples.

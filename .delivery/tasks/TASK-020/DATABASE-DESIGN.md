---
artifact: DATABASE-DESIGN.md
version: "1.0"
owner: design-database
status: approved
updated_at: "2026-08-24T19:34:05+07:00"
task_id: TASK-020
depends_on: [TASK-PACKET.md, REQUIREMENTS.md, ARCHITECTURE.md, DOMAIN-MODEL.md]
---

# TASK-020 Thiết kế Database - Luồng gắn nhãn đối tượng thật

## Traceability

- REQ-005: Zone rules phải bao gồm 8 nhãn hệ thống bị khóa và các nhãn custom đang hoạt động. Khi nhãn custom được tạo mới hoặc restore, dữ liệu phải được đồng bộ vào mọi zone với trạng thái mặc định `forbidden` và cho phép backend refresh zone runtime cache.
- REQ-007: Contract dữ liệu bao phủ import ảnh/video thật, metadata source, frame video đang chọn, bbox samples, label CRUD, soft delete/restore nhãn custom, uniqueness không phân biệt hoa/thường, batch validation, reload dữ liệu persisted, tính nhất quán `sample_count`, và rule khóa sửa/xóa nhãn hệ thống.
- CR-004: Thiết kế này chuyển `Cài đặt > Nhãn đối tượng` từ mock/local state sang storage thật bằng SQLite + local disk, nhưng không cam kết AI realtime nhận diện class custom mới trong phạm vi CR-004.

## Current Data Context

Data layer hiện đã có `custom_labels`, `dataset_sources`, và `bbox_samples`, nhưng đây mới là nền tảng từ CR-001. `custom_labels` chỉ có `label_name UNIQUE` phân biệt hoa/thường, chưa có phân biệt `system/custom`, chưa có soft-delete lifecycle, restore metadata hay `label_key` chuẩn hóa. `bbox_samples.label_id` chưa có FK tới label table, nên rename/delete label không có integrity rõ ràng. `dataset_sources.url` có thể là demo path, nhưng schema chưa mô tả file upload thật, MIME type, file size, checksum, original filename, import status, frame metadata, hay public path an toàn.

Source of truth của CR-004 là SQLite và local disk. Database chỉ lưu metadata và quan hệ; bytes của ảnh/video nằm trong managed backend storage và được tham chiếu bằng relative/public path. Zone cache không thuộc persisted dataset schema, nhưng label sync phải cập nhật `zones.allowed_classes` / `zones.forbidden_classes` trong cùng business transaction trước khi downstream backend refresh cache.

## Existing Schema Evidence

- `docs/contracts/db/schema.sql`: định nghĩa `custom_labels(id, label_name UNIQUE, category, sample_count, created_at, updated_at)`, `dataset_sources(id, name, kind, url, duration_seconds, total_frames, created_at)`, và `bbox_samples(id, label_id, source_id FK, frame_index, x, y, w, h, category, label_name, created_at)`.
- `backend/database/models.py`: model SQLAlchemy khớp schema hiện tại; `BBoxSample.source_id` có relationship tới `DatasetSource`, còn `BBoxSample.label_id` vẫn là plain string, chưa có `ForeignKey`.
- `backend/database/repository.py`: `create_or_increment()` tìm label theo exact-case name và tăng `sample_count`; `save_samples_batch()` tạo label như side effect; `delete_sample()` chưa decrement/recompute `sample_count`; `sync_custom_labels_to_zones()` append mọi label vào `forbidden_classes` mà chưa loại deleted/inactive labels.
- `backend/app/api/v1/dataset.py`: đã có baseline `GET /labels`, `GET/POST /sources`, `GET/POST/DELETE /samples`, `POST /sync-zones`; còn thiếu upload metadata, label CRUD đầy đủ, soft delete/restore, bbox update, atomic batch validation, và frame retrieval theo imported dataset source.
- `backend/tests/test_database.py`: có test source creation, batch sample save, zone sync; chưa cover case-insensitive uniqueness, soft delete/restore, system-label immutability, FK integrity, sample_count recomputation, hay persisted media metadata.
- `backend/database/engine.py`: bật `PRAGMA foreign_keys=ON` và WAL mode, nên migration có thể dựa vào FK enforcement và serialized additive DDL.

## Entities

- `object_labels`: taxonomy chuẩn cho object labels, thay nghĩa hẹp hiện tại của `custom_labels`. Cột cần có: `id`, `label_key`, `label_name`, `label_type`, `category`, `sample_count`, `is_active`, `deleted_at`, `created_at`, `updated_at`. `label_key` là key đã `lower(trim(...))`. `label_type` là `system` hoặc `custom`. `category` là `person`, `vehicle_shape`, hoặc `custom`.
- `dataset_sources`: metadata media đã import. Cột cần có: `id`, `name`, `kind`, `storage_path`, `public_url`, `original_filename`, `mime_type`, `file_size_bytes`, `sha256`, `duration_seconds`, `total_frames`, `fps`, `width`, `height`, `import_status`, `import_error`, `created_at`, `updated_at`.
- `bbox_samples`: annotation samples persisted. Cột cần có: `id`, `label_id`, `source_id`, `frame_index`, `frame_timestamp_seconds`, `x`, `y`, `w`, `h`, `coordinate_space`, `created_at`, `updated_at`. `coordinate_space` là `percent_0_100` vì frontend canvas hiện lưu tọa độ phần trăm.
- `zones`: bảng hiện hữu vẫn là source of truth cho zone rules. `allowed_classes` và `forbidden_classes` tiếp tục là JSON arrays để tương thích zone cache/vision pipeline.
- `dataset_media_files`: không tách bảng riêng trong CR-004; lifecycle file nằm trong `dataset_sources` để tránh thêm abstraction khi chưa có yêu cầu deduplicate file vật lý.

## Relationships

- Một `dataset_source` sở hữu nhiều `bbox_samples`; xóa source thì cascade samples.
- Một `object_label` sở hữu nhiều `bbox_samples`; xóa label trong CR-004 là soft-delete cho custom label, còn system label bị cấm xóa.
- Một custom label có thể xuất hiện trong nhiều zone qua JSON arrays. Đây là quan hệ denormalized để giữ compatibility với zone cache; integrity do repository transaction đảm bảo.
- System labels được seed một lần, có thể được dùng để gắn samples, nhưng không được sync như custom additions.
- Rename label cập nhật `object_labels.label_name` và `label_key`; samples vẫn trỏ bằng `label_id`, còn repository phải cập nhật các zone class array từ key/name cũ sang key/name mới atomically.

## Invariants and Constraints

- `object_labels.label_key` unique trên toàn bộ labels, không phân biệt hoa/thường, kể cả soft-deleted labels.
- `label_type = system` không được rename, soft delete hay hard delete qua CR-004 APIs; vẫn được gắn bbox samples và tăng `sample_count`.
- `label_type = custom` được create, rename, soft delete và restore. Soft delete set `is_active = 0`, `deleted_at`; restore set `is_active = 1`, `deleted_at = null`.
- Custom label đang nằm trong bất kỳ `allowed_classes` hoặc `forbidden_classes` nào không được soft delete.
- `bbox_samples.label_id` phải FK tới `object_labels.id`; `bbox_samples.source_id` phải FK tới `dataset_sources.id`.
- `bbox_samples.x/y` nằm trong `[0,100]`; `w/h > 0`; `x + w <= 100`; `y + h <= 100`. DB CHECK enforce geometry cơ bản, API enforce ngưỡng bbox quá nhỏ.
- Image source có thể để `frame_index` / `frame_timestamp_seconds` null và API hiểu là frame 0. Video source bắt buộc có `frame_index >= 0`.
- `sample_count` là dữ liệu derived, phải bằng số samples hiện có của label; create/update/delete sample phải recompute hoặc adjust trong cùng transaction.
- Batch save bbox samples là atomic: chỉ cần một item invalid thì toàn bộ batch không được persist.

## Access Patterns and Indexes

- List labels cho UI: mặc định filter `is_active`, tùy chọn include deleted cho restore flow; order system trước custom. Index: `(is_active, label_type, label_key)`.
- Enforce uniqueness khi create/rename/restore: lookup bằng `label_key`. Index bắt buộc: unique `label_key`.
- Reload sources sau khi mở lại trang: list `dataset_sources` order `created_at DESC`. Index: `created_at DESC`.
- Load samples theo source/frame: query `source_id + frame_index`, order `created_at DESC`. Index: `(source_id, frame_index, created_at DESC)`.
- Load samples/count theo label: giữ index `idx_bbox_samples_label` trên FK-backed `label_id`.
- Sync labels to zones: scan active custom labels và update mọi zones. Không thêm JSON membership index vì đây là control-plane, không nằm trong hot path từng frame.
- Idempotent media import: optional lookup bằng `sha256`; index `idx_dataset_sources_sha256` non-unique để API quyết định reuse hay tạo source mới.

## Transaction and Concurrency

- Label create/rename/restore chạy trong một transaction: validate uniqueness, mutate label, sync active custom labels vào zones khi cần, commit DB; sau commit API refresh zone cache.
- Nếu cache refresh fail sau commit, DB vẫn là source of truth; API trả lỗi/warning recoverable để retry sync/cache refresh.
- Label soft delete chạy trong một transaction: kiểm tra zone JSON arrays, set inactive fields, giữ nguyên samples; nếu label còn trong zone rules thì abort.
- Batch sample create/update validate toàn bộ batch trước, persist toàn bộ thay đổi, rồi recompute `sample_count` cho affected labels trong cùng transaction.
- Sample delete xóa sample và recompute `sample_count` của label cũ trong cùng transaction.
- SQLite WAL đã bật; các thao tác CR-004 là control-plane writes ngắn. Video frame loop không được đọc các bảng này mỗi frame.

## Migration Strategy

- Chạy schema migration tuần tự trong pre-implementation wave trước `TASK-023`; không task backend/frontend song song nào được mutate schema khi migration này chưa xong.
- Migration version: `1.2.0-cr004-object-labeling`.
- Additive DDL cho `custom_labels`: thêm `label_key`, `label_type DEFAULT 'custom'`, `is_active DEFAULT 1`, `deleted_at`, bảo toàn `updated_at`; backfill `label_key = lower(trim(label_name))`.
- Contract gọi entity là `object_labels`. Implementation có thể rename physical table từ `custom_labels` sang `object_labels`, hoặc giữ tên bảng `custom_labels` với semantic mới để giảm churn; cả hai phải cập nhật ORM/repository nhất quán trong cùng migration wave.
- Seed 8 system labels với stable keys: `person`, `container`, `truck`, `forklift`, `crane`, `car`, `motorbike`, `bicycle`.
- Rebuild `bbox_samples` nếu SQLite không thể add FK/CHECK constraints in-place. Bảng mới cần FK tới label table, FK `source_id REFERENCES dataset_sources(id) ON DELETE CASCADE`, thêm `frame_timestamp_seconds`, `coordinate_space`, `updated_at`.
- Khi rebuild, map sample cũ bằng `label_id` nếu match; nếu không thì map bằng lowercase `label_name`, tạo custom label nếu cần. `label_id` là identity chuẩn.
- Add columns cho `dataset_sources`: `storage_path`, `public_url`, `original_filename`, `mime_type`, `file_size_bytes`, `sha256`, `fps`, `width`, `height`, `import_status`, `import_error`, `updated_at`; backfill từ `url` và set `import_status = 'ready'`.
- Tạo indexes: `idx_object_labels_label_key` unique, `idx_object_labels_active_type_key`, `idx_dataset_sources_created_at`, `idx_dataset_sources_sha256`, `idx_bbox_samples_source_frame`, và recreate `idx_bbox_samples_label`.
- Recompute toàn bộ `sample_count` sau migration, rồi insert row vào `schema_migrations`.

## Rollback Strategy

- Trước migration phải backup SQLite DB file và manifest thư mục media managed.
- Nếu rollback trước khi có CR-004 user data, drop indexes mới, restore `bbox_samples` từ backup table, rebuild/drop columns mới nếu cần, và đưa `schema_migrations` về version trước.
- Nếu rollback sau khi user đã import media hoặc gắn samples, phải export `dataset_sources`, labels, samples và media manifest ra JSON/CSV trước; chỉ restore backup sau khi owner approved vì có nguy cơ mất dữ liệu mới.
- Rollback cache sync là non-destructive: zone JSON arrays trong DB vẫn là source of truth và cache có thể refresh lại từ DB.

## Security and Privacy

- DB chỉ lưu backend-managed relative paths/public URLs; không lưu absolute filesystem path từ browser.
- `original_filename` chỉ dùng để hiển thị; không dùng trực tiếp để tạo storage path.
- `storage_path` phải nằm trong managed media root như `data/dataset/`; API download/frame phải validate resolved path nằm trong root này.
- `sha256`, MIME type và file size phục vụ audit/validation. DB không lưu raw bytes của ảnh/video.
- Labels và bbox samples có thể lộ ngữ cảnh camera/vận hành; authz là ngoài scope TASK-020 nhưng API sau này không được expose unmanaged paths hay deleted labels mặc định.

## Performance Risks

- Video lớn làm list source nặng nếu API nhúng frame data inline. Chỉ lưu metadata trong `dataset_sources`; frame extraction là media service/API operation riêng.
- Recompute global `sample_count` sau mỗi write sẽ tốn kém khi dữ liệu tăng; chỉ recompute affected labels, full recompute chỉ dùng cho migration/repair.
- Zone JSON arrays không có FK/index hiệu quả trong SQLite; chấp nhận vì sync là control-plane hiếm, còn frame loop dùng zone cache.
- Case-insensitive uniqueness nếu chỉ enforce trong app sẽ race-prone; phải có persisted `label_key` unique index.
- Add FK vào `bbox_samples` có thể fail nếu đang có orphan rows; migration phải map, clean hoặc quarantine orphan samples trước khi tạo bảng mới.

## Applicability Checklist

- Entities: đã bao phủ object labels, dataset sources, bbox samples và zones hiện hữu.
- Relationships and cardinality: đã mô tả label-to-samples, source-to-samples, và label-to-zone rules dạng denormalized.
- Ownership and lifecycle: đã mô tả source-owned samples, custom label soft delete/restore, locked system labels và local media references.
- Uniqueness and nullability: đã mô tả label keys, required source/sample fields, image/video frame nullability.
- Integrity constraints: đã mô tả FK, CHECK, unique indexes, repository validation và sample_count recomputation.
- Access patterns: đã lấy từ UI reload, frame scrubber, label CRUD, sample CRUD và zone sync.
- Indexes: đã có index vật chất và ghi chú write-cost.
- Transactions and concurrency: đã bao phủ batch atomicity, label lifecycle, zone sync và SQLite WAL transactions ngắn.
- Migration serialization: đã yêu cầu một migration tuần tự trước implementation.
- Rollback: đã có backup, phân biệt rollback trước/sau user data, và export trước destructive rollback.
- Security/privacy: đã bao phủ path safety, file metadata, managed storage và deleted-label visibility.
- Non-applicable topics: replication, sharding, retention/purge schedule và true AI model retraining không áp dụng cho CR-004.

## Open Questions

- Không có blocker. Requirements đã approved quyết định local backend storage, sync mặc định `forbidden`, soft delete/restore không giới hạn thời gian, bbox edit support, và không yêu cầu realtime AI inference cho custom labels trong CR-004.

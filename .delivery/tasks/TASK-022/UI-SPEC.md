---
artifact: UI-SPEC.md
version: "1.0"
owner: design-ui-ux
status: in-review
updated_at: "2026-08-24T20:14:24+07:00"
task_id: TASK-022
depends_on: [TASK-PACKET.md, REQUIREMENTS.md, DOMAIN-MODEL.md, TASK-020]
---

# TASK-022 Đặc tả UI - Cài đặt > Nhãn đối tượng

## Traceability

- REQ-005: `Nhãn đối tượng` phải đưa các nhãn custom đang hoạt động vào danh sách rule của mọi zone với trạng thái mặc định là `cấm` sau khi tạo mới hoặc restore. UI phải hiển thị trạng thái đồng bộ và làm rõ tác động tới zone rule trước khi người dùng rời luồng cài đặt.
- REQ-007: UI phải hỗ trợ import ảnh/video thật, tải lại source/sample đã lưu, scrub frame cho video, nhiều BBox sample trên cùng một frame, sửa/xóa sample đã lưu, khóa sửa/xóa nhãn hệ thống, tạo/sửa tên/soft delete/restore nhãn custom, lỗi trùng tên không phân biệt hoa/thường, batch validation dạng atomic, và không hứa rằng nhãn custom mới được AI realtime nhận diện nếu chưa huấn luyện model.
- CR-004: Subtab chuyển từ mock/local state sang media, labels và samples được backend persist. TASK-024 mới triển khai production; TASK-022 chỉ đặc tả UI/UX.

## Screen and Component Inventory

### Vị trí màn hình

- Route/tab hiện có: `Cài đặt` -> subtab `Nhãn đối tượng` trong `ZoneTagSettings`.
- Các subtab lân cận giữ nguyên: `Gắn nhãn xe`, `Vẽ zone`.
- Bố cục desktop chính: bề mặt làm việc hai cột.
- Bố cục tablet/mobile: vùng source/annotation đứng trước, vùng quản lý nhãn nằm phía dưới.

### Cây component và ranh giới

- `ZoneTagSettingsPage` hoặc `ZoneTagSettings` hiện hữu: Client Component. Quản lý chọn subtab và compose feature gắn nhãn đối tượng. Với Vite React đây là route render phía client; không dùng RSC.
- `ObjectLabelingTab`: Client Component. Data container cho API hooks của object-labeling, state lựa chọn, dirty/pending state và điều phối lưu.
- `DatasetSourcePanel`: Client Component. Hiển thị danh sách ảnh/video đã import, tìm kiếm/lọc, source đang chọn, entry point import, trạng thái progress/error của import.
- `MediaImportDialog`: Client Component. File picker/drop zone, hiển thị validate MIME/dung lượng, progress upload và phục hồi lỗi import. Mutation mode: client fetch hook gọi schema API chặt chẽ từ TASK-021 khi có.
- `FrameScrubber`: Client Component. Chỉ hiển thị cho video source. Đọc metadata frame từ source đang chọn và phát ra `frame_index`. Hỗ trợ range input, nút bước, nhập frame thủ công, trạng thái loading/error.
- `AnnotationCanvas`: Client Component. Hiển thị ảnh hoặc frame video đang chọn; hỗ trợ vẽ BBox, chọn sample saved/pending, resize/move BBox đang chọn, xóa sample đang chọn và nudge bằng bàn phím.
- `SampleInspector`: Client Component. Sửa nhãn sample đang chọn và tóm tắt geometry; hiển thị trạng thái saved/pending và lỗi validation.
- `BatchSaveBar`: Client Component. Hiển thị số sample pending, thao tác lưu atomic, tóm tắt validation, discard/retry.
- `ObjectLabelList`: Client Component. Liệt kê nhãn hệ thống và custom, filter active/deleted, sample count, nhãn đang chọn, control bị khóa cho nhãn hệ thống và control restore cho nhãn custom đã xóa.
- `CustomLabelDialog`: Client Component. Tạo/đổi tên nhãn custom với validation uniqueness không phân biệt hoa/thường.
- `DeleteLabelConfirmDialog`: Client Component. Chỉ xác nhận soft delete sau khi API cho biết nhãn không còn được dùng trong zone rules; nếu còn dùng thì hiển thị trạng thái blocked kèm danh sách zone liên quan.
- `ZoneSyncStatusBanner`: Client Component. Hiển thị kết quả sync sau create/restore/rename và cảnh báo cache refresh nếu backend trả về lỗi recoverable.

### Chế độ tích hợp dữ liệu

- Load dữ liệu ban đầu: client fetch hooks tải labels, dataset sources, samples của source đang chọn và metadata frame video đang chọn.
- Mutations: client fetch hooks gọi endpoint API chặt chẽ từ TASK-021. Khi TASK-021 chưa có, tên endpoint trong thiết kế chỉ là placeholder và phải thay bằng API contract đã duyệt.
- TASK-022 không giới thiệu Server Components, Server Actions hoặc production frontend code.

## UI States

### Dataset Sources

- Loading: danh sách source hiển thị skeleton rows; annotation canvas bị disabled với panel loading trung tính.
- Empty: first-run state có hành động import ảnh/video và không hiển thị dữ liệu demo giả.
- Ready: source đang chọn có active styling; metadata hiển thị loại media, original filename, kích thước nếu có, và sample count.
- Importing: row hiển thị progress, cancel nếu API hỗ trợ; nếu không thì cancel là `Not specified in source artifacts`.
- Import failed: row lỗi giữ filename và thông báo lỗi; người dùng có thể retry import hoặc xóa row lỗi.

### Annotation Canvas

- Chưa chọn source: canvas disabled với prompt chọn source.
- Đã chọn ảnh: render ảnh, frame hiện tại cố định là frame 0, ẩn scrubber.
- Đã chọn video: render frame đang chọn và hiển thị scrubber.
- Frame loading: nếu có frame cũ thì giữ lại ở trạng thái dimmed; tắt vẽ cho tới khi frame mới tải xong.
- Frame error: hiển thị retry control và giữ source đang chọn.
- Draw mode: bắt buộc có nhãn đang chọn; BBox mới xuất hiện dưới dạng pending sample.
- Chọn saved sample: hiển thị handle move/resize; inspector cho phép đổi nhãn hoặc xóa.
- Chọn pending sample: dùng cùng edit controls, nhưng trạng thái là pending và có thể discard trước khi lưu.
- Save success: xóa pending state và refresh sample counts từ API.

### Labels

- Nhãn hệ thống: hiển thị trước, có badge khóa, disabled rename/delete controls, vẫn chọn được để gắn sample.
- Nhãn custom active: chọn được để gắn sample, có action rename, soft delete và sample count.
- Nhãn custom deleted: mặc định ẩn; hiện trong filter restore; disabled cho sample mới cho tới khi restore.
- Nhãn vừa tạo/restore: xuất hiện trong danh sách active và kích hoạt zone sync status.
- Nhãn custom đang được dùng trong zone rules: action delete mở blocked state với danh sách zone đang dùng thay vì confirm.

## Responsive Rules

- Desktop >= 1100px: bố cục hai cột, vùng annotation khoảng 65%, vùng quản lý label/source khoảng 35%.
- Tablet 768-1099px: xếp `DatasetSourcePanel` phía trên `AnnotationCanvas`, label list nằm cột phải hoặc panel dưới tùy chiều rộng khả dụng.
- Mobile < 768px: một cột theo thứ tự import/source, frame scrubber, canvas, sample inspector, save bar, labels. Canvas giữ aspect ratio từ media metadata và không tràn chiều rộng viewport.
- Action bars được wrap thay vì ép chữ nhỏ dưới mức đọc được.
- Dialog dùng max width 640px trên desktop và dạng full-width sheet trên mobile.

## Validation and Error States

- Import từ chối MIME type không hỗ trợ, file rỗng, file quá dung lượng khi API có limit, và ảnh/video không đọc được metadata.
- BBox validation: bắt buộc có label, source, frame video nếu source là video, tọa độ nằm trong 0-100, width/height dương, và kích thước nhìn thấy tối thiểu ở UI. Ngưỡng tối thiểu chính xác là `Not specified in source artifacts`; TASK-024 phải theo TASK-021/API validation sau khi duyệt.
- Batch save là atomic: nếu một pending sample fail, không sample nào được đánh dấu saved; lỗi hiển thị theo từng sample và trong summary ở `BatchSaveBar`.
- Rename/create custom label validate tên không rỗng, display name đã trim, và uniqueness không phân biệt hoa/thường. Conflict message nhận diện trạng thái label hiện có khi API trả về.
- Người dùng không thể rename/delete nhãn hệ thống từ control enabled.
- Xóa nhãn custom bắt buộc confirm và bị block nếu nhãn xuất hiện trong bất kỳ zone rule nào.
- Restore nhãn custom kích hoạt sync; nếu sync/cache refresh trả warning, label vẫn restored và banner giải thích cách retry sync.

## Accessibility

- Subtab buttons dùng semantics `role="tablist"` / `role="tab"` hoặc button state tương đương có thể truy cập.
- Canvas có phương án bàn phím cho BBox đang chọn: phím mũi tên để nudge, Shift+mũi tên để resize, Delete yêu cầu xóa sample, Escape hủy drawing/selection.
- Mọi icon-only action phải có accessible name/tooltip.
- Dialog trap focus, đóng bằng Escape khi không có confirm phá hủy đang chờ, và trả focus về control đã mở dialog.
- Form inputs có label hiển thị và error text liên kết bằng `aria-describedby`.
- Màu sắc không phải kênh trạng thái duy nhất: locked, deleted, pending, saved, allowed/forbidden và error đều có text/icon indicator.
- Tiến trình upload/save/sync dùng polite `aria-live`; lỗi destructive dùng assertive announcement.

## Open Questions

- Endpoint API chính xác và response envelope đang chờ TASK-021.
- Giới hạn upload và codec được hỗ trợ chưa được chỉ định trong source artifacts.
- Ngưỡng BBox tối thiểu theo pixel/percentage chưa được chỉ định trong source artifacts.
- Kích thước thumbnail và hành vi zoom/pan canvas chưa được chỉ định trong source artifacts.

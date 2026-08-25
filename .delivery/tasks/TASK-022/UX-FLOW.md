---
artifact: UX-FLOW.md
version: "1.0"
owner: design-ui-ux
status: in-review
updated_at: "2026-08-24T20:14:24+07:00"
task_id: TASK-022
depends_on: [TASK-PACKET.md, REQUIREMENTS.md, DOMAIN-MODEL.md, TASK-020]
---

# TASK-022 Luồng UX - Cài đặt > Nhãn đối tượng

## Traceability

- REQ-005: Tạo mới/restore nhãn custom phải đồng bộ nhãn đó vào mọi zone với trạng thái mặc định là `cấm`; người dùng nhìn thấy kết quả sync và có thể retry sync nếu backend báo lỗi cache refresh recoverable.
- REQ-007: Luồng bao phủ import, reload, scrub frame video, lưu batch nhiều BBox, sửa/xóa sample đã lưu, lifecycle nhãn hệ thống/custom, uniqueness, batch validation và restore.
- CR-004: Trải nghiệm phải được persist và reload được; mock-only local state sẽ được thay trong TASK-024.

## Actors and Entry Points

- Actor: nhân viên vận hành an ninh hoặc admin cấu hình dataset labels.
- Entry point chính: tab `Cài đặt` -> subtab `Nhãn đối tượng`.
- Entry point phụ: sau khi thêm/restore nhãn custom, người dùng có thể chuyển sang `Vẽ zone` để kiểm tra rule mặc định `cấm`.
- Điểm nhập dữ liệu: import ảnh, import video, chọn dataset source đã có, chọn label, chọn sample đã lưu.

## Happy Path

1. Người dùng mở `Cài đặt > Nhãn đối tượng`.
2. UI tải labels, dataset sources và sample counts từ backend.
3. Người dùng import một ảnh hoặc video.
4. UI hiển thị progress import, sau đó chọn source mới khi đã sẵn sàng.
5. Nếu là video, người dùng kéo timeline scrubber tới frame mong muốn; UI tải frame đó.
6. Người dùng chọn một nhãn hệ thống hoặc nhãn custom active.
7. Người dùng vẽ một hoặc nhiều BBox sample trên canvas.
8. UI đánh dấu samples là pending và hiển thị pending count ở save bar.
9. Người dùng review samples đang chọn và có thể chỉnh geometry hoặc label.
10. Người dùng bấm lưu.
11. UI validate batch phía client, submit toàn bộ pending samples theo atomic batch, refresh samples/sample counts và hiển thị success.
12. Khi reload trang, cùng source, frame metadata và saved samples có thể tải lại từ backend.

## Alternative and Failure Paths

### Tạo nhãn custom

1. Người dùng mở dialog tạo label.
2. Người dùng nhập tên và category.
3. UI validate local rằng tên không rỗng.
4. API validate uniqueness không phân biệt hoa/thường.
5. Khi thành công, label xuất hiện trong danh sách custom active và chọn được để gắn samples.
6. UI hiển thị zone sync status: đã sync vào mọi zone với mặc định `cấm`.

### Đổi tên nhãn custom

1. Người dùng chọn rename cho nhãn custom active.
2. UI hiển thị tên hiện tại trong dialog.
3. Người dùng submit tên mới.
4. API validate uniqueness và cập nhật samples/zone rules theo label identity.
5. UI refresh label list, label của samples và sync status.

### Soft delete nhãn custom

1. Người dùng chọn delete cho một nhãn custom.
2. UI hỏi API hoặc dùng response API để biết nhãn có đang được dùng trong zone rules không.
3. Nếu đang được dùng, dialog hiển thị zone usage đang block và không có confirm destructive.
4. Nếu không còn được dùng, confirm dialog giải thích rằng samples được giữ lại để restore.
5. Sau khi confirm, label chuyển sang filter deleted và không còn chọn được cho samples mới.

### Restore nhãn custom

1. Người dùng bật filter nhãn đã xóa.
2. Người dùng chọn restore.
3. API restore label và sync label vào mọi zone với mặc định `cấm`.
4. UI hiển thị label active và sync status.

### Batch validation fail

- Nếu bất kỳ sample nào thiếu label/source/frame, geometry invalid hoặc vi phạm API validation, toàn bộ batch vẫn ở trạng thái pending.
- UI highlight samples lỗi trên canvas và liệt kê lỗi có thể hành động ở save bar.
- Người dùng sửa samples và retry save mà không mất các pending samples hợp lệ.

### Import fail

- File không hỗ trợ hoặc không đọc được metadata tạo ra failed import row.
- Người dùng có thể retry hoặc xóa row lỗi.
- Các persisted sources hiện có vẫn dùng được.

### Lỗi tải frame

- Canvas hiển thị lỗi theo frame và nút retry.
- Người dùng có thể chọn frame khác hoặc source khác.
- Pending samples ở các frame khác vẫn được giữ nguyên.

### Cảnh báo sync sau restore/create/rename label

- Nếu DB mutation thành công nhưng cache refresh/sync có warning, UI vẫn giữ thay đổi label đã hiển thị.
- Banner nói rõ zone rules là source of truth và cung cấp retry sync khi API hỗ trợ.
- Endpoint retry chính xác đang chờ TASK-021.

## Completion States

- Source import hoàn tất và được chọn.
- Frame video được chọn và render.
- Pending samples được lưu và reload từ backend.
- Saved sample được sửa/xóa và refresh từ backend.
- Nhãn hệ thống vẫn bị khóa nhưng chọn được.
- Nhãn custom được tạo/đổi tên/soft-delete/restore với trạng thái cuối rõ ràng.
- Zone sync feedback hiển thị sau create/restore/rename nhãn custom.
- TASK-022 không sửa production frontend files.

## Open Questions

- TASK-021 phải chốt API routes, envelope shapes và retry sync endpoint.
- Upload limits, codec hỗ trợ, hành vi cancel import và chiến lược media thumbnail chưa được chỉ định trong source artifacts.
- Nhãn phím tắt bàn phím và high-fidelity visual mockups chưa được chỉ định trong source artifacts.

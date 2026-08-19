---
artifact: BUG-DIAGNOSIS.md
version: 1.0.0
task_id: TASK-012
owner: diagnose-bug
status: in-review
updated_at: "2026-08-19T14:02:00+07:00"
---

# Bug Diagnosis: Khung Vẽ Zone Thiếu Video Feed, Trình Chọn Video Test & Liên Kết Dữ Liệu Zone

## Traceability
- **Task ID:** TASK-012
- **Linked Requirements:** REQ-005 (SVG Ray-Casting Polygon Zone), REQ-006 (Vehicle Tagging), REQ-007 (YOLO-World Custom Prompt Labeler)
- **Affected Components:** `frontend/src/components/zone/PolygonZoneEditor.tsx`, `frontend/src/pages/ZoneTagSettings.tsx`, `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/context/AppContext.tsx`
- **Owner:** diagnose-bug
- **Status:** in-review

---

## Reproduction
1. Mở ứng dụng web SentriAI Mini trong trình duyệt (`npm --prefix frontend run dev`).
2. Chuyển sang **Tab 3: Zone & Nhãn Xe (Zone & Tag Settings)**.
3. **Quan sát khi tạo/chỉnh sửa Zone:**
   - Khung canvas vẽ đa giác `PolygonZoneEditor` chỉ hiển thị nền đen tĩnh kèm text `[Camera Feed Preview: Click on screen to add polygon vertices]`.
   - Không có luồng video phát bên dưới khung vẽ, dẫn đến người dùng không nhìn thấy hình ảnh vị trí bãi kiểm/nhà xưởng để căn chỉnh đỉnh đa giác theo vật thể thực tế.
   - Thay đổi dropdown "Camera Áp Dụng" (`BAI_KIEM`, `XUONG_AN_NINH`, `GATE_01`) không thay đổi hình ảnh hay luồng video preview.
4. **Quan sát khi phát/test video:**
   - Cả Tab 2 và Tab 3 đang gán cứng URL video mẫu công cộng `https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4`.
   - Không có bộ tải video test từ local (`backend/data/videos/`) hoặc nút Upload video test tùy chọn để kiểm thử trực tiếp thuật toán Ray-Casting PIP trên luồng video thực tế.
5. **Quan sát khi lưu Zone & chuyển sang Tab 2 (Giám Sát Khu Vực):**
   - Bấm "Lưu Quy Tắc Zone" ở Tab 3 chỉ hiển thị thông báo thành công tạm thời (local state) nhưng không lưu vào `AppContext` hay gọi API backend.
   - Khi quay lại Tab 2 (Area Security Dashboard), các zone vừa tạo/chỉnh sửa không xuất hiện trên video giám sát.
6. **Quan sát Timeline Scrubber (REQ-007):**
   - Kéo thanh trượt timeline `videoTimestamp` không điều khiển `currentTime` của video element thực tế.

---

## Minimal Failing Case
- File: `frontend/src/components/zone/PolygonZoneEditor.tsx` (Lines 156–160):
```tsx
<div className="relative aspect-video bg-black border border-slate-800 rounded-lg overflow-hidden cursor-crosshair group shadow-inner">
  <div className="absolute inset-0 flex items-center justify-center text-slate-600 text-xs font-mono select-none">
    [Camera Feed Preview: Click on screen to add polygon vertices]
  </div>
  <svg ref={canvasRef} onClick={handleCanvasClick} className="absolute inset-0 w-full h-full">
    {/* SVG Polygon rendered without background video feed */}
  </svg>
</div>
```
Thành phần `<video>` hoàn toàn thiếu trong `PolygonZoneEditor`, làm cho người dùng vẽ polygon "mù" trên nền đen.

---

## Evidence
1. **Màn hình chụp thực tế (Screenshot):** Khung editor ở Tab 3 bị đen hoàn toàn phía sau các điểm $P_1, P_2$, không hiển thị khung hình camera thực tế.
2. **Kiểm tra mã nguồn `PolygonZoneEditor.tsx`:** Thiếu thẻ `<video>`, thiếu logic load video theo `selectedCamera`, thiếu nút chọn video test file/upload local file video.
3. **Kiểm tra mã nguồn `ZoneTagSettings.tsx` & `AreaSecurityDashboard.tsx`:**
   - Dùng gán cứng link demo ngoài thay vì hỗ trợ stream/video test từ `backend/data/videos/` hoặc local file upload.
   - Thẻ `<video>` trong timeline scrubber (REQ-007) thiếu `ref` gắn kết với `videoTimestamp` state (`videoRef.current.currentTime = videoTimestamp`).
4. **Kiểm tra `AppContext.tsx`:** Chưa lưu danh sách `zones` toàn cục để đồng bộ giữa Tab 3 (Cấu hình) và Tab 2 (Giám sát).

---

## Root Cause
1. **Thiếu Video Layer trong `PolygonZoneEditor.tsx`:** Khung vẽ polygon SVG chỉ chứa lớp canvas đè lên nền đen tĩnh, chưa được chèn lớp `<video>` phát bên dưới (z-index / absolute positioning).
2. **Thiếu Bộ Chọn Video Test / Stream Manager:** Chưa có cơ chế cho phép người dùng chọn video mẫu có sẵn trong hệ thống (như `BAI_KIEM.mp4`, `XUONG_AN_NINH.mp4`) hoặc tải lên file video `.mp4` bất kỳ để kiểm thử vùng cấm.
3. **Thiếu Đồng Bộ Dữ Liệu Zone (State Synchronization & API Integration):** Hàm `handleSave` tại `PolygonZoneEditor` chưa đưa dữ liệu polygon mới tạo vào state chung của ứng dụng (`AppContext`) hoặc gửi request tới backend `POST /api/v1/zones`.
4. **Timeline Scrubber chưa绑定 vớí DOM Video:** State `videoTimestamp` không thực hiện seek frame trên thẻ `<video>` HTML5 (`videoRef.current.currentTime`).

---

## Ownership
- **Capability:** `frontend-implementation`
- **Owning Specialist:** `implement-frontend`
- **Impacted Files:**
  - `frontend/src/components/zone/PolygonZoneEditor.tsx`
  - `frontend/src/pages/ZoneTagSettings.tsx`
  - `frontend/src/pages/AreaSecurityDashboard.tsx`
  - `frontend/src/context/AppContext.tsx` (hoặc `frontend/src/types/index.ts`)

---

## Regression Test
- **Test Feasibility:** Feasible via Vite/React unit test (Vitest / React Testing Library) hoặc E2E / Component Build Test.
- **Proposed Test Case:**
  1. Kiểm tra render `PolygonZoneEditor`: Đảm bảo tồn tại phần tử `<video>` background và tương tác thay đổi `selectedCamera` làm thay đổi `src` của video.
  2. Kiểm tra thao tác lưu Zone: Giả lập nhấp tọa độ canvas -> Bấm "Lưu Quy Tắc Zone" -> Xúc tiến lưu zone vào `AppContext` và xuất hiện ở danh sách zone được bật trong Tab 2.
  3. Kiểm tra tính năng chọn/tải Video Test: Chọn file video test -> Thẻ `<video>` cập nhật video phát thành công.

---

## Recommended Fix Scope
1. **Cập nhật `PolygonZoneEditor.tsx`:**
   - Thêm phần tử `<video>` phát video preview bên dưới SVG canvas (tự động phát, lặp lại, muted, mờ nhẹ z-0 để các điểm $P_1, P_2, \dots$ hiển thị rõ nét trên z-10).
   - Thêm bộ chọn video test (Local Sample Videos: Bãi Kiểm 10s, Xưởng An Ninh 4m32s, hoặc Nút "Tải Video Test MP4 Cục Bộ" từ đĩa).
   - Khi chuyển đổi dropdown "Camera Áp Dụng", tự động cập nhật nguồn video phát tương ứng.
2. **Đồng bộ Zone vào Global State / AppContext:**
   - Cập nhật `AppContext` hỗ trợ lưu danh sách `zones`.
   - Khi lưu zone ở Tab 3, đồng bộ zone đó sang Tab 2 (`AreaSecurityDashboard`) để vẽ đè polygon trực quan lên luồng camera giám sát real-time.
3. **Cập nhật Timeline Scrubber trong `ZoneTagSettings.tsx`:**
   - Gắn `useRef<HTMLVideoElement>` cho video custom prompt labeler. Khi thay đổi slider `videoTimestamp`, cập nhật `videoRef.current.currentTime = videoTimestamp`.

---

## Open Questions
- Không có câu hỏi mở. Phương án khắc phục đã rõ ràng và hoàn toàn thuộc phạm vi nâng cấp giao diện frontend.

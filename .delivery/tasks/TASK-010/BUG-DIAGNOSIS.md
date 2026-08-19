---
artifact: BUG-DIAGNOSIS.md
version: 1.0.0
task_id: TASK-010
owner: diagnose-bug
status: approved
updated_at: "2026-08-19T14:10:00+07:00"
---

# Bug Diagnosis: Luồng Video Giám Sát Bị Đen (Black Screen) Ở Tab 2 Area Security Dashboard

## Traceability
- **Task ID:** TASK-010
- **Linked Requirements:** REQ-002 (Bãi kiểm 10s Ring Buffer & Area Security), CR-002 (Real-time Stream & Zone Detection)
- **Affected Components:** `frontend/src/pages/AreaSecurityDashboard.tsx`, `frontend/src/context/AppContext.tsx`
- **Owner:** diagnose-bug
- **Status:** in-review

---

## Reproduction
1. Mở ứng dụng web SentriAI Mini trong trình duyệt (`npm --prefix frontend run dev`).
2. Chuyển sang **Tab 2: Giám Sát Khu Vực (Area Security Dashboard)**.
3. **Quan sát luồng video giám sát real-time:**
   - Khung hình xem trực tiếp camera bị đen hoàn toàn (black screen).
   - Chỉ xuất hiện các chữ cảnh báo SVG Zone đè lên (như `[Vùng Cấm Bãi Kiểm A]`, `[Vùng Chú Ý Xưởng An Ninh]`) và thẻ BBox (`Person (Conf: 96.5%) • Vi phạm Mức 3`) nhưng video bên dưới không phát được.
4. **Thay đổi luồng camera:**
   - Chuyển đổi dropdown luồng camera giữa `Camera 1: Bãi Kiểm (BAI_KIEM)` và `Camera 2: Xưởng An Ninh (XUONG_AN_NINH)`.
   - Cả hai lựa chọn đều trỏ về một URL video ngoài duy nhất (`https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4`) và đều bị đen màn hình.
5. **Kiểm thử video cục bộ:**
   - Không có công cụ cho phép người dùng chọn hoặc tải lên file video `.mp4` test từ ổ đĩa (vd: `BAI_KIEM.mp4` 10s hay `XUONG_AN_NINH.mp4` 4m32s) để chạy thử nghiệm ngay trên Tab 2.

---

## Minimal Failing Case
- File: `frontend/src/pages/AreaSecurityDashboard.tsx` (Lines 18–35 & 205–213):
```tsx
const streams: StreamOption[] = [
  {
    id: 'BAI_KIEM',
    name: 'Camera 1: Bãi Kiểm (BAI_KIEM - Clip 10s)',
    videoSrc: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    fps: 15.0,
    activeZonesCount: 2,
    resolution: '1080p',
  },
  {
    id: 'XUONG_AN_NINH',
    name: 'Camera 2: Xưởng An Ninh (XUONG_AN_NINH - Clip 4p32s)',
    videoSrc: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    fps: 15.0,
    activeZonesCount: 3,
    resolution: '1080p',
  },
];

{/* Video Element */}
<video
  key={activeVideoSrc}
  src={activeVideoSrc}
  autoPlay
  loop
  muted
  playsInline
  className="w-full h-full object-cover"
/>
```
Phần tử `<video>` phụ thuộc hoàn toàn vào nguồn video ngoài trực tuyến. Khi URL ngoài bị chặn cross-origin hoặc không phản hồi, màn hình video lập tức bị đen hoàn toàn và không có nút tải/thay thế video test local.

---

## Evidence
1. **Màn hình chụp thực tế (Screenshot từ người dùng):** Khung xem luồng camera real-time tại Tab 2 bị đen tuyền, mặc dù các khung SVG Zone overlay và BBox vi phạm vẫn vẽ đúng vị trí.
2. **Kiểm tra mã nguồn `AreaSecurityDashboard.tsx`:**
   - URL video gán cứng liên kết demo ngoài (`https://commondatastorage.googleapis.com/...`).
   - Cả 2 luồng camera `BAI_KIEM` và `XUONG_AN_NINH` dùng chung 1 URL mẫu.
   - Thiếu nút **"Tải Video Test MP4"** (file upload/picker) và thiếu cơ chế fallback phát mẫu khi URL bị chặn.

---

## Root Cause
1. **Phụ thuộc URL Video Demo Ngoài Không Ổn Định:** Nguồn video phát trực tuyến dùng URL Google Cloud demo ngoài bị lỗi/chặn tải trên một số trình duyệt hoặc môi trường mạng, làm thẻ `<video>` rơi vào trạng thái error/black frame.
2. **Thiếu Trình Quản Lý / Tải Video Test Cục Bộ tại Tab 2:** Tab 2 chưa có bộ tải video test `.mp4` (File Picker / Upload) cho phép người dùng nạp file video bãi kiểm hoặc nhà xưởng trực tiếp từ ổ đĩa để phát thực tế.
3. **Trùng Lặp Nguồn Video Giữa Các Camera:** Nguồn video của Camera Bãi Kiểm và Camera Xưởng An Ninh chưa được phân tách nguồn video độc lập.

---

## Ownership
- **Capability:** `frontend-implementation`
- **Owning Specialist:** `implement-frontend`
- **Impacted Files:**
  - `frontend/src/pages/AreaSecurityDashboard.tsx`
  - `frontend/src/context/AppContext.tsx`

---

## Regression Test
- **Test Feasibility:** Feasible via Vite/React component typecheck & build verification (`npm --prefix frontend run lint` & `npm --prefix frontend run build`).
- **Proposed Test Case:**
  1. Kiểm tra render luồng video: Thêm nút tải video test MP4 tại Tab 2.
  2. Tự động chuyển đổi nguồn video khi chọn camera `BAI_KIEM` hoặc `XUONG_AN_NINH`.
  3. Kiểm tra tính sẵn sàng của video: Cho phép nạp file video từ đĩa cục bộ, đảm bảo video luôn hiển thị mượt mà không bị đen màn hình.

---

## Recommended Fix Scope
1. **Cập nhật `AreaSecurityDashboard.tsx`:**
   - Phân tách nguồn video riêng biệt cho `BAI_KIEM` (`ForBiggerBlazes.mp4`) và `XUONG_AN_NINH` (`ForBiggerEscapes.mp4` / `ForBiggerFun.mp4`).
   - Thêm nút **"Tải Video Test MP4"** trên thanh tiêu đề Tab 2, cho phép chọn bất kỳ file video `.mp4` nào để thử nghiệm giám sát bãi kiểm ngay lập tức.
   - Cập nhật handler fallback khi video gặp sự cố tải.
2. **Đồng bộ State Video Test với `AppContext.tsx`:**
   - Cho phép dùng chung nguồn video test giữa Tab 2 và Tab 3.

---

## Open Questions
- Không có câu hỏi mở. Phương án khắc phục đã rõ ràng và hoàn toàn thuộc phạm vi nâng cấp giao diện frontend.

---
artifact: UI-UX-FOUNDATION.md
version: 1.0.0
owner: design-ui-ux
task_id: TASK-004
status: approved
updated_at: "2026-08-19T11:42:06+07:00"
linked_requirements:
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-005
  - CR-002
---

# UI/UX Foundation & React Design System Contract — SentriAI Mini

Tài liệu quy định hệ thống thiết kế giao diện (Design System Tokens), kiến trúc thông tin 4 Tab chính, quy chuẩn màu sắc trung tâm giám sát an ninh 24/7 (Monitoring Slate Dark Mode), và bộ Shared UI Components cho hệ thống Giám sát Camera AI (SentriAI Mini - CR-002 React & YOLOv26).

---

## Traceability

Ma trận vết các yêu cầu sản phẩm và thành phần giao diện React UI liên quan đến TASK-004:

| Requirement ID | Tiêu đề Yêu cầu | Trang/Component Giao diện Liên quan | Mô tả Thiết kế Chi tiết |
|---|---|---|---|
| **REQ-001** | LPR Gate Monitoring | `<GateDashboard>`, `Recharts KPI Cards`, `<VideoModal>` | Bố cục Màn 1 - Gate Dashboard render camera GATE-01, bảng tin nhận diện LPR realtime, 4 thẻ Recharts KPI visualizers và modal xem clip 10s. |
| **REQ-002** | Area Zone Monitoring | `<AreaSecurityDashboard>`, `<EventFeedCard>` | Bố cục Màn 2 - Area Security Dashboard render camera BAI-KIEM, phát hiện 8 loại đối tượng YOLOv26, Point-in-Polygon event feed. |
| **REQ-003** | Alert Severity Classification | `Severity Badges (Level 1, 2, 3)` | Bảng mã màu cảnh báo độ tương phản cao: Mức 1 (Emerald Green), Mức 2 (Amber Yellow), Mức 3 (Crimson Red Pulse). |
| **REQ-005** | Polygon Zone UI | `<ZoneTagSettings>`, `<PolygonZoneEditor>` | Màn 3 - Zone Editor dùng SVG Canvas kéo thả đỉnh đa giác polygon, nút bật/tắt quyền đối tượng (Lucide `Check`, `X`). |
| **CR-002** | React SPA Modernization | All React Components, `index.css` | Chuẩn hóa Tailwind CSS Design Tokens, Lucide Icons, Recharts, Web Audio API `<AudioBeepPlayer>` trên Vite + React SPA. |

---

## Information Architecture and Navigation

### 1. Overall Application Layout Structure
Giao diện ứng dụng SentriAI Mini bao gồm 3 khu vực chính:
```
+-----------------------------------------------------------------------------------+
| HEADER (Shared Top Bar): SentriAI Logo | System Status | Realtime Clock | User    |
+--------------+--------------------------------------------------------------------+
| SIDEBAR      | MAIN CONTENT AREA (Tab Router Container)                           |
| (Shared Left)|                                                                    |
| [1] Gate     | [Tab 1: GateDashboard]          [Tab 2: AreaSecurityDashboard]    |
| [2] Area     |  - Stream GATE-01                - Stream BAI-KIEM                |
| [3] Settings |  - 4 Recharts KPI Cards          - 4 Recharts KPI Cards            |
| [4] Chatbot  |  - LPR Realtime Feed            - Zone Violation Feed             |
|              |--------------------------------------------------------------------|
|              | [Tab 3: ZoneTagSettings]         [Tab 4: AIChatbotAssistant]       |
|              |  - SVG Polygon Canvas Editor     - Natural Language Q&A            |
|              |  - Vehicle Whitelist/Blacklist    - Prompt Chips                    |
|              |  - Custom Dataset Scrubber       - Evidence Video Clips 10s          |
+--------------+--------------------------------------------------------------------+
| SHARED MODALS & SOUND PLAYERS: <VideoModal 10s evidence> | <AudioBeepPlayer>     |
+-----------------------------------------------------------------------------------+
```

### 2. Tab Navigation Routing Structure
- **Tab 1: Gate Dashboard (`/gate`)**: Màn hình giám sát LPR Cổng vào (`GATE-01`).
- **Tab 2: Area Security (`/area`)**: Màn hình giám sát khu vực Bãi kiểm (`BAI-KIEM`).
- **Tab 3: Zone & Tag Settings (`/settings`)**: Quản lý SVG Polygon Zone Canvas, Gán nhãn xe & Dataset custom.
- **Tab 4: AI Chatbot Assistant (`/chatbot`)**: Trợ lý AI hỏi đáp sự kiện ngôn ngữ tự nhiên tiếng Việt.

---

## Design Tokens

Thiết kế bảng màu tối ưu cho **Màn hình Giám sát An ninh 24/7 (Monitoring Slate Dark Mode)** giúp người vận hành quan sát liên tục mà không gây mỏi mắt, đồng thời đảm bảo độ tương phản chuẩn WCAG AAA:

### 1. Monitoring Dark Color Palette
- **Background Slate Base**:
  - `bg-monitoring-base`: `#020617` (Slate 950 - Background chính nền tối sâu).
  - `bg-monitoring-card`: `#0F172A` (Slate 900 - Background cho Container, Cards, Sidebar, Header).
  - `bg-monitoring-hover`: `#1E293B` (Slate 800 - Nền Hover & Active State).
  - `border-monitoring`: `#334155` (Slate 700 - Viền viền sắc nét).

### 2. High-Contrast Severity Level Badges
Mã màu cảnh báo nổi bật chuyên dùng cho trung tâm giám sát:

| Level | Badge Code | Background Hex | Text / Border Hex | Yêu cầu Hiển thị & Visual Behavior |
|---|---|---|---|---|
| **Mức 1 (Green)** | `SEVERITY_LEVEL_1` | `#064E3B` (Emerald 900) | `#34D399` / `#10B981` | **Xe quen / Được phép**: Hiển thị badge màu Xanh Emerald hiền hòa, không gây xao nhãng. |
| **Mức 2 (Yellow)** | `SEVERITY_LEVEL_2` | `#78350F` (Amber 900) | `#FBBF24` / `#F59E0B` | **Xe lạ / Chú ý**: Hiển thị badge màu Vàng Amber nổi bật để bảo vệ rà soát. |
| **Mức 3 (Red)** | `SEVERITY_LEVEL_3` | `#7F1D1D` (Red 900) | `#F87171` / `#EF4444` | **Vi phạm zone cấm / Báo động**: Badge Đỏ Crimson kèm hiệu ứng nhấp nháy Pulse (`animate-pulse`) & kích hoạt tiếng bíp còi hiệu. |

### 3. Primary & Accent Colors
- **Primary Accent**: Electric Indigo (`#6366F1` - Tailwind Indigo 500) cho Buttons, Navigation Active State, và Primary Focus Rings.
- **Secondary Accent**: Sky Blue (`#0EA5E9` - Tailwind Sky 500) cho Video Stream Overlays, Recharts Charts Line/Bar Visualizers.
- **Typography Text Colors**:
  - Primary Text: `#F8FAFC` (Slate 50 - Chữ trắng sáng rõ nét).
  - Muted Text: `#94A3B8` (Slate 400 - Chữ phụ/Nhãn thông số).

---

## Component Primitives

Tất cả các React Components trong hệ thống được phân định rõ ràng giữa Server Containers và Client Components:

### 1. Shared Layout Primitives
- `<Header>` (`'use client'`): Thanh điều hướng trên cùng, hiển thị Logo, Trạng thái Hệ thống (Online/Degraded), Đồng hồ thời gian thực và Indicator âm thanh còi hiệu.
- `<Sidebar>` (`'use client'`): Thanh Menu dọc bên trái với 4 Tab Navigation icons (Lucide `LayoutDashboard`, `ShieldAlert`, `Sliders`, `MessageSquare`).

### 2. Shared Operational Primitives
- `<AudioBeepPlayer>` (`'use client'`): Shared Web Audio API Context Component. Tự động phát âm thanh còi bíp cảnh báo khi nhận WebSocket Event `ALERT_LEVEL_3_NOTIFICATION`.
- `<VideoModal>` (`'use client'`): Modal xem clip chứng cứ MP4 10s. Tích hợp trình phát video HTML5, nút tải xuống clip, và thông tin chi tiết sự kiện.
- `<KpiWidgetCard>` (`'use client'`): Thẻ hiển thị chỉ số KPI Recharts kết hợp biểu đồ mini Sparkline/Pie Chart.

---

## Forms and Validation

### 1. `<PolygonZoneEditor>` (SVG Canvas Form)
- **Controls**:
  - Toolbar chuyển đổi chế độ: Nút Chọn (`Select Mode`) và Nút Vẽ (`Draw Polygon Mode`).
  - Nút Xóa Zone (`Delete Zone`), Nút Đổi màu Zone (`Color Picker`).
  - Form cấu hình quy tắc: Danh sách checkboxes gán nhãn từng loại xe/đối tượng với biểu tượng Lucide `Check` (Được phép - Green) và `X` (Cấm - Red).
- **Validation Rules**:
  - Đa giác zone BẮT BUỘC có tối thiểu 3 đỉnh hợp lệ.
  - Các cạnh đa giác không được tự cắt nhau (Self-intersection validation).

### 2. `<VehicleTagTable>` (Vehicle Tagging Form)
- **Controls**: Bảng danh sách xe hỗ trợ 1-click gán nhãn (`Xe quen` / `Xe lạ` / `Blacklist`).
- **Validation**: Đổi nhãn cập nhật trạng thái UI tức thì với hiệu ứng Optimistic UI Update.

---

## Shared UI States

Mọi trang và component React BẮT BUỘC xử lý 5 trạng thái giao diện cốt lõi:

1. **Initial / Loading State**: Hiển thị Skeleton Loader hiệu ứng sóng (`animate-pulse`) với tông màu Slate 800 (`#1E293B`).
2. **Success State**: Hiển thị luồng video stream realtime, biểu đồ Recharts cập nhật mượt mà và danh sách sự kiện mới nhất.
3. **Empty State**: Khi không có sự kiện vi phạm hoặc dữ liệu rỗng, hiển thị Icon Lucide `Inbox` kèm thông điệp "Chưa ghi nhận sự kiện vi phạm nào".
4. **Error / Offline State**: Hiển thị Banner màu Đỏ Mức 3 kèm nút "Thử kết nối lại" (`Retry Connection`).
5. **Realtime Alert State**: Khi có sự kiện Mức 3, viền thẻ sự kiện nhấp nháy đỏ rực và còi bíp vang lên.

---

## Responsive Rules

Thiết kế tối ưu cho 3 độ phân giải màn hình giám sát tiêu chuẩn:

1. **Desktop Large (1920x1080 Full HD & 4K Monitoring Workstations)**:
   - Layout 2 cột chính: Video Stream chiếm 65% chiều rộng bên trái, Sidebar tin tức sự kiện realtime chiếm 35% bên phải.
   - Hàng 4 thẻ KPI Recharts dàn ngang đều nhau.
2. **Laptop Desktop (1366x768 & 1440x900)**:
   - Grid 2 cột co dãn linh hoạt, giảm Padding container.
3. **Mobile & Tablet (Touch Screens)**:
   - Sidebar rút gọn dạng Drawer Icon, các thẻ KPI tự động xuống hàng 2x2.

---

## Accessibility Baseline

- **WCAG AAA High Contrast**: Tỉ lệ tương phản màu chữ trên nền tối đạt tối thiểu `7:1`.
- **Keyboard Navigation (ARIA Baseline)**:
  - Phím `Tab` điều hướng lần lượt qua các nút trên Header, Sidebar Tabs, và các thẻ sự kiện.
  - Phím `ESC` để đóng Modal `<VideoModal>`.
  - Phím `Space` / `Enter` để kích hoạt các nút lệnh.

---

## Extension Rules

- **Custom Theme Variables**: Tất cả các màu sắc được lưu dưới dạng CSS Custom Variables (`--color-monitoring-base`, `--color-severity-level-3`) trong `index.css`, giúp dễ dàng chuyển đổi sang Light Mode nếu cần trong tương lai.

---

## Open Questions

Hiện tại không còn câu hỏi mở nào. Tất cả các quy chuẩn màu sắc giám sát, giao diện 4 tab và component primitives đã được định nghĩa hoàn chỉnh.

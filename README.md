# SentriAI Mini (VisionEdge-AI)

Hệ thống giám sát an ninh camera bằng AI cho khu vực cảng/kho vận. Phần mềm xử lý luồng video, phát hiện đối tượng, đọc biển số xe tại cổng, kiểm tra vi phạm theo vùng đa giác do người dùng tự vẽ, và trả lời câu hỏi về sự kiện bằng ngôn ngữ tự nhiên kèm clip chứng cứ.

---

## 1. Tổng quan

Hệ thống phục vụ hai kịch bản giám sát chính:

**Giám sát cổng (LPR Gate Monitoring)** — Camera tại cổng vào ghi nhận từng lượt xe, cắt vùng biển số và đọc bằng OCR. Biển số đọc được sẽ đối chiếu với danh sách xe quen / xe lạ để phân loại lượt ra vào, kèm bộ thẻ KPI thời gian thực.

**Giám sát khu vực (Area Zone Monitoring)** — Người dùng vẽ các vùng đa giác trực tiếp lên khung hình camera và khai báo loại đối tượng nào được phép, loại nào bị cấm trong từng vùng. Pipeline AI phát hiện đối tượng theo từng khung hình, kiểm tra điểm-trong-đa-giác và sinh sự kiện vi phạm khi có đối tượng bị cấm xuất hiện.

Ngoài hai kịch bản trên, hệ thống còn có công cụ gán nhãn dữ liệu và trợ lý hỏi đáp sự kiện.

### Tính năng theo tab giao diện

| Tab | Nội dung |
|---|---|
| **Giám sát cổng** | Luồng camera cổng, overlay bounding box bám khung hình, nhận diện biển số, bộ 4 thẻ KPI (Recharts) |
| **Giám sát khu vực** | Luồng MJPEG có overlay, phát hiện vi phạm vùng theo thời gian thực, bảng sự kiện, cảnh báo âm thanh |
| **Cài đặt** | Vẽ/sửa zone đa giác bằng SVG Canvas, quản lý biển số quen–lạ, công cụ gán nhãn bounding box cho ảnh và frame video |
| **Hỏi đáp AI** | Đặt câu hỏi tự nhiên về sự kiện đã ghi nhận, trả lời kèm clip chứng cứ 10 giây. Hỗ trợ hỏi tiếp nối ("còn nữa không", "lọc xe nâng thôi") và trả nhiều clip trong một câu trả lời |

Cảnh báo mức cao được đẩy qua WebSocket tới giao diện và gửi kèm clip qua Telegram Bot.

---

## 2. Công nghệ sử dụng

**Backend** — Python, FastAPI, Uvicorn, SQLite (SQLAlchemy), OpenCV, Ultralytics YOLO, EasyOCR, Google Gemini (tùy chọn).

**Frontend** — React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, SVG Canvas.

**Mô hình phát hiện** — Mặc định dùng `sentri-yolo11s.pt`, bản YOLOv11s finetune 50 epoch trên dataset cảng với 9 lớp riêng. Có thể đổi sang `yolov8s-worldv2.pt` (YOLO-World open-vocabulary) qua biến `DETECTION_MODEL_WEIGHTS`. Khi weights chính thiếu hoặc hỏng, pipeline tự lùi về `yolov8n.pt` (COCO) và ghi log cảnh báo — lúc đó độ chính xác giảm đáng kể vì mất các lớp chuyên biệt của cảng.

---

## 3. Cấu trúc thư mục

```
VisionEdge-AI/
├── backend/
│   ├── main.py                 # Điểm khởi động FastAPI, mount static, init DB
│   ├── app/
│   │   ├── api/v1/             # events, alerts, zones, vehicles, dataset, assistant, websocket
│   │   ├── ai/weights/         # File .pt — KHÔNG có trong git
│   │   ├── core/               # config.py (đọc .env), logger
│   │   ├── services/           # vision_pipeline, video_stream, frame_extractor, qa_agent, query_spec
│   │   └── models/
│   ├── database/               # engine, repository, migrations
│   ├── scripts/                # Công cụ đo đạc, render overlay
│   └── tests/                  # pytest
├── frontend/
│   ├── src/
│   │   ├── pages/              # GateDashboard, AreaSecurityDashboard, ZoneTagSettings, AIChatbotAssistant
│   │   ├── components/         # common, dashboard, layout, zone
│   │   ├── context/, hooks/, services/, types/
│   │   └── contracts/api/
│   └── vite.config.ts          # Proxy /api, /videos, /media về cổng 8000
├── data/                       # Chỉ có .gitkeep — nội dung KHÔNG có trong git
│   ├── video/                  # Video demo đặt ở đây
│   ├── images/, clips/, crops/
├── docs/contracts/db/schema.sql  # Schema SQLite, chạy tự động lúc khởi động
├── .delivery/                  # Tài liệu yêu cầu, kiến trúc, kế hoạch
├── .env.example
└── requirements.txt
```

---

## 4. Yêu cầu môi trường

- Python 3.11 trở lên
- Node.js 18 trở lên và npm
- Khoảng 3 GB dung lượng trống (PyTorch và các file weights chiếm phần lớn)

---

## 5. Cài đặt

### 5.1. Clone và tạo môi trường Python

```bash
git clone <repo-url>
cd VisionEdge-AI

python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# .venv\Scripts\activate         # Windows CMD/PowerShell
# source .venv/bin/activate      # macOS / Linux
```

### 5.2. Cài thư viện Python

```bash
pip install -r requirements.txt
pip install ultralytics sqlalchemy pydantic-settings httpx
```

> **Lưu ý quan trọng:** dòng thứ hai là bắt buộc. `requirements.txt` hiện thiếu bốn package này nhưng code có dùng, nên nếu chỉ chạy dòng đầu thì backend sẽ báo `ModuleNotFoundError` ngay khi khởi động. PyTorch được kéo về tự động như dependency của `ultralytics`, bước này mất vài phút.

### 5.3. Cài thư viện frontend

```bash
cd frontend
npm install
cd ..
```

### 5.4. Xin các file nhị phân (bắt buộc)

Video demo và file weights **không nằm trong git** vì dung lượng lớn (`.gitignore` chặn `*.mp4`, `*.pt`, `weights/`). Máy vừa clone sẽ không có chúng, và đây là nguyên nhân phổ biến nhất khiến màn hình camera bị đen.

Xin người trong nhóm gửi qua Drive hoặc USB, rồi đặt đúng vị trí sau:

| File | Đặt vào | Bắt buộc |
|---|---|---|
| `GATE-01.mp4` | `data/video/` | Có — thiếu thì tab Giám sát cổng đen |
| `BAI-KIEM.mp4` | `data/video/` | Có — thiếu thì tab Giám sát khu vực đen |
| `XUONG-AN-NINH.mp4` | `data/video/` | Tùy chọn |
| `sentri-yolo11s.pt` | `backend/app/ai/weights/` | Nên có — thiếu thì tự lùi về `yolov8n.pt`, mất các lớp riêng của cảng |

**Tên file phải khớp chính xác.** Trang Giám sát cổng tải video qua đường dẫn tĩnh `/videos/GATE-01.mp4`, nên `gate-01.mp4` hay `GATE_01.mp4` (gạch dưới) đều trả 404 và cho ra màn hình đen. Thư mục là `data/video` — số ít, không phải `videos`.

Không cần xin file `.db`: cơ sở dữ liệu SQLite được tạo tự động từ `docs/contracts/db/schema.sql` ở lần khởi động đầu tiên, kèm sẵn dữ liệu mẫu cho camera và zone.

### 5.5. Tạo file cấu hình

```bash
cp .env.example .env
```

Hệ thống chạy được ngay với giá trị mặc định. Chỉ điền thêm nếu cần các tính năng tùy chọn (xem mục 6).

---

## 6. Cấu hình `.env`

Các biến đáng chú ý:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./sentri_ai.db` | Chuỗi kết nối SQLite |
| `VIDEOS_DIR` | `./data/video` | Thư mục video, dùng chung cho cả `/videos` lẫn AI pipeline |
| `DETECTION_MODEL_WEIGHTS` | `sentri-yolo11s.pt` | Tên file trong `backend/app/ai/weights/` hoặc đường dẫn tuyệt đối |
| `DETECTION_CONFIDENCE_THRESHOLD` | `0.30` | Ngưỡng tin cậy YOLO. Đừng vượt `0.35`: đo trên footage thật, `0.35` làm Bãi Kiểm rụng từ 4 detection xuống còn 1 |
| `OCR_CONFIDENCE_THRESHOLD` | `0.50` | Ngưỡng OCR biển số. Camera cổng nhìn xe góc nghiêng nên hiếm khi vượt `0.70` dù đọc đúng |
| `EVENT_COOLDOWN_SECONDS` | `15` | Cửa sổ chống trùng sự kiện vùng |
| `LPR_COOLDOWN_SECONDS` | `12` | Cửa sổ chống trùng sự kiện biển số |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | rỗng | Bật gửi cảnh báo Telegram. Để trống thì bỏ qua, hệ thống vẫn chạy |
| `GEMINI_API_KEY` | rỗng | Bật nhánh LLM cho trợ lý hỏi đáp. Để trống thì dùng Rule Engine, không gọi mạng |
| `VIDEO_GATE_01_PATH` | rỗng | Trỏ video riêng cho một camera. Để trống thì tự tìm theo tên trong `VIDEOS_DIR` |

Không commit `.env` — file này đã nằm trong `.gitignore`, và tuyệt đối không đưa khóa Telegram hay Gemini thật lên git.

> `.env.example` có sẵn hai dòng `HOST` và `PORT` nhưng chúng **không có tác dụng**: `config.py` không khai báo hai biến này, còn `backend/main.py` gán cứng `0.0.0.0:8000`. Muốn đổi cổng thì chạy bằng lệnh `uvicorn` ở mục 7 và truyền `--port`.

---

## 7. Chạy dự án

Cần **hai terminal** chạy song song.

**Terminal 1 — Backend** (chạy từ thư mục gốc repo):

```bash
source .venv/Scripts/activate
python -m uvicorn backend.main:app --port 8000
```

Backend lắng nghe tại `http://localhost:8000`. Thêm `--reload` để tự nạp lại khi sửa code.

Cách chạy `python backend/main.py` cũng dùng được và cho kết quả tương đương, nhưng nó gán cứng cổng 8000 nên không đổi cổng được.

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Giao diện mở tại `http://localhost:3000`. Vite tự chuyển tiếp `/api`, `/videos`, `/media` sang cổng 8000, nên **phải bật backend trước** thì video và dữ liệu mới hiện.

### Kiểm tra nhanh sau khi khởi động

```bash
curl http://localhost:8000/health                  # {"status":"healthy",...}
curl -I http://localhost:8000/videos/GATE-01.mp4   # cần 200 hoặc 206
```

Đọc log khởi động của backend, dòng này cho biết video đã nạp đúng chưa:

```
[INFO] Mount /videos -> ...\data\video (3 file: BAI-KIEM.mp4, GATE-01.mp4, XUONG-AN-NINH.mp4)
```

Nếu thấy `[WARNING] ... thư mục KHÔNG có file video nào` thì quay lại bước 5.4.

Tài liệu API tương tác có sẵn tại `http://localhost:8000/docs`.

---

## 8. Chạy kiểm thử

```bash
python -m pytest backend/tests -q
```

Hai bài test sau nhạy cảm với thời gian và hỏng ngẫu nhiên khoảng 30–60% số lần chạy, kể cả trên code sạch — hỏng ở hai bài này không có nghĩa là môi trường sai:

- `test_camera_pipeline_decodes_and_infers_once_for_shared_snapshot`
- `test_inference_drops_backlog_instead_of_queueing`

---

## 9. Xử lý sự cố thường gặp

**Màn hình camera đen ở tab Giám sát cổng**

Mở thẳng `http://localhost:8000/videos/GATE-01.mp4` trên trình duyệt:

- Trả **404** — thiếu file, sai tên, hoặc sai thư mục. Kiểm tra `data/video/GATE-01.mp4` đúng gạch ngang và chữ hoa, rồi **khởi động lại backend**. Thư mục static chỉ được nạp một lần lúc khởi động, nên chép video vào khi backend đang chạy sẽ không có tác dụng.
- **Không kết nối được** — backend chưa chạy.
- **Phát được video** — lỗi nằm ở frontend, xem tab Console và Network của DevTools.

**`ModuleNotFoundError: No module named 'ultralytics'` (hoặc `sqlalchemy`, `pydantic_settings`)**

Chưa chạy dòng `pip install` thứ hai ở bước 5.2.

**Bounding box nhận sai loại đối tượng**

Thiếu `sentri-yolo11s.pt`. Kiểm tra log khởi động: nếu thấy `Lùi về weights dự phòng ... yolov8n.pt` thì hệ thống đang chạy bằng model COCO mặc định. Xin lại file weights ở bước 5.4.

**Cảnh báo Telegram không gửi**

Kiểm tra `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` trong `.env`. Để trống thì tính năng bị tắt và hệ thống vẫn chạy bình thường.

**Trợ lý AI trả lời cứng nhắc, không hiểu câu hỏi tự nhiên**

Chưa có `GEMINI_API_KEY` nên đang chạy Rule Engine. Lấy khóa tại https://aistudio.google.com/apikey rồi điền vào `.env`.

---

## 10. Tài liệu liên quan

- `.delivery/REQUIREMENTS.md` — Đặc tả yêu cầu và nhật ký thay đổi
- `.delivery/ARCHITECTURE.md` — Kiến trúc hệ thống, phân rã thành phần
- `.delivery/API-CONTRACT.md` — Hợp đồng API chi tiết
- `CLAUDE.md` — Quy ước làm việc và quản lý bug trong repo

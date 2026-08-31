import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# .env của gốc dự án được nạp trong app.core.config qua model_config.env_file.
# Không gọi load_dotenv() ở đây: nó ghi vào os.environ toàn cục nên các test dựng
# Settings(_env_file=None) sẽ đọc phải .env của máy đang chạy.

# logger phải import TRƯỚC router: import router kéo theo events.py, nơi
# AIVisionPipeline() được dựng ngay ở cấp module và ghi log nạp weights. Đặt sau thì
# handler chưa kịp gắn và dòng "Loaded YOLO model from: ..." biến mất khỏi console.
from backend.app.core.logger import logger
from backend.app.api.router import api_router, websocket_router
from backend.app.core.config import settings
from backend.app.services.frame_extractor import VIDEO_EXTENSIONS
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


def _resolve_videos_dir() -> str:
    """Thư mục phục vụ `/videos`, ưu tiên VIDEOS_DIR trong .env.

    Giữ nguyên các vị trí mặc định cũ làm fallback để repo sẵn có không phải đổi
    layout: thư mục nào đang thật sự chứa video thì dùng thư mục đó.
    """
    configured = os.getenv("VIDEOS_DIR") or getattr(settings, "VIDEOS_DIR", "")
    candidates = []
    if configured:
        candidates.append(
            configured if os.path.isabs(configured) else os.path.join(project_root, configured)
        )
    candidates.append(os.path.join(project_root, "data", "video"))
    candidates.append(os.path.join(project_root, "data", "videos"))
    candidates.append(os.path.join(backend_dir, "data", "videos"))

    for candidate in candidates:
        resolved = os.path.normpath(candidate)
        if os.path.isdir(resolved) and any(
            entry.lower().endswith(VIDEO_EXTENSIONS) for entry in os.listdir(resolved)
        ):
            return resolved
    # Không thư mục nào có video: trả ứng viên đầu tiên để mount vẫn tồn tại và
    # người dùng chỉ cần thả file vào đúng đường dẫn ghi trong log cảnh báo.
    return os.path.normpath(candidates[0])

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0"
)

# Enable CORS for React SPA frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files for videos and prototype image assets.
# Trang Cổng Vấn phát video bằng thẻ <video src="/videos/GATE-01.mp4"> nên nó ăn
# thẳng mount này, không đi qua resolve_video_path(). Dùng chung VIDEOS_DIR để hai
# đường (static và AI pipeline) không trỏ về hai thư mục khác nhau.
videos_dir = _resolve_videos_dir()
# Mount vô điều kiện: trước đây bọc trong `if os.path.exists(...)` nên máy vừa clone
# (git không track thư mục rỗng) khởi động backend là /videos biến mất im lặng, copy
# video vào sau cũng vô ích vì mount chỉ chạy một lần lúc import.
os.makedirs(videos_dir, exist_ok=True)
app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")

_available_videos = sorted(
    entry for entry in os.listdir(videos_dir) if entry.lower().endswith(VIDEO_EXTENSIONS)
)
if _available_videos:
    logger.info(f"Mount /videos -> {videos_dir} ({len(_available_videos)} file: {', '.join(_available_videos)})")
else:
    logger.warning(
        f"Mount /videos -> {videos_dir} nhưng thư mục KHÔNG có file video nào. "
        f"Trang Cổng Vấn sẽ đen vì /videos/GATE-01.mp4 trả 404. "
        f"Chép các file .mp4 demo vào đúng thư mục này (tên phân biệt gạch ngang/gạch dưới) rồi khởi động lại."
    )

assets_dir = os.path.join(project_root, "Prototype", "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Clip 10s bằng chứng và ảnh crop được sinh ra dưới dạng URL `/media/clips/...` và
# `/media/crops/...` (xem event_manager.slice_10s_ring_buffer_clip). Không mount thì
# mọi URL bằng chứng — Tab 4 lẫn Telegram CR-005 — đều trả 404.
# Tạo sẵn thư mục: chúng chỉ xuất hiện sau lần cắt clip đầu tiên, mà StaticFiles
# yêu cầu thư mục phải tồn tại ngay lúc mount.
os.makedirs(settings.CLIPS_DIR, exist_ok=True)
os.makedirs(settings.CROPS_DIR, exist_ok=True)
app.mount("/media/clips", StaticFiles(directory=settings.CLIPS_DIR), name="media-clips")
app.mount("/media/crops", StaticFiles(directory=settings.CROPS_DIR), name="media-crops")

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(websocket_router)

@app.on_event("startup")
def startup_event():
    from backend.database.engine import init_db
    schema_path = os.path.join(project_root, "docs", "contracts", "db", "schema.sql")
    init_db(schema_sql_path=schema_path)
    logger.info("SQLite Database initialized with schema.sql successfully!")

@app.get("/")

def root():
    return {
        "system": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "sentri-ai-backend"}

if __name__ == "__main__":
    import uvicorn
    reload_enabled = os.getenv("SENTRIAI_RELOAD", "").lower() in {"1", "true", "yes"}
    logger.info("Starting SentriAI Mini FastAPI Server on port 8000...")
    uvicorn.run(
        "main:app" if reload_enabled else app,
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
    )

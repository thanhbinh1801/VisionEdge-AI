import os
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "db" / "sentriai.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

# Locate project root
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
project_root = os.path.dirname(backend_dir)

# .env được nạp qua model_config.env_file bên dưới, không qua load_dotenv():
# load_dotenv() ghi thẳng vào os.environ nên Settings(_env_file=None) không còn cô lập
# được nữa, và test_database_config sẽ đọc phải .env của máy đang chạy.


def _path_from_sqlite_url(parsed_path: str) -> Path:
    raw_path = unquote(parsed_path)
    if len(raw_path) >= 4 and raw_path[0] == "/" and raw_path[2] == ":":
        raw_path = raw_path[1:]
    elif raw_path.startswith("/./") or raw_path.startswith("/../"):
        raw_path = raw_path[1:]
    return Path(raw_path)


def _sqlite_url_from_path(path_value: str) -> str:
    db_path = Path(path_value)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return f"sqlite:///{db_path.resolve().as_posix()}"


def _canonicalize_sqlite_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url

    parsed = urlparse(database_url)
    if parsed.netloc:
        db_path = Path(f"//{parsed.netloc}{unquote(parsed.path)}")
    else:
        db_path = _path_from_sqlite_url(parsed.path)

    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    return f"sqlite:///{db_path.resolve().as_posix()}"


def resolve_from_project_root(path: str) -> str:
    """
    Quy đổi đường dẫn tương đối theo gốc dự án thay vì theo thư mục làm việc.

    Dev server chạy bằng `cd backend && python main.py` nên CWD là backend/,
    còn pytest chạy từ gốc repo. Nếu để nguyên đường dẫn tương đối thì cùng một
    giá trị trong .env sẽ trỏ vào hai chỗ khác nhau — đó là lý do trước đây
    sinh ra hai file sentri_ai.db riêng biệt.
    """
    if not path:
        return path
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(project_root, path))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(PROJECT_ROOT / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "SentriAI Mini Backend"
    API_V1_STR: str = "/api/v1"
    PROJECT_ROOT: str = project_root

    DATABASE_URL: str = DEFAULT_DATABASE_URL
    SENTRIAI_DB_PATH: str | None = None

    CLIPS_DIR: str = "./data/clips"
    CROPS_DIR: str = "./data/crops"
    VIDEOS_DIR: str = "./data/video"
    IMAGES_DIR: str = "./data/images"

    # Ghi đè video cho từng camera; để trống thì dùng ánh xạ mặc định trong
    # backend/app/api/v1/events.py.
    VIDEO_BAI_KIEM_PATH: str = ""
    VIDEO_GATE_01_PATH: str = ""
    VIDEO_XUONG_AN_NINH_PATH: str = ""

    # Ngưỡng tin cậy tối thiểu để giữ lại một detection của YOLO.
    # Sau khi thay prompt trần bằng cụm mô tả (xem CANONICAL_CLASS_PROMPTS), điểm số
    # tăng rõ: xe đầu kéo ở cổng lên 0.89, container trong bãi 0.57-0.59. Nhờ vậy nâng
    # được ngưỡng từ 0.25 lên 0.30 để cắt lớp false positive quanh 0.26-0.29 (cột đèn
    # bị nhận thành người, bồn chứa thành xe tải) mà không mất detection thật.
    # Đừng đặt cao hơn ~0.35: đo trên footage thật, 0.35 làm bãi Bãi Kiểm rụng từ
    # 4 detection xuống còn 1.
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.30

    EVENT_COOLDOWN_SECONDS: int = 15
    VIDEO_PATH: str = ""
    DEMO_MODE: bool = False
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    @field_validator(
        "CLIPS_DIR", "CROPS_DIR", "VIDEOS_DIR", "IMAGES_DIR",
        "VIDEO_BAI_KIEM_PATH", "VIDEO_GATE_01_PATH", "VIDEO_XUONG_AN_NINH_PATH",
    )
    @classmethod
    def _absolutize(cls, value: str) -> str:
        return resolve_from_project_root(value)

    @field_validator("DATABASE_URL")
    @classmethod
    def _absolutize_sqlite_url(cls, value: str) -> str:
        """Neo file SQLite vào gốc dự án để CWD không quyết định dùng DB nào."""
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        raw_path = value[len(prefix):]
        if raw_path.startswith(":memory:") or not raw_path:
            return value
        return prefix + resolve_from_project_root(raw_path).replace("\\", "/")

    @field_validator("DETECTION_CONFIDENCE_THRESHOLD")
    @classmethod
    def _check_confidence(cls, value: float) -> float:
        if not 0.0 < value < 1.0:
            raise ValueError(
                f"DETECTION_CONFIDENCE_THRESHOLD phải nằm trong khoảng (0, 1), nhận được {value}"
            )
        return value

    @model_validator(mode="after")
    def normalize_paths(self) -> "Settings":
        if self.SENTRIAI_DB_PATH and self.DATABASE_URL == DEFAULT_DATABASE_URL:
            self.DATABASE_URL = _sqlite_url_from_path(self.SENTRIAI_DB_PATH)
        else:
            self.DATABASE_URL = _canonicalize_sqlite_url(self.DATABASE_URL)

        clips_path = Path(self.CLIPS_DIR)
        if not clips_path.is_absolute():
            resolved_clips = (PROJECT_ROOT / clips_path).resolve()
            if not resolved_clips.exists() and (PROJECT_ROOT / "backend" / clips_path).exists():
                resolved_clips = (PROJECT_ROOT / "backend" / clips_path).resolve()
            self.CLIPS_DIR = str(resolved_clips)

        crops_path = Path(self.CROPS_DIR)
        if not crops_path.is_absolute():
            resolved_crops = (PROJECT_ROOT / crops_path).resolve()
            if not resolved_crops.exists() and (PROJECT_ROOT / "backend" / crops_path).exists():
                resolved_crops = (PROJECT_ROOT / "backend" / crops_path).resolve()
            self.CROPS_DIR = str(resolved_crops)

        return self

    def video_path_override(self, camera_id: str) -> Optional[str]:
        """Trả về video ghi đè cho camera nếu .env có khai báo và file tồn tại."""
        attr = "VIDEO_" + camera_id.replace("-", "_").upper() + "_PATH"
        path = getattr(self, attr, "")
        if path and os.path.exists(path):
            return path
        return None


settings = Settings()

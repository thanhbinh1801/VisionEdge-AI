from pathlib import Path
from urllib.parse import unquote, urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "db" / "sentriai.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"


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
    DATABASE_URL: str = DEFAULT_DATABASE_URL
    SENTRIAI_DB_PATH: str | None = None
    CLIPS_DIR: str = "./data/clips"
    CROPS_DIR: str = "./data/crops"
    EVENT_COOLDOWN_SECONDS: int = 15
    VIDEO_PATH: str = ""
    DEMO_MODE: bool = False
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

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

settings = Settings()

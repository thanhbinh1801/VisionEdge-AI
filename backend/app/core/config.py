from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


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
    DATABASE_URL: str = "sqlite:///./sentri_ai.db"
    CLIPS_DIR: str = "./data/clips"
    CROPS_DIR: str = "./data/crops"
    EVENT_COOLDOWN_SECONDS: int = 15
    VIDEO_PATH: str = ""
    DEMO_MODE: bool = False

settings = Settings()

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SentriAI Mini Backend"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sentri_ai.db")
    CLIPS_DIR: str = os.getenv("CLIPS_DIR", "./data/clips")
    CROPS_DIR: str = os.getenv("CROPS_DIR", "./data/crops")
    EVENT_COOLDOWN_SECONDS: int = 15

    class Config:
        case_sensitive = True

settings = Settings()

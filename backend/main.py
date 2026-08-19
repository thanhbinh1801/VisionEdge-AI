import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logger import logger
from app.api.router import api_router

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

# Mount Static Files for videos and prototype image assets
videos_dir = os.path.join(backend_dir, "data", "videos")
if os.path.exists(videos_dir):
    app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")

assets_dir = os.path.join(project_root, "Prototype", "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

app.include_router(api_router, prefix=settings.API_V1_STR)

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
    logger.info("Starting SentriAI Mini FastAPI Server on port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

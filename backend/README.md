# SentriAI Mini - Python Backend Infrastructure

Thư mục chứa mã nguồn Python Backend FastAPI cho Hệ thống Giám sát Camera AI SentriAI Mini.

## Thư mục Mô-đun (Module Directory Structure)

- `main.py`: Entrypoint chạy FastAPI app server qua Uvicorn.
- `app/core/`: Cấu hình hệ thống (`config.py`), kết nối CSDL SQLite (`database.py`), logging (`logger.py`).
- `app/models/`: Định nghĩa ORM Database models (`domain/`) và Pydantic API Request/Response Schemas (`schemas/`).
- `app/api/`: Khai báo REST API Routers (`v1/`) và WebSocket Connection Handlers.
- `app/services/`: Mã nguồn logic xử lý nghiệp vụ các module:
  - `video_stream.py`: Ingestion Stream Loop (OpenCV VideoCapture)
  - `vision_pipeline.py`: YOLOv26 Object Detector & EasyOCR Engine
  - `event_manager.py`: Cooldown Window Deduplication & 10s Ring Buffer Clip Slicer
  - `alert_dispatcher.py`: WebSocket Real-time Alert & Telegram Bot Dispatcher
  - `qa_agent.py`: LLM Text-to-SQL Assistant Engine & Fallback Matcher

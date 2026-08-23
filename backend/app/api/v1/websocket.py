import asyncio
import json
import logging
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.vision_pipeline import AIVisionPipeline
from backend.app.api.v1.events import persist_area_metadata_violations
from backend.app.services.area_metadata import build_area_metadata_event
from backend.app.services.video_stream import get_camera_pipeline
from backend.app.services.zone_cache import zone_cache_service
from backend.database.engine import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()
vision_pipeline = AIVisionPipeline()
_SNAPSHOT_WAIT_SECONDS = 0.5

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def send_json(self, websocket: WebSocket, payload: dict) -> bool:
        try:
            await websocket.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            self.disconnect(websocket)
            logger.warning("WebSocket send failed; disconnecting stale client.", exc_info=True)
            return False
        return True

manager = ConnectionManager()


async def _watch_disconnect(websocket: WebSocket, disconnected: asyncio.Event) -> None:
    try:
        while not disconnected.is_set():
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnected.set()
    except RuntimeError:
        disconnected.set()

@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WS message: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/v1/events")
async def websocket_events_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    camera_id = websocket.query_params.get("camera_id", "BAI-KIEM")
    conf_threshold = float(websocket.query_params.get("conf_threshold", "0.35"))
    db = SessionLocal()
    disconnected = asyncio.Event()
    disconnect_task = asyncio.create_task(_watch_disconnect(websocket, disconnected))
    try:
        zone_state = zone_cache_service.get_or_load(db, camera_id)
        pipeline = get_camera_pipeline(camera_id, vision_pipeline)
        pipeline.update_zones(list(zone_state.zones), zone_state.zone_version)
        last_frame_id = None
        while not disconnected.is_set():
            snapshot = await asyncio.to_thread(
                pipeline.wait_for_snapshot,
                last_frame_id,
                timeout=_SNAPSHOT_WAIT_SECONDS,
            )
            if snapshot is None:
                continue
            last_frame_id = snapshot.frame_id
            zone_state = zone_cache_service.get_or_load(db, camera_id)
            payload = build_area_metadata_event(
                camera_id=camera_id,
                snapshot=snapshot,
                zone_state=zone_state,
                confidence_threshold=conf_threshold,
            )
            await asyncio.to_thread(
                persist_area_metadata_violations,
                db,
                camera_id=camera_id,
                metadata_event=payload,
            )
            if not await manager.send_json(websocket, payload):
                disconnected.set()
                break
    except WebSocketDisconnect:
        disconnected.set()
    finally:
        disconnected.set()
        disconnect_task.cancel()
        with suppress(asyncio.CancelledError):
            await disconnect_task
        manager.disconnect(websocket)
        db.close()

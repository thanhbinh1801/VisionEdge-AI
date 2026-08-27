from fastapi import APIRouter

from backend.app.api.v1 import alerts, assistant, dataset, events, vehicles, websocket, zones

api_router = APIRouter()
websocket_router = APIRouter()

api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(zones.router, prefix="/zones", tags=["zones"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(dataset.router, prefix="/dataset", tags=["dataset"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
websocket_router.include_router(websocket.router, tags=["websocket"])

from __future__ import annotations

import asyncio

from backend.app.api.v1.websocket import ConnectionManager


class FailingWebSocket:
    def __init__(self) -> None:
        self.query_params = {}
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, _message: str) -> None:
        raise RuntimeError("socket closed")


async def _send_json_disconnects_stale_client_on_send_failure():
    manager = ConnectionManager()
    websocket = FailingWebSocket()

    await manager.connect(websocket)

    sent = await manager.send_json(websocket, {"event_type": "AREA_FRAME_METADATA"})

    assert sent is False
    assert websocket.accepted is True
    assert websocket not in manager.active_connections


def test_send_json_disconnects_stale_client_on_send_failure():
    asyncio.run(_send_json_disconnects_stale_client_on_send_failure())

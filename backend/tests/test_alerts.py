import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.services.alert_dispatcher import AlertDispatcher, alert_dispatcher
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_alert_dispatcher_format_html_message():
    dispatcher = AlertDispatcher(telegram_token="123456:ABC", chat_id="-10012345")
    event_data = {
        "captured_at": "2026-08-24T22:30:15+07:00",
        "camera_id": "BAI-KIEM",
        "camera_name": "Camera Bãi kiểm",
        "zone_id": "zK1",
        "zone_name": "Khu vực cấm xe máy",
        "object_type": "motorbike",
        "object_type_name": "Xe máy",
        "violation_reason": "Xe máy đi vào Khu vực cấm xe máy",
    }
    msg = dispatcher.format_telegram_message(event_data)

    assert "CẢNH BÁO VI PHẠM AN NINH KHU VỰC" in msg
    assert "2026-08-24 22:30:15 (+07:00)" in msg
    assert "Camera Bãi kiểm (BAI-KIEM)" in msg
    assert "Khu vực cấm xe máy (zK1)" in msg
    assert "Xe máy (motorbike)" in msg
    assert "Xe máy đi vào Khu vực cấm xe máy" in msg


def test_alert_dispatcher_skipped_without_credentials():
    dispatcher = AlertDispatcher(telegram_token="", chat_id="")
    res = dispatcher.send_telegram_notification_sync({"severity_level": 3})
    assert res["status"] == "skipped"
    assert res["error"] == "BOT_TOKEN_INVALID"


def test_alert_dispatcher_send_video_success(tmp_path):
    clip_file = tmp_path / "test_clip.mp4"
    clip_file.write_bytes(b"dummy mp4 content")

    dispatcher = AlertDispatcher(telegram_token="123456:TEST", chat_id="-100123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 99}}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = dispatcher.send_telegram_notification_sync({
            "severity_level": 3,
            "video_clip_url": str(clip_file),
            "camera_id": "BAI-KIEM",
            "zone_id": "zK1",
            "object_type": "motorbike",
        })
        assert res["status"] == "sent"
        assert res["error"] is None
        assert res["dispatched_at"] is not None
        assert mock_post.called


def test_alert_dispatcher_send_video_rate_limited(tmp_path):
    clip_file = tmp_path / "test_clip.mp4"
    clip_file.write_bytes(b"dummy mp4 content")

    dispatcher = AlertDispatcher(telegram_token="123456:TEST", chat_id="-100123")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"ok": False, "description": "Too Many Requests: retry after 30"}

    with patch("httpx.Client.post", return_value=mock_resp):
        res = dispatcher.send_telegram_notification_sync({
            "severity_level": 3,
            "video_clip_url": str(clip_file),
            "camera_id": "BAI-KIEM",
        })
        assert res["status"] == "failed"
        assert res["error"] == "RATE_LIMITED"


def test_telegram_test_endpoint(client):
    mock_res = {
        "success": True,
        "message": "Gửi tin nhắn thử nghiệm Telegram thành công.",
        "bot_username": "SentriAIBot",
    }
    with patch("backend.app.api.v1.alerts.alert_dispatcher.test_telegram_connection", return_value=mock_res):
        response = client.post(
            "/api/v1/alerts/telegram/test",
            json={
                "bot_token": "123456:TEST_TOKEN",
                "chat_id": "-10012345",
                "custom_message": "Test connection",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_username"] == "SentriAIBot"


def test_get_event_evidence_not_found(client):
    response = client.get("/api/v1/events/non-existent-event-id/evidence")
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


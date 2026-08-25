import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Valid Telegram error codes according to TASK-026 API-CONTRACT.md
TELEGRAM_ERROR_CODES = {
    "BOT_TOKEN_INVALID",
    "CHAT_ID_NOT_FOUND",
    "TELEGRAM_API_TIMEOUT",
    "RATE_LIMITED",
    "VIDEO_CLIP_UNAVAILABLE",
    "PAYLOAD_TOO_LARGE",
    "NETWORK_ERROR",
}


class AlertDispatcher:
    """
    Multi-channel Alert Dispatcher (WebSocket & Telegram Bot API) for CR-005.
    Sends 10s MP4 evidence clip notifications to Telegram for Level 3 security violations.
    """

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.telegram_token = telegram_token if telegram_token is not None else settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id if chat_id is not None else settings.TELEGRAM_CHAT_ID
        self.timeout = timeout

    def format_telegram_message(self, event_data: Dict[str, Any]) -> str:
        """
        Formats HTML message string with 5 required fields:
        1. Thời gian vi phạm (captured_at)
        2. Camera (camera_name / camera_id)
        3. Khu vực (zone_name / zone_id)
        4. Đối tượng (object_type_name / object_type)
        5. Lý do vi phạm (violation_reason)
        """
        ict_tz = timezone(timedelta(hours=7))
        captured_at_raw = event_data.get("captured_at") or event_data.get("timestamp")
        dt_ict: Optional[datetime] = None

        if isinstance(captured_at_raw, datetime):
            if captured_at_raw.tzinfo is None:
                dt_ict = captured_at_raw.replace(tzinfo=timezone.utc).astimezone(ict_tz)
            else:
                dt_ict = captured_at_raw.astimezone(ict_tz)
        elif isinstance(captured_at_raw, str):
            try:
                clean_iso = captured_at_raw.replace("Z", "+00:00")
                parsed_dt = datetime.fromisoformat(clean_iso)
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                dt_ict = parsed_dt.astimezone(ict_tz)
            except Exception:
                dt_ict = datetime.now(ict_tz)
        else:
            dt_ict = datetime.now(ict_tz)

        captured_at_str = dt_ict.strftime("%Y-%m-%d %H:%M:%S (+07:00)")

        camera_id = event_data.get("camera_id", "UNKNOWN_CAM")
        camera_name = event_data.get("camera_name") or f"Camera {camera_id}"

        zone_id = event_data.get("zone_id") or "N/A"
        zone_name = event_data.get("zone_name") or "Khu vực cấm"

        object_type = event_data.get("object_type") or event_data.get("object_class", "unknown")
        object_type_name = event_data.get("object_type_name") or event_data.get("vietnamese_name") or object_type

        violation_reason = event_data.get("violation_reason")
        if not violation_reason:
            violation_reason = f"{object_type_name} đi vào {zone_name}"

        return (
            f"⚠️ <b>CẢNH BÁO VI PHẠM AN NINH KHU VỰC</b> ⚠️\n\n"
            f"⏰ <b>Thời gian:</b> {captured_at_str}\n"
            f"📹 <b>Camera:</b> {camera_name} ({camera_id})\n"
            f"📍 <b>Khu vực (Zone):</b> {zone_name} ({zone_id})\n"
            f"🚗 <b>Đối tượng:</b> {object_type_name} ({object_type})\n"
            f"❗ <b>Lý do vi phạm:</b> {violation_reason}\n\n"
            f"🎥 <i>Video clip chứng cứ 10s đính kèm ở tin nhắn.</i>"
        )

    def resolve_clip_filepath(self, video_clip_url: Optional[str]) -> Optional[Path]:
        if not video_clip_url:
            return None
        # Handle relative URL /media/clips/clip_xxx.mp4 or data/clips/clip_xxx.mp4
        clean_url = video_clip_url.lstrip("/")
        if clean_url.startswith("media/clips/"):
            filename = clean_url.replace("media/clips/", "")
            filepath = Path(settings.CLIPS_DIR) / filename
        elif clean_url.startswith("data/clips/"):
            filename = clean_url.replace("data/clips/", "")
            filepath = Path(settings.CLIPS_DIR) / filename
        else:
            filepath = Path(clean_url)

        if filepath.exists() and filepath.is_file():
            return filepath

        # Fallback check under PROJECT_ROOT / backend / data / clips / filename
        from backend.app.core.config import PROJECT_ROOT
        alt_path1 = PROJECT_ROOT / "backend" / "data" / "clips" / filepath.name
        if alt_path1.exists() and alt_path1.is_file():
            return alt_path1

        alt_path2 = PROJECT_ROOT / "data" / "clips" / filepath.name
        if alt_path2.exists() and alt_path2.is_file():
            return alt_path2

        return None

    def send_telegram_notification_sync(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous dispatch method for background pipeline threads.
        Returns dispatch status dict: {"status": "sent"|"failed"|"skipped", "error": err_code, "dispatched_at": iso_str}
        """
        token = self.telegram_token
        chat_id = self.chat_id

        if not token:
            logger.warning("Telegram dispatch skipped: TELEGRAM_BOT_TOKEN not configured.")
            return {"status": "skipped", "error": "BOT_TOKEN_INVALID", "dispatched_at": None}

        if not chat_id:
            logger.warning("Telegram dispatch skipped: TELEGRAM_CHAT_ID not configured.")
            return {"status": "skipped", "error": "CHAT_ID_NOT_FOUND", "dispatched_at": None}

        caption_html = self.format_telegram_message(event_data)
        clip_path = self.resolve_clip_filepath(event_data.get("video_clip_url"))

        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if clip_path and clip_path.exists():
                    file_size = clip_path.stat().st_size
                    if file_size > 50 * 1024 * 1024:  # 50MB limit
                        logger.error(f"Telegram video clip size exceeds limit: {file_size} bytes")
                        return {"status": "failed", "error": "PAYLOAD_TOO_LARGE", "dispatched_at": None}

                    url = f"https://api.telegram.org/bot{token}/sendVideo"
                    with open(clip_path, "rb") as video_file:
                        files = {"video": (clip_path.name, video_file, "video/mp4")}
                        data = {
                            "chat_id": chat_id,
                            "caption": caption_html,
                            "parse_mode": "HTML",
                        }
                        response = client.post(url, data=data, files=files)
                else:
                    # Fallback to sendMessage if clip is unavailable
                    logger.warning(f"Clip file unavailable for Telegram send, falling back to sendMessage: {event_data.get('video_clip_url')}")
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    data = {
                        "chat_id": chat_id,
                        "text": caption_html + "\n\n⚠️ <i>(Lưu ý: Không tìm thấy tệp video clip chứng cứ 10s).</i>",
                        "parse_mode": "HTML",
                    }
                    response = client.post(url, data=data)

                if response.status_code == 200 and response.json().get("ok"):
                    logger.info("Successfully dispatched Telegram notification.")
                    return {"status": "sent", "error": None, "dispatched_at": now_iso}

                # Handle HTTP error responses from Telegram API
                status_code = response.status_code
                resp_json = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                err_desc = resp_json.get("description", response.text)

                logger.error(f"Telegram API returned error HTTP {status_code}: {err_desc}")

                if status_code in (401, 404):
                    err_code = "BOT_TOKEN_INVALID" if "token" in err_desc.lower() else "CHAT_ID_NOT_FOUND"
                elif status_code == 429:
                    err_code = "RATE_LIMITED"
                elif status_code == 400 and "chat not found" in err_desc.lower():
                    err_code = "CHAT_ID_NOT_FOUND"
                else:
                    err_code = "NETWORK_ERROR"

                return {"status": "failed", "error": err_code, "dispatched_at": None}

        except httpx.TimeoutException:
            logger.error("Telegram API connection timed out.")
            return {"status": "failed", "error": "TELEGRAM_API_TIMEOUT", "dispatched_at": None}
        except httpx.RequestError as exc:
            logger.error(f"Telegram API network error: {exc}")
            return {"status": "failed", "error": "NETWORK_ERROR", "dispatched_at": None}
        except Exception as exc:
            logger.exception(f"Unexpected exception during Telegram dispatch: {exc}")
            return {"status": "failed", "error": "NETWORK_ERROR", "dispatched_at": None}

    async def dispatch_alert(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async dispatch entrypoint for level 3 security alerts.
        """
        severity = event_data.get("severity_level", event_data.get("severity", 1))
        logger.info(f"Dispatching event alert (Severity level {severity})")

        if severity == 3:
            return self.send_telegram_notification_sync(event_data)

        return {"status": "skipped", "error": None, "dispatched_at": None}

    def test_telegram_connection(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        custom_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tests Telegram bot API connection & chat_id validity.
        """
        token = bot_token or self.telegram_token
        target_chat = chat_id or self.chat_id

        if not token:
            return {"success": False, "message": "Bot token chưa được cấu hình.", "bot_username": ""}
        if not target_chat:
            return {"success": False, "message": "Chat ID chưa được cấu hình.", "bot_username": ""}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # 1. Test getMe
                get_me_resp = client.get(f"https://api.telegram.org/bot{token}/getMe")
                if get_me_resp.status_code != 200 or not get_me_resp.json().get("ok"):
                    return {"success": False, "message": "Bot token không hợp lệ.", "bot_username": ""}

                bot_username = get_me_resp.json().get("result", {}).get("username", "")

                # 2. Test sendMessage
                msg = custom_message or "Kiểm tra kết nối Telegram Bot từ SentriAI Mini"
                send_resp = client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": target_chat, "text": f"✅ {msg}"},
                )
                if send_resp.status_code == 200 and send_resp.json().get("ok"):
                    return {
                        "success": True,
                        "message": "Gửi tin nhắn thử nghiệm Telegram thành công.",
                        "bot_username": bot_username,
                    }
                else:
                    err_desc = send_resp.json().get("description", send_resp.text)
                    return {
                        "success": False,
                        "message": f"Không thể gửi tin nhắn tới Chat ID: {err_desc}",
                        "bot_username": bot_username,
                    }
        except Exception as exc:
            return {"success": False, "message": f"Lỗi kết nối Telegram API: {exc}", "bot_username": ""}


# Global instance
alert_dispatcher = AlertDispatcher()

import logging

logger = logging.getLogger(__name__)

class AlertDispatcher:
    """
    Multi-channel Alert Dispatcher (WebSocket & Telegram Bot API).
    """
    def __init__(self, telegram_token: str = None, chat_id: str = None):
        self.telegram_token = telegram_token
        self.chat_id = chat_id

    async def dispatch_alert(self, event_data: dict):
        severity = event_data.get("severity", 1)
        logger.info(f"Dispatching event alert (Severity level {severity})")

        if severity == 3 and self.telegram_token and self.chat_id:
            await self._send_telegram_notification(event_data)

    async def _send_telegram_notification(self, event_data: dict):
        logger.info(f"Sending Telegram notification for Level 3 alert: {event_data.get('event_type')}")

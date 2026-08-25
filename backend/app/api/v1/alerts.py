from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.services.alert_dispatcher import alert_dispatcher

router = APIRouter()


class TelegramTestRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    custom_message: Optional[str] = None


class TelegramTestResponseData(BaseModel):
    success: bool
    message: str
    bot_username: str


class TelegramTestEnvelope(BaseModel):
    success: bool
    data: Optional[TelegramTestResponseData] = None
    error: Optional[dict] = None


@router.post("/telegram/test", response_model=TelegramTestEnvelope)
def test_telegram_alert(payload: TelegramTestRequest):
    """
    Test Telegram Bot connection & chat_id configuration.
    """
    res = alert_dispatcher.test_telegram_connection(
        bot_token=payload.bot_token,
        chat_id=payload.chat_id,
        custom_message=payload.custom_message,
    )
    return {
        "success": res["success"],
        "data": {
            "success": res["success"],
            "message": res["message"],
            "bot_username": res["bot_username"],
        },
        "error": None if res["success"] else {"code": "TELEGRAM_TEST_FAILED", "message": res["message"]},
    }

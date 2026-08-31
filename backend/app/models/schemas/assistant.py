from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    """Một lượt trong hội thoại, gửi kèm để trợ lý hiểu được câu hỏi rút gọn."""

    role: Literal["user", "ai"]
    text: str


class QueryRequest(BaseModel):
    query: str
    #: Vài lượt gần nhất; backend chỉ đọc 4 lượt cuối.
    history: list[ChatTurn] = Field(default_factory=list)
    #: `spec` của lượt trả lời trước, để câu hỏi tiếp nối sửa đổi thay vì dựng lại.
    previous_spec: Optional[dict[str, Any]] = None


class ClipRef(BaseModel):
    """Một clip bằng chứng, luôn thuộc về sự kiện nằm trong kết quả truy vấn."""

    event_id: Optional[str] = None
    url: str
    timestamp: Optional[str] = None
    camera: Optional[str] = None
    label: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sql_query: Optional[str] = None
    clips: list[ClipRef] = Field(default_factory=list)
    #: Clip đầu tiên trong `clips`. Giữ cho client cũ; client mới nên đọc `clips`.
    clip_url: Optional[str] = None
    #: `QuerySpec` đã dùng, để client gửi lại ở lượt sau.
    spec: Optional[dict[str, Any]] = None

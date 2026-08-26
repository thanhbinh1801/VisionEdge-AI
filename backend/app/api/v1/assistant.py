from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.qa_agent import LLMQAAgent
from backend.database.engine import get_db

router = APIRouter()
agent = LLMQAAgent()


# Khai báo inline theo quy ước của các router khác (xem events.py::EventResponse).
# `app/models/schemas/assistant.py` là bản trùng lặp cũ và không còn được dùng.
class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    sql_query: Optional[str] = None
    # Mã sự kiện dùng làm chứng cứ; frontend lấy clip 10s theo mã này.
    event_id: Optional[str] = None
    clip_url: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
def ask_assistant(req: QueryRequest, db: Session = Depends(get_db)):  # noqa: B008
    res = agent.answer_question(req.query, db=db)
    return QueryResponse(**res)

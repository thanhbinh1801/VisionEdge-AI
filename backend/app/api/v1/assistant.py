from fastapi import APIRouter
from app.models.schemas.assistant import QueryRequest, QueryResponse
from app.services.qa_agent import LLMQAAgent

router = APIRouter()
agent = LLMQAAgent()

@router.post("/query", response_model=QueryResponse)
def ask_assistant(req: QueryRequest):
    res = agent.answer_question(req.query)
    return QueryResponse(**res)

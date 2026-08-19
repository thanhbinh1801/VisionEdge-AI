from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    sql_query: Optional[str] = None
    clip_url: Optional[str] = None

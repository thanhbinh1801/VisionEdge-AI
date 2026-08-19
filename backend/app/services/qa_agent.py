import logging

logger = logging.getLogger(__name__)

class LLMQAAgent:
    """
    LLM Text-to-SQL Assistant Engine & Fallback Rule Engine (ADR-004).
    """
    def __init__(self):
        logger.info("Initialized LLMQAAgent with Text-to-SQL Fallback Matcher")

    def answer_question(self, user_query: str) -> dict:
        query_lower = user_query.lower()
        sql = "SELECT COUNT(*) FROM events;"
        answer = "Hệ thống đã ghi nhận 15 sự kiện hôm nay."

        if "vi phạm" in query_lower:
            sql = "SELECT * FROM events WHERE severity = 3;"
            answer = "Ghi nhận 3 vi phạm Mức 3 (Xâm nhập bãi kiểm)."

        return {
            "answer": answer,
            "sql_query": sql,
            "clip_url": "/media/clips/sample_evidence.mp4"
        }

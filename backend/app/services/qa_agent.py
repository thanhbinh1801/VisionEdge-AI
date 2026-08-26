"""
LLM Text-to-SQL Assistant Engine & Fallback Rule Engine (ADR-004).

ADR-004 quy định hai tầng: một tầng dịch câu hỏi bằng LLM và một tầng fallback
rule-based. Hiện dự án chưa có LLM client nào trong `requirements.txt`, và
`requirements.txt` là shared file nằm ngoài write scope của TASK-011, nên bản này
triển khai đầy đủ tầng rule-based cộng với `TextToSQLTranslator` làm chỗ cắm cho
tầng LLM về sau. Xem `Scope change request` trong TASK-RESULT.md.

Nguyên tắc an toàn: câu hỏi của người dùng không bao giờ được nối thẳng vào SQL.
Mọi truy vấn dựng từ mẫu cố định trong file này, giá trị đi qua bind parameter, và
`assert_read_only` chặn mọi thứ không phải một câu SELECT đơn trên bảng `events`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional, Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Cột được phép đọc. Bảng `events` là bề mặt dữ liệu duy nhất của trợ lý.
EVENT_COLUMNS = (
    "id, timestamp, camera_id, zone_id, event_type, severity_level, "
    "license_plate, object_class, confidence, video_clip_url"
)

# Nhãn hiển thị tiếng Việt được lưu thẳng vào events.object_class (xem
# events.py::_persist_violation_event), nên khớp theo nhãn chứ không theo tên lớp
# canonical. Khoá là từ người dùng hay gõ, giá trị là chuỗi LIKE trên object_class.
OBJECT_KEYWORDS: dict[str, str] = {
    "container": "Container",
    "xe container": "Container",
    "xe tải": "Xe tải",
    "xe nâng": "Xe nâng",
    "forklift": "Xe nâng",
    "xe cẩu": "Xe cẩu",
    "cẩu": "Xe cẩu",
    "xe con": "Xe con",
    "ô tô": "Xe con",
    "xe hơi": "Xe con",
    "xe máy": "Xe máy",
    "mô tô": "Xe máy",
    "xe đạp": "Xe đạp",
    "người": "Người",
    "công nhân": "Người",
}

CAMERA_KEYWORDS: dict[str, str] = {
    "cổng": "GATE-01",
    "gate": "GATE-01",
    "bãi kiểm": "BAI-KIEM",
    "bãi": "BAI-KIEM",
    "xưởng": "XUONG-AN-NINH",
    "an ninh": "XUONG-AN-NINH",
}

COUNT_KEYWORDS = ("bao nhiêu", "mấy", "số lượng", "tổng số", "đếm")
VIOLATION_KEYWORDS = ("vi phạm", "xâm nhập", "cấm", "cảnh báo", "nghiêm trọng")

PLATE_RE = re.compile(r"\b\d{2}[A-Za-z]{1,2}[- ]?\d{3}\.?\d{2}\b")

_WRITE_TOKENS = (
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "attach", "detach", "pragma", "vacuum", "truncate", "grant", "begin", "commit",
)


class ReadOnlyViolation(RuntimeError):
    """Câu SQL dựng ra không phải truy vấn chỉ đọc trên `events`."""


@dataclass
class SQLPlan:
    """Một truy vấn đã dịch, kèm tham số và mô tả để sinh câu trả lời."""

    sql: str
    params: dict[str, Any] = field(default_factory=dict)
    intent: str = "list"  # "count" | "list"
    filters_desc: list[str] = field(default_factory=list)


class TextToSQLTranslator(Protocol):
    """Chỗ cắm cho tầng LLM của ADR-004. Trả về None nếu không dịch được."""

    def translate(self, question: str) -> Optional[SQLPlan]:  # pragma: no cover - protocol
        ...


def assert_read_only(sql: str) -> None:
    """
    Chặn mọi câu không phải một SELECT đơn trên `events`.

    Đây là lưới an toàn cuối, không phải lớp bảo vệ duy nhất: giá trị người dùng
    luôn đi qua bind parameter nên không tới được đây dưới dạng SQL. Giữ hàm này
    để một translator LLM cắm vào sau cũng không thể vượt qua ranh giới chỉ đọc.
    """
    normalized = " ".join(sql.lower().split())
    if not normalized.startswith("select "):
        raise ReadOnlyViolation(f"Chỉ chấp nhận câu SELECT, nhận được: {sql[:60]!r}")
    if ";" in normalized.rstrip(";"):
        raise ReadOnlyViolation("Không chấp nhận nhiều câu lệnh trong một truy vấn")
    for token in _WRITE_TOKENS:
        if re.search(rf"\b{token}\b", normalized):
            raise ReadOnlyViolation(f"Từ khoá ghi dữ liệu bị chặn: {token}")
    if " from events" not in normalized:
        raise ReadOnlyViolation("Trợ lý chỉ được truy vấn bảng `events`")


class RuleBasedTranslator:
    """
    Dịch câu hỏi tiếng Việt sang SQLPlan bằng luật.

    Cố tình không đoán bừa: câu hỏi không khớp bộ lọc nào và cũng không phải câu
    đếm thì trả None để tầng trên rơi về câu trả lời fallback, thay vì trả về một
    truy vấn "toàn bộ sự kiện" trông như đã hiểu đúng câu hỏi.
    """

    def translate(self, question: str) -> Optional[SQLPlan]:
        q = question.lower().strip()
        if not q:
            return None

        where: list[str] = []
        params: dict[str, Any] = {}
        desc: list[str] = []
        # Mốc thời gian một mình không đủ để coi là đã hiểu câu hỏi: "thời tiết hôm
        # nay thế nào" cũng chứa "hôm nay". Phải có thêm chủ thể (loại đối tượng,
        # camera, mức vi phạm, biển số) hoặc ý định đếm thì mới dịch.
        has_subject = False

        since = self._time_filter(q)
        if since is not None:
            where.append("timestamp >= :since")
            params["since"] = since[0]
            desc.append(since[1])

        for keyword, label in OBJECT_KEYWORDS.items():
            if keyword in q:
                where.append("object_class LIKE :object_class")
                params["object_class"] = f"%{label}%"
                desc.append(label.lower())
                has_subject = True
                break

        for keyword, camera_id in CAMERA_KEYWORDS.items():
            if keyword in q:
                where.append("camera_id = :camera_id")
                params["camera_id"] = camera_id
                desc.append(f"camera {camera_id}")
                has_subject = True
                break

        if any(keyword in q for keyword in VIOLATION_KEYWORDS):
            where.append("severity_level = :severity_level")
            params["severity_level"] = 3
            desc.append("vi phạm mức 3")
            has_subject = True

        plate_match = PLATE_RE.search(question)
        if plate_match:
            where.append("license_plate = :license_plate")
            params["license_plate"] = plate_match.group(0)
            desc.append(f"biển số {plate_match.group(0)}")
            has_subject = True

        wants_count = any(keyword in q for keyword in COUNT_KEYWORDS)
        if not has_subject and not wants_count:
            return None

        clause = f" WHERE {' AND '.join(where)}" if where else ""
        if wants_count:
            sql = f"SELECT COUNT(*) AS total FROM events{clause}"
            return SQLPlan(sql=sql, params=params, intent="count", filters_desc=desc)

        sql = (
            f"SELECT {EVENT_COLUMNS} FROM events{clause} "
            "ORDER BY timestamp DESC LIMIT :limit"
        )
        params["limit"] = 5
        return SQLPlan(sql=sql, params=params, intent="list", filters_desc=desc)

    @staticmethod
    def _time_filter(q: str) -> Optional[tuple[datetime, str]]:
        now = datetime.utcnow()
        if "hôm nay" in q or "hôm nây" in q:
            return now.replace(hour=0, minute=0, second=0, microsecond=0), "hôm nay"
        if "hôm qua" in q:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start - timedelta(days=1), "hôm qua"
        if "tuần này" in q or "tuần nay" in q:
            return now - timedelta(days=7), "7 ngày qua"
        if "giờ qua" in q or "vừa rồi" in q:
            return now - timedelta(hours=1), "1 giờ qua"
        return None


class LLMQAAgent:
    """LLM Text-to-SQL Assistant Engine & Fallback Rule Engine (ADR-004)."""

    FALLBACK_ANSWER = (
        "Tôi chưa hiểu câu hỏi này. Bạn thử hỏi theo sự kiện, ví dụ: "
        "\"Hôm nay có bao nhiêu vi phạm ở bãi kiểm?\" hoặc "
        "\"Có xe máy nào vào khu vực cấm không?\"."
    )
    NO_DB_ANSWER = "Chưa kết nối được cơ sở dữ liệu sự kiện nên tôi chưa trả lời được."

    def __init__(self, translator: Optional[TextToSQLTranslator] = None):
        self.translator = translator or RuleBasedTranslator()
        logger.info("Initialized LLMQAAgent with %s", type(self.translator).__name__)

    def answer_question(self, user_query: str, db: Optional[Session] = None) -> dict:
        """
        Trả về {answer, sql_query, event_id, clip_url}.

        `event_id` là mã sự kiện dùng làm chứng cứ; tầng API/UI lấy clip 10s theo mã
        này. Không có sự kiện khớp thì `event_id` và `clip_url` là None — không bịa
        ra một clip để câu trả lời trông đầy đủ hơn.
        """
        plan = self.translator.translate(user_query)
        if plan is None:
            return self._fallback(self.FALLBACK_ANSWER)
        if db is None:
            return self._fallback(self.NO_DB_ANSWER, sql_query=plan.sql)

        try:
            assert_read_only(plan.sql)
            rows = db.execute(text(plan.sql), plan.params).mappings().all()
        except ReadOnlyViolation:
            logger.exception("Truy vấn bị chặn vì không phải chỉ đọc")
            return self._fallback(self.FALLBACK_ANSWER)
        except Exception:
            logger.exception("Lỗi thực thi truy vấn trợ lý")
            return self._fallback(self.NO_DB_ANSWER, sql_query=plan.sql)

        if plan.intent == "count":
            return self._answer_count(plan, rows, db)
        return self._answer_list(plan, rows)

    def _answer_count(self, plan: SQLPlan, rows, db: Session) -> dict:
        total = int(rows[0]["total"]) if rows else 0
        scope = " ".join(plan.filters_desc) if plan.filters_desc else "toàn bộ"
        answer = f"Ghi nhận {total} sự kiện {scope}." if total else f"Không có sự kiện nào {scope}."

        evidence = None
        if total:
            # Đính kèm sự kiện gần nhất trong cùng bộ lọc làm chứng cứ cho câu đếm.
            evidence_sql = plan.sql.replace(
                "SELECT COUNT(*) AS total", f"SELECT {EVENT_COLUMNS}", 1
            ) + " ORDER BY timestamp DESC LIMIT 1"
            assert_read_only(evidence_sql)
            evidence_rows = db.execute(text(evidence_sql), plan.params).mappings().all()
            evidence = evidence_rows[0] if evidence_rows else None

        return {
            "answer": answer,
            "sql_query": plan.sql,
            "event_id": evidence["id"] if evidence else None,
            "clip_url": evidence["video_clip_url"] if evidence else None,
        }

    def _answer_list(self, plan: SQLPlan, rows) -> dict:
        if not rows:
            scope = " ".join(plan.filters_desc) if plan.filters_desc else ""
            return {
                "answer": f"Không tìm thấy sự kiện nào {scope}.".replace("  ", " ").strip(),
                "sql_query": plan.sql,
                "event_id": None,
                "clip_url": None,
            }

        newest = rows[0]
        lines = [
            f"- {row['object_class']} · mức {row['severity_level']} · camera {row['camera_id']}"
            for row in rows
        ]
        answer = f"Tìm thấy {len(rows)} sự kiện gần nhất:\n" + "\n".join(lines)
        return {
            "answer": answer,
            "sql_query": plan.sql,
            "event_id": newest["id"],
            "clip_url": newest["video_clip_url"],
        }

    @staticmethod
    def _fallback(answer: str, sql_query: Optional[str] = None) -> dict:
        return {"answer": answer, "sql_query": sql_query, "event_id": None, "clip_url": None}

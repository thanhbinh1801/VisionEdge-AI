"""
LLM Text-to-SQL Assistant Engine & Fallback Rule Engine (ADR-004).

ADR-004 chọn kiến trúc "LLM Text-to-SQL kết hợp Fallback Rule-based Engine".
Hai nhánh được thử theo thứ tự, dừng ở nhánh đầu tiên thành công:

1. Nhánh LLM (TASK-029) — Google Gemini nhận schema rút gọn kèm câu hỏi tiếng
   Việt và trả về một câu `SELECT`.
2. Nhánh Rule Engine (TASK-013) — 5 intent tiếng Việt dựng SQL tham số hóa tĩnh.

Nhánh 2 là lưới an toàn: hệ thống phải trả lời được cả khi không có mạng, không
có `GEMINI_API_KEY`, hoặc chưa cài `google-genai`. SQL của cả hai nhánh đều
được *thực thi thật* trên SQLite và đều đi qua cùng một chốt an toàn.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.services.vision_pipeline import OBJECT_VIETNAMESE_NAMES

logger = logging.getLogger(__name__)

# Trần số dòng áp cho SQL do LLM sinh ra: một câu hỏi mơ hồ không được phép kéo
# nguyên bảng events vào bộ nhớ.
_LLM_ROW_LIMIT = 50

# Schema rút gọn gửi cho LLM. Cố ý chỉ mô tả các cột cần cho hỏi đáp sự kiện,
# không đưa toàn bộ DDL: prompt ngắn thì SQL sinh ra bám sát hơn và rẻ hơn.
_SCHEMA_PROMPT = """\
Bảng và cột khả dụng (SQLite):

events(
  id TEXT, timestamp DATETIME, camera_id TEXT, zone_id TEXT,
  event_type TEXT,        -- 'LPR_PASSAGE' | 'ZONE_VIOLATION' | 'RESTRICTED_ACCESS'
  severity_level INTEGER, -- 1 | 2 | 3, trong đó 3 là nghiêm trọng nhất
  license_plate TEXT,     -- NULL nếu không đọc được biển số
  object_class TEXT,      -- 'container','truck','forklift','crane','car','motorbike','bicycle','person'
  confidence REAL, video_clip_url TEXT, crop_image_url TEXT
)
vehicles(id TEXT, license_plate TEXT, vehicle_type TEXT,
         tag_label TEXT)  -- 'known' (xe quen) | 'unknown' (xe lạ) | 'blacklisted'
zones(id TEXT, camera_id TEXT, name TEXT, is_active BOOLEAN)
cameras(id TEXT, name TEXT, location TEXT, status TEXT)

Nghĩa tiếng Việt: xe quen = tag_label 'known'; xe lạ = tag_label 'unknown';
vi phạm khu vực = event_type 'ZONE_VIOLATION' hoặc 'RESTRICTED_ACCESS';
Container/Xe tải/Xe nâng/Xe cẩu/Xe con/Xe máy/Xe đạp/Người lần lượt là
container/truck/forklift/crane/car/motorbike/bicycle/person.
"""

_LLM_INSTRUCTIONS = f"""\
Bạn là bộ dịch câu hỏi tiếng Việt sang SQL cho hệ thống giám sát camera SentriAI.

Ngữ cảnh nghiệp vụ: hệ thống giám sát an ninh cổng ra vào và bãi kiểm hóa. Người
dùng là nhân viên trực ca, họ hỏi về xe ra vào cổng (nhận dạng biển số), phương
tiện lạ/xe trong danh sách đen, vi phạm khu vực cấm và hoạt động của máy móc
thiết bị trong bãi. Câu hỏi luôn nói về dữ liệu đã ghi nhận trong bảng `events`.

{{schema}}

Quy tắc bắt buộc:
- Chỉ trả về DUY NHẤT một câu lệnh SQLite bắt đầu bằng SELECT.
- Không giải thích, không thêm dấu chấm phẩy, không bọc trong khối markdown.
- Không dùng INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/PRAGMA hay bất kỳ lệnh ghi nào.
- Luôn thêm LIMIT không vượt quá {_LLM_ROW_LIMIT}.
- Ưu tiên trả về số liệu tổng hợp (COUNT, SUM) khi câu hỏi hỏi "bao nhiêu".
- Đặt bí danh (AS) tiếng Việt không dấu, dễ đọc cho các cột kết quả.
- Mốc thời gian hiện tại: {{now}} (giờ Việt Nam, UTC+7).

Quy tắc ánh xạ ngữ nghĩa (bắt buộc lọc đúng, không được đếm cả bảng):
- Hỏi về vi phạm khu vực cấm / xâm nhập / khu vực hạn chế:
  WHERE event_type IN ('ZONE_VIOLATION', 'RESTRICTED_ACCESS')
- Hỏi về xe ra vào cổng / biển số / lượt qua cổng:
  WHERE event_type = 'LPR_PASSAGE'
- Hỏi về xe lạ: JOIN vehicles v ON v.license_plate = e.license_plate
  WHERE v.tag_label = 'unknown' (xe quen: 'known'; danh sách đen: 'blacklisted')
- Hỏi về mức độ nghiêm trọng / cảnh báo nặng: WHERE severity_level = 3
- Hỏi về một loại phương tiện/thiết bị cụ thể: WHERE object_class = '<lớp tương ứng>'
- Chỉ dùng `SELECT COUNT(*) FROM events` không kèm điều kiện khi câu hỏi thật sự
  hỏi tổng số toàn bộ sự kiện. Mọi câu hỏi có chủ đề cụ thể đều phải có WHERE.
"""

# Câu chào hỏi / hỏi năng lực trợ lý: không được dịch sang SQL. Nếu để lọt xuống
# nhánh Text-to-SQL, LLM buộc phải sinh một câu SELECT và thường trả về
# `SELECT COUNT(*) FROM events` — tức là đếm sạch bảng để trả lời chữ "hi".
_CHITCHAT_EXACT = {
    "hi",
    "hii",
    "hey",
    "helo",
    "hello",
    "chao",
    "chao ban",
    "chao bot",
    "xin chao",
    "xin chao ban",
    "hi ban",
    "hello ban",
    "alo",
    "chao buoi sang",
    "chao buoi chieu",
    "chao buoi toi",
    "good morning",
    "ok",
    "oke",
}

_CHITCHAT_PATTERN = re.compile(
    r"\b("
    r"ban la ai|ban ten gi|ban ten la gi|ai tao ra ban|ban do ai tao"
    r"|ban lam duoc gi|ban co the lam gi|ban giup duoc gi|ban biet lam gi"
    r"|tro giup|help|huong dan|cach su dung|dung nhu the nao"
    r"|cam on|thank you|thanks|tam biet|goodbye"
    r")\b"
)

_CHITCHAT_ANSWER = (
    "Xin chào! Tôi là Trợ lý AI giám sát an ninh của SentriAI. "
    "Bạn có thể hỏi tôi về các sự kiện xe ra vào cổng (biển số, số lượt qua cổng), "
    "phương tiện lạ hoặc xe trong danh sách đen, vi phạm khu vực cấm, "
    "và hoạt động của máy móc thiết bị trong bãi. "
    "Ví dụ: “Hôm nay có bao nhiêu xe lạ vào?”, “Có vi phạm khu vực cấm nào không?”, "
    "“Xe nâng hoạt động thế nào tuần này?”. "
    "Khi câu trả lời có sự kiện thật, tôi sẽ kèm clip bằng chứng 10 giây."
)

# Một câu SELECT đơn: chặn kiểu "SELECT 1; DROP TABLE events" nối lệnh qua prompt.
_SINGLE_SELECT_RE = re.compile(r"^\s*SELECT\b[^;]*;?\s*$", re.IGNORECASE | re.DOTALL)

# Sự kiện được ghi theo giờ Việt Nam (xem `datetime.now(ICT_TZ)` trong
# backend/app/api/v1/events.py), nên "hôm nay" phải được tính theo cùng múi giờ
# đó, không phải UTC của máy chủ.
ICT_TZ = timezone(timedelta(hours=7))

# Chốt an toàn: agent chỉ được phép chạy câu lệnh đọc.
_FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|replace|pragma|vacuum)\b",
    re.IGNORECASE,
)

_TAG_LABEL_VN = {
    "known": "xe quen",
    "unknown": "xe lạ",
    "blacklisted": "xe trong danh sách đen",
}

_SEVERITY_VN = {1: "Mức 1 (thấp)", 2: "Mức 2 (trung bình)", 3: "Mức 3 (nghiêm trọng)"}


def _strip_accents(value: str) -> str:
    """Bỏ dấu để so khớp được cả khi người dùng gõ không dấu."""
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn").lower()


def _is_chitchat(normalized: str) -> bool:
    """
    Nhận biết câu chào hỏi / hỏi năng lực trợ lý (không phải câu hỏi dữ liệu).

    Nhận `normalized` đã đi qua `_strip_accents`. Dấu câu bị lược bỏ để "Xin chào!"
    và "xin chao" khớp cùng một mẫu. `đ` không bị NFD tách ra nên phải quy về `d`
    thủ công, nếu không "bạn làm được gì" sẽ thành "ban lam đuoc gi" và trượt mẫu.
    """
    cleaned = normalized.replace("đ", "d")
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return True
    if cleaned in _CHITCHAT_EXACT:
        return True
    return bool(_CHITCHAT_PATTERN.search(cleaned))


@dataclass(frozen=True)
class TimeScope:
    """Khoảng thời gian suy ra từ câu hỏi, kèm cách diễn đạt lại cho câu trả lời."""

    label: str
    start: Optional[datetime]
    end: Optional[datetime]

    def where_clause(self, column: str = "e.timestamp") -> str:
        if self.start is None:
            return ""
        return f" AND {column} >= :ts_start AND {column} < :ts_end"

    def params(self) -> dict:
        if self.start is None:
            return {}
        # SQLAlchemy lưu DateTime của SQLite dạng chuỗi naive; bỏ tzinfo để so sánh
        # cùng hệ quy chiếu với giá trị đã ghi.
        return {
            "ts_start": self.start.replace(tzinfo=None),
            "ts_end": self.end.replace(tzinfo=None),
        }


def _resolve_time_scope(normalized: str, now: Optional[datetime] = None) -> TimeScope:
    current = now or datetime.now(ICT_TZ)
    midnight = current.replace(hour=0, minute=0, second=0, microsecond=0)

    if "hom qua" in normalized:
        return TimeScope("hôm qua", midnight - timedelta(days=1), midnight)
    if "tuan" in normalized:
        return TimeScope("7 ngày qua", midnight - timedelta(days=6), midnight + timedelta(days=1))
    if "thang" in normalized:
        return TimeScope("30 ngày qua", midnight - timedelta(days=29), midnight + timedelta(days=1))
    if "hom nay" in normalized or "hien tai" in normalized:
        return TimeScope("hôm nay", midnight, midnight + timedelta(days=1))
    return TimeScope("toàn bộ dữ liệu đã ghi nhận", None, None)


def _match_object_class(normalized: str) -> Optional[str]:
    """Dò xem câu hỏi có nhắc tới một trong 8 lớp đối tượng chuẩn không."""
    for class_key, vn_name in OBJECT_VIETNAMESE_NAMES.items():
        if _strip_accents(vn_name) in normalized or class_key in normalized:
            return class_key
    return None


@dataclass
class Intent:
    """Một quy tắc: điều kiện khớp, SQL tham số hóa, và cách dựng câu trả lời."""

    name: str
    matches: Callable[[str], bool]
    build: Callable[[str, TimeScope], tuple]


def _sanitize_llm_sql(raw: Optional[str]) -> Optional[str]:
    """
    Làm sạch và kiểm duyệt SQL do LLM trả về.

    Trả `None` nếu SQL không dùng được — caller phải hiểu đó là tín hiệu fallback,
    không phải lỗi cần ném ra ngoài.
    """
    if not raw or not raw.strip():
        return None

    sql = raw.strip()

    # Model hay bọc kết quả trong ```sql ... ``` dù prompt đã dặn không.
    if sql.startswith("```"):
        sql = re.sub(r"^```[a-zA-Z]*\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql).strip()

    if not _SINGLE_SELECT_RE.match(sql):
        logger.warning("SQL từ LLM không phải một câu SELECT đơn, bỏ qua")
        return None
    if _FORBIDDEN_SQL.search(sql):
        logger.warning("SQL từ LLM chạm chốt an toàn _FORBIDDEN_SQL, bỏ qua")
        return None

    sql = sql.rstrip(";").strip()

    # Prompt đã yêu cầu LIMIT nhưng không thể tin model luôn tuân thủ.
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql}\nLIMIT {_LLM_ROW_LIMIT}"
    return sql


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _rows_have_data(rows: Sequence[Any]) -> bool:
    """
    Kết quả có phản ánh sự kiện có thật không?

    Một dòng aggregate toàn số 0 (`COUNT(*) = 0`) về mặt kỹ thuật là "có dòng"
    nhưng về mặt nghiệp vụ là *không có sự kiện nào* — nên không được kèm clip
    bằng chứng cho nó.
    """
    if not rows:
        return False
    for row in rows:
        for value in row._mapping.values():
            if value is None:
                continue
            if _is_number(value):
                if value != 0:
                    return True
            else:
                return True
    return False


def _humanize_alias(alias: str) -> str:
    """`camera_count` -> `camera count`: bí danh SQL đọc được trong câu trả lời."""
    return str(alias).replace("_", " ").strip() or "giá trị"


def _fmt_value(value: Any) -> str:
    if value is None:
        return "không có"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _render_llm_rows(rows: Sequence[Any]) -> Optional[str]:
    """
    Dựng câu trả lời tiếng Việt tự nhiên từ tập kết quả có hình dạng bất kỳ.

    Cách diễn giải chỉ dựa vào *hình dạng kết quả và bí danh cột*, không dựa vào
    câu hỏi gốc: SQL do LLM sinh ra mới là thứ quyết định con số, nên diễn giải
    theo câu hỏi sẽ có nguy cơ gán nhãn sai cho dữ liệu.
    """
    if not rows:
        return "Không có dữ liệu nào phù hợp với yêu cầu của bạn."

    if not _rows_have_data(rows):
        return "Không có sự kiện nào phù hợp với yêu cầu của bạn."

    def describe(row) -> str:
        mapping = row._mapping
        parts = [f"{_humanize_alias(key)}: {_fmt_value(val)}" for key, val in mapping.items()]
        return ", ".join(parts)

    if len(rows) == 1:
        mapping = rows[0]._mapping
        if len(mapping) == 1:
            value = next(iter(mapping.values()))
            if _is_number(value):
                # Truy vấn tổng hợp một ô: dạng câu hỏi "bao nhiêu" phổ biến nhất.
                return (
                    f"Ghi nhận {_fmt_value(value)} sự kiện phù hợp với yêu cầu của bạn "
                    "trong dữ liệu giám sát đã lưu."
                )
            return f"Kết quả tôi tra được là: {_fmt_value(value)}."
        return f"Kết quả tra cứu — {describe(rows[0])}."

    shown = [f"• {describe(r)}" for r in rows[:5]]
    header = f"Tôi tìm thấy {len(rows)} kết quả phù hợp"
    if len(rows) > 5:
        header += " (hiển thị 5 kết quả đầu)"
    return header + ":\n" + "\n".join(shown)


class GeminiSqlGenerator:
    """
    Sinh SQL bằng Google Gemini (ADR-004).

    Mọi lỗi đều được nuốt và quy về `None` để `LLMQAAgent` rơi xuống Rule Engine:
    trợ lý không được chết chỉ vì nhà cung cấp LLM có sự cố.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None

    def available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self):
        if self._client is not None:
            return self._client
        # Import trễ: `google-genai` là dependency tùy chọn, thiếu nó thì hệ thống
        # vẫn phải chạy được bằng Rule Engine.
        from google import genai

        self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_sql(self, user_query: str, now: Optional[datetime] = None) -> Optional[str]:
        if not self.available():
            return None

        current = now or datetime.now(ICT_TZ)
        prompt = _LLM_INSTRUCTIONS.format(
            schema=_SCHEMA_PROMPT,
            now=current.strftime("%Y-%m-%d %H:%M:%S"),
        )
        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.model,
                contents=f"{prompt}\n\nCâu hỏi: {user_query}\nSQL:",
            )
            return _sanitize_llm_sql(getattr(response, "text", None))
        except ImportError:
            logger.warning("Chưa cài `google-genai`; dùng Rule Engine thay thế")
            return None
        except Exception:
            logger.exception("Gọi Gemini thất bại; dùng Rule Engine thay thế")
            return None


class LLMQAAgent:
    """
    LLM Text-to-SQL Assistant Engine & Fallback Rule Engine (ADR-004).
    """

    def __init__(self, llm: Optional[GeminiSqlGenerator] = None):
        self._intents = self._build_intents()
        self._llm = llm if llm is not None else GeminiSqlGenerator()
        logger.info(
            "Initialized LLMQAAgent (llm=%s, model=%s, %d rule intents)",
            "on" if self._llm.available() else "off",
            self._llm.model,
            len(self._intents),
        )

    # ------------------------------------------------------------------ intents

    def _build_intents(self) -> Sequence[Intent]:
        return (
            Intent("vehicle_by_tag", self._is_vehicle_tag_question, self._build_vehicle_tag_query),
            Intent("zone_violation", self._is_violation_question, self._build_violation_query),
            Intent("object_class", self._is_object_class_question, self._build_object_class_query),
            Intent("plate_lookup", self._is_plate_question, self._build_plate_query),
            Intent("event_count", lambda _: True, self._build_event_count_query),
        )

    @staticmethod
    def _is_vehicle_tag_question(normalized: str) -> bool:
        return any(k in normalized for k in ("xe la", "xe quen", "danh sach den", "bien so la"))

    @staticmethod
    def _is_violation_question(normalized: str) -> bool:
        return any(
            k in normalized
            for k in ("vi pham", "xam nhap", "khu vuc cam", "canh bao", "muc 3", "nghiem trong")
        )

    @staticmethod
    def _is_object_class_question(normalized: str) -> bool:
        return _match_object_class(normalized) is not None

    @staticmethod
    def _is_plate_question(normalized: str) -> bool:
        return any(k in normalized for k in ("bien so", "bien kiem soat"))

    # ------------------------------------------------------------- query builds

    def _build_vehicle_tag_query(self, normalized: str, scope: TimeScope) -> tuple:
        if "xe quen" in normalized:
            tag = "known"
        elif "danh sach den" in normalized:
            tag = "blacklisted"
        else:
            tag = "unknown"

        sql = (
            "SELECT COUNT(DISTINCT e.license_plate) AS plate_count, COUNT(*) AS event_count\n"
            "FROM events e\n"
            "JOIN vehicles v ON v.license_plate = e.license_plate\n"
            "WHERE v.tag_label = :tag" + scope.where_clause()
        )
        params = {"tag": tag, **scope.params()}

        def render(rows):
            row = rows[0] if rows else None
            plates = (row.plate_count if row else 0) or 0
            events = (row.event_count if row else 0) or 0
            if plates == 0:
                return f"Không có {_TAG_LABEL_VN[tag]} nào được ghi nhận trong {scope.label}."
            return (
                f"Ghi nhận {plates} {_TAG_LABEL_VN[tag]} khác nhau "
                f"qua {events} lượt trong {scope.label}."
            )

        return sql, params, render, {"tag": tag}

    def _build_violation_query(self, normalized: str, scope: TimeScope) -> tuple:
        only_severe = "muc 3" in normalized or "nghiem trong" in normalized
        severity_clause = " AND e.severity_level = 3" if only_severe else ""

        sql = (
            "SELECT COUNT(*) AS total, MAX(e.severity_level) AS max_severity\n"
            "FROM events e\n"
            "WHERE e.event_type IN ('ZONE_VIOLATION', 'RESTRICTED_ACCESS')"
            + severity_clause
            + scope.where_clause()
        )
        params = dict(scope.params())

        def render(rows):
            row = rows[0] if rows else None
            total = (row.total if row else 0) or 0
            if total == 0:
                return f"Không có vi phạm khu vực nào trong {scope.label}."
            max_sev = (row.max_severity if row else None) or 0
            sev_text = _SEVERITY_VN.get(max_sev, f"Mức {max_sev}")
            prefix = "vi phạm Mức 3" if only_severe else "vi phạm khu vực"
            return (
                f"Ghi nhận {total} {prefix} trong {scope.label}. "
                f"Mức nghiêm trọng cao nhất: {sev_text}."
            )

        clip_filter = (
            "e.event_type IN ('ZONE_VIOLATION', 'RESTRICTED_ACCESS')" + severity_clause
        )
        return sql, params, render, {"clip_filter": clip_filter}

    def _build_object_class_query(self, normalized: str, scope: TimeScope) -> tuple:
        class_key = _match_object_class(normalized) or "person"
        vn_name = OBJECT_VIETNAMESE_NAMES.get(class_key, class_key)

        sql = (
            "SELECT COUNT(*) AS total, COUNT(DISTINCT e.camera_id) AS camera_count\n"
            "FROM events e\n"
            "WHERE e.object_class = :object_class" + scope.where_clause()
        )
        params = {"object_class": class_key, **scope.params()}

        def render(rows):
            row = rows[0] if rows else None
            total = (row.total if row else 0) or 0
            if total == 0:
                return f"Không ghi nhận hoạt động nào của {vn_name} trong {scope.label}."
            cameras = (row.camera_count if row else 0) or 0
            return (
                f"{vn_name} xuất hiện trong {total} sự kiện "
                f"trên {cameras} camera, tính trong {scope.label}."
            )

        return sql, params, render, {"clip_filter": "e.object_class = :object_class"}

    def _build_plate_query(self, normalized: str, scope: TimeScope) -> tuple:
        sql = (
            "SELECT e.license_plate AS plate, COUNT(*) AS total\n"
            "FROM events e\n"
            "WHERE e.license_plate IS NOT NULL" + scope.where_clause() + "\n"
            "GROUP BY e.license_plate\n"
            "ORDER BY total DESC, plate ASC\n"
            "LIMIT 5"
        )
        params = dict(scope.params())

        def render(rows):
            if not rows:
                return f"Chưa đọc được biển số nào trong {scope.label}."
            listed = ", ".join(f"{r.plate} ({r.total} lượt)" for r in rows)
            return f"Biển số ghi nhận nhiều nhất trong {scope.label}: {listed}."

        return sql, params, render, {"clip_filter": "e.license_plate IS NOT NULL"}

    def _build_event_count_query(self, normalized: str, scope: TimeScope) -> tuple:
        sql = (
            "SELECT COUNT(*) AS total, COUNT(DISTINCT e.camera_id) AS camera_count\n"
            "FROM events e\n"
            "WHERE 1 = 1" + scope.where_clause()
        )
        params = dict(scope.params())

        def render(rows):
            row = rows[0] if rows else None
            total = (row.total if row else 0) or 0
            if total == 0:
                return f"Chưa có sự kiện nào được ghi nhận trong {scope.label}."
            cameras = (row.camera_count if row else 0) or 0
            return f"Hệ thống đã ghi nhận {total} sự kiện trên {cameras} camera trong {scope.label}."

        return sql, params, render, {}

    # ---------------------------------------------------------------- execution

    def _latest_clip_url(
        self, session: Session, scope: TimeScope, extra: dict, params: dict
    ) -> Optional[str]:
        """
        Lấy clip bằng chứng của sự kiện khớp gần nhất — chỉ trả URL có thật trong CSDL.

        Không bịa đường dẫn mặc định: câu trả lời không có bằng chứng thì
        `clip_url` phải là None để UI hiển thị đúng trạng thái đó.
        """
        clip_filter = extra.get("clip_filter")
        where = "e.video_clip_url IS NOT NULL AND e.video_clip_url <> ''"
        if clip_filter:
            where += f" AND {clip_filter}"
        if extra.get("tag"):
            where += (
                " AND e.license_plate IN"
                " (SELECT v.license_plate FROM vehicles v WHERE v.tag_label = :tag)"
            )

        sql = (
            "SELECT e.video_clip_url AS clip\n"
            "FROM events e\n"
            f"WHERE {where}" + scope.where_clause() + "\n"
            "ORDER BY e.timestamp DESC\n"
            "LIMIT 1"
        )
        try:
            row = session.execute(text(sql), params).fetchone()
        except Exception:
            logger.exception("Không truy vấn được clip bằng chứng")
            return None
        return row.clip if row else None

    def _try_llm_branch(
        self, user_query: str, session: Session, scope: TimeScope
    ) -> Optional[dict]:
        """
        Nhánh 1 của ADR-004. Trả `None` ở mọi điều kiện fallback đã quy định.
        """
        try:
            sql = self._llm.generate_sql(user_query)
        except Exception:
            # GeminiSqlGenerator đã tự nuốt lỗi, nhưng generator có thể được thay
            # bằng cài đặt khác; không để lỗi provider làm hỏng cả câu trả lời.
            logger.exception("Generator SQL ném lỗi; chuyển sang Rule Engine")
            return None
        if not sql:
            return None

        try:
            rows = session.execute(text(sql)).fetchall()
        except Exception:
            # SQL sinh ra sai cột/sai cú pháp là chuyện bình thường với LLM;
            # rollback để session còn dùng được cho nhánh Rule Engine phía sau.
            logger.exception("SQL từ Gemini chạy lỗi; chuyển sang Rule Engine")
            session.rollback()
            return None

        answer = _render_llm_rows(rows)
        if answer is None:
            return None

        # Clip bằng chứng chỉ có nghĩa khi truy vấn thật sự trả về sự kiện; gắn
        # clip vào một câu trả lời "không có gì" là bịa bằng chứng.
        clip_url = (
            self._latest_clip_url(session, scope, {}, scope.params())
            if _rows_have_data(rows)
            else None
        )
        logger.info("QA branch=llm model=%s", self._llm.model)
        return {"answer": answer, "sql_query": sql, "clip_url": clip_url}

    def answer_question(self, user_query: str, session: Optional[Session] = None) -> dict:
        """
        Trả lời câu hỏi tiếng Việt bằng SQL thật chạy trên CSDL sự kiện.

        Thử nhánh LLM trước, rơi xuống Rule Engine khi nhánh LLM không dùng được
        (ADR-004). Trả về dict đúng `QueryResponse`: `answer`, `sql_query`,
        `clip_url`. `sql_query` là chính câu lệnh đã được thực thi.
        """
        normalized = _strip_accents(user_query or "")

        # Chặn trước cả hai nhánh: câu chào hỏi không có ý định truy vấn dữ liệu,
        # nên không mở session, không sinh SQL và không kèm clip bằng chứng.
        if _is_chitchat(normalized):
            logger.info("QA branch=chitchat")
            return {"answer": _CHITCHAT_ANSWER, "sql_query": None, "clip_url": None}

        scope = _resolve_time_scope(normalized)

        owns_session = session is None
        if owns_session:
            from backend.database.engine import SessionLocal

            session = SessionLocal()
        try:
            llm_result = self._try_llm_branch(user_query, session, scope)
            if llm_result is not None:
                return llm_result
            return self._answer_with_rules(normalized, scope, session)
        finally:
            if owns_session:
                session.close()

    def _answer_with_rules(
        self, normalized: str, scope: TimeScope, session: Session
    ) -> dict:
        """Nhánh 2 của ADR-004: Rule Engine tiếng Việt với SQL tham số hóa tĩnh."""
        intent = next(i for i in self._intents if i.matches(normalized))
        sql, params, render, extra = intent.build(normalized, scope)

        if _FORBIDDEN_SQL.search(sql):
            # Không thể xảy ra với các mẫu tĩnh ở trên, nhưng giữ chốt này như lớp
            # phòng vệ cuối nếu ai đó sửa mẫu SQL trong tương lai.
            logger.error("Chặn câu lệnh không phải SELECT từ intent %s", intent.name)
            return {
                "answer": "Trợ lý chỉ được phép truy vấn dữ liệu, không thể thực hiện yêu cầu này.",
                "sql_query": None,
                "clip_url": None,
            }

        try:
            rows = session.execute(text(sql), params).fetchall()
            answer = render(rows)
            clip_url = (
                self._latest_clip_url(session, scope, extra, params)
                if _rows_have_data(rows)
                else None
            )
        except Exception as exc:
            logger.exception("Text-to-SQL thất bại cho intent %s", intent.name)
            return {
                "answer": f"Không truy vấn được dữ liệu sự kiện: {exc}",
                "sql_query": sql,
                "clip_url": None,
            }

        logger.info("QA branch=rules intent=%s scope=%s", intent.name, scope.label)
        return {"answer": answer, "sql_query": sql, "clip_url": clip_url}

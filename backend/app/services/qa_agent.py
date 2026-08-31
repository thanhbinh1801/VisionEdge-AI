"""
Trợ lý hỏi đáp sự kiện: LLM → QuerySpec → SQL do backend dựng (ADR-004 rev.2).

Bản trước để Gemini sinh thẳng SQL. Cách đó đặt lên vai mô hình những thứ nó
không thể biết chắc — tên cột, giá trị enum thật trong DB, cách join `vehicles` —
và khi sai thì sai *im lặng*: truy vấn chạy được, trả 0 dòng, câu trả lời nghe
vẫn trôi chảy.

Bản này chia lại việc:

1. Chặn chitchat — câu chào không có ý định truy vấn, không tốn lượt gọi LLM.
2. Gemini trả về `QuerySpec` (JSON có schema cố định), không phải SQL.
3. `compile_spec` dựng SQL tham số hóa. Backend là nơi duy nhất biết schema.
4. Không dùng được LLM thì Rule Engine sinh **cùng một `QuerySpec`**, nên chỉ có
   một đường biên dịch và một đường diễn giải cho cả hai nhánh.

Clip bằng chứng lấy từ chính bộ lọc của truy vấn, nên không thể lạc đề so với
câu hỏi — đó là lỗi cấu trúc của bản trước.
"""

import json
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.services.query_spec import (
    ICT_TZ,
    MAX_CLIPS,
    MAX_LIMIT,
    CompiledQuery,
    EventTypeKey,
    GroupBy,
    Metric,
    ObjectClassKey,
    QuerySpec,
    TagLabel,
    TimeRange,
    class_display_name,
    compile_spec,
    render_answer,
    rows_have_data,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ICT_TZ",
    "GeminiSpecGenerator",
    "LLMQAAgent",
    "rule_spec_from_question",
]


# --------------------------------------------------------------------- chitchat

# Câu chào hỏi / hỏi năng lực trợ lý: không được dịch thành truy vấn. Nếu để lọt
# xuống nhánh sinh spec, mô hình buộc phải trả về một spec nào đó và thường ra
# `metric=count` không bộ lọc — tức đếm sạch bảng để trả lời chữ "hi".
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


# ------------------------------------------------------------- schema cho Gemini

# Schema viết tay thay vì suy ra từ Pydantic: giữ toàn quyền kiểm soát tập con
# OpenAPI mà Gemini chấp nhận, và tránh việc đổi model Pydantic vô tình đổi luôn
# hợp đồng gửi cho nhà cung cấp LLM.
_SPEC_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "metric": {
            "type": "string",
            "enum": [m.value for m in Metric],
            "description": (
                "count = đếm số sự kiện; list = liệt kê từng sự kiện kèm clip; "
                "breakdown = thống kê theo nhóm; top_plates = biển số nhiều lượt nhất"
            ),
        },
        "event_type": {
            "type": "array",
            "items": {"type": "string", "enum": [t.value for t in EventTypeKey]},
        },
        "object_class": {
            "type": "array",
            "items": {"type": "string", "enum": [o.value for o in ObjectClassKey]},
        },
        "tag_label": {
            "type": "array",
            "items": {"type": "string", "enum": [t.value for t in TagLabel]},
        },
        "min_severity": {"type": "integer", "description": "1..3, chỉ đặt khi hỏi mức nghiêm trọng"},
        "license_plate": {"type": "string"},
        "camera_id": {"type": "string"},
        "time_range": {"type": "string", "enum": [t.value for t in TimeRange]},
        "group_by": {"type": "string", "enum": [g.value for g in GroupBy]},
        "limit": {"type": "integer"},
        "offset": {"type": "integer", "description": "Bỏ qua N kết quả đầu, dùng cho 'còn nữa không'"},
        "want_clips": {"type": "boolean"},
    },
    # `time_range` phải nằm trong required: khi để tùy chọn, mô hình hay bỏ trống
    # trường này và spec rơi về mặc định "all" — câu hỏi "tháng này" khi đó bị trả
    # lời bằng số liệu toàn bộ lịch sử. Bắt buộc chọn thì mô hình phải cân nhắc.
    "required": ["metric", "time_range"],
}

_SPEC_INSTRUCTIONS = f"""\
Bạn là bộ phân tích ý định của trợ lý giám sát an ninh SentriAI (cảng/kho vận).

Nhiệm vụ: đọc câu hỏi tiếng Việt của nhân viên trực ca và trả về DUY NHẤT một
đối tượng JSON mô tả truy vấn cần chạy. Không viết SQL. Không giải thích.

Ngữ nghĩa các trường:
- metric: "count" cho "có bao nhiêu"; "list" cho "liệt kê / cho tôi xem / đưa tôi
  N clip"; "breakdown" cho "loại nào nhiều nhất / phân bố theo"; "top_plates" cho
  "biển số nào ra vào nhiều nhất".
- event_type: "LPR_PASSAGE" = xe ra vào cổng, đọc biển số. "ZONE_VIOLATION" và
  "RESTRICTED_ACCESS" = vi phạm khu vực cấm / xâm nhập. Hỏi về vi phạm thì đưa cả
  hai giá trị này.
- object_class: container=Container, truck=Xe tải, forklift=Xe nâng, crane=Xe cẩu,
  car=Xe con, motorbike=Xe máy, bicycle=Xe đạp, person=Người.
- tag_label: known=xe quen, unknown=xe lạ, blacklisted=xe trong danh sách đen.
- min_severity: chỉ đặt khi câu hỏi nhắc tới mức nghiêm trọng (mức 3, nghiêm
  trọng, nặng).
- time_range: "hôm nay/bây giờ/hiện tại" -> today; "hôm qua" -> yesterday;
  "tuần này/tuần qua/tuần rồi/7 ngày" -> week; "tháng này/tháng qua/tháng rồi/
  30 ngày" -> month. Câu hỏi không nhắc thời gian thì để "all". Luôn đặt trường
  này khi câu hỏi có nhắc mốc thời gian, đừng bỏ về "all".
- limit: số kết quả người dùng muốn. "đưa tôi 2 clip" -> metric=list, limit=2.
- offset: chỉ đặt >0 khi người dùng xin xem tiếp ("còn nữa không", "tiếp đi").
- want_clips: true khi người dùng muốn xem clip/bằng chứng/video, và luôn true khi
  câu hỏi nói về vi phạm hoặc cảnh báo (kể cả khi chỉ hỏi số lượng).

Quy tắc bắt buộc:
- Chủ đề cụ thể thì phải có bộ lọc tương ứng. Chỉ để mọi mảng rỗng khi người dùng
  thật sự hỏi tổng số toàn bộ sự kiện.
- Không bịa camera_id hay license_plate nếu câu hỏi không nêu.
- limit không vượt quá {MAX_LIMIT}.

Ví dụ:
Câu hỏi: "Hôm nay có bao nhiêu xe lạ vào?"
{{"metric":"count","event_type":["LPR_PASSAGE"],"tag_label":["unknown"],"time_range":"today"}}

Câu hỏi: "Có vi phạm khu vực cấm nào không?"
{{"metric":"count","event_type":["ZONE_VIOLATION","RESTRICTED_ACCESS"],"time_range":"all","want_clips":true}}

Câu hỏi: "Đưa tôi 2 clip vi phạm"
{{"metric":"list","event_type":["ZONE_VIOLATION","RESTRICTED_ACCESS"],"limit":2,"want_clips":true}}

Câu hỏi: "Xe nâng hoạt động thế nào tuần này?"
{{"metric":"count","object_class":["forklift"],"time_range":"week"}}

Câu hỏi: "Loại xe nào vi phạm nhiều nhất tháng này?"
{{"metric":"breakdown","event_type":["ZONE_VIOLATION","RESTRICTED_ACCESS"],"group_by":"object_class","time_range":"month"}}

Câu hỏi: "Biển số nào ra vào nhiều nhất?"
{{"metric":"top_plates","event_type":["LPR_PASSAGE"],"time_range":"all"}}
"""


def _coerce_spec_payload(payload: Any) -> dict:
    """
    Gạn payload thô của LLM về đúng hình dạng `QuerySpec`.

    Lọc bớt giá trị lạ thay vì để Pydantic đánh trượt cả spec: một mảng
    `object_class` có lẫn giá trị bịa vẫn còn dùng được phần hợp lệ, và đánh trượt
    toàn bộ chỉ khiến trợ lý rơi xuống Rule Engine một cách không cần thiết.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload không phải object JSON")

    def _clean_enum_list(key: str, allowed: set[str], *, upper: bool = False) -> list[str]:
        raw = payload.get(key) or []
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return []
        out = []
        for item in raw:
            value = str(item).strip()
            value = value.upper() if upper else value.lower()
            if value in allowed and value not in out:
                out.append(value)
        return out

    cleaned: dict[str, Any] = {
        "event_type": _clean_enum_list(
            "event_type", {t.value for t in EventTypeKey}, upper=True
        ),
        "object_class": _clean_enum_list("object_class", {o.value for o in ObjectClassKey}),
        "tag_label": _clean_enum_list("tag_label", {t.value for t in TagLabel}),
    }

    metric = str(payload.get("metric", "")).strip().lower()
    cleaned["metric"] = metric if metric in {m.value for m in Metric} else Metric.COUNT.value

    time_range = str(payload.get("time_range", "")).strip().lower()
    if time_range in {t.value for t in TimeRange}:
        cleaned["time_range"] = time_range

    group_by = str(payload.get("group_by", "")).strip().lower()
    if group_by in {g.value for g in GroupBy}:
        cleaned["group_by"] = group_by

    severity = payload.get("min_severity")
    if isinstance(severity, (int, float)) and 1 <= int(severity) <= 3:
        cleaned["min_severity"] = int(severity)

    for key in ("license_plate", "camera_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            cleaned[key] = value.strip()

    limit = payload.get("limit")
    if isinstance(limit, (int, float)) and int(limit) >= 1:
        cleaned["limit"] = min(int(limit), MAX_LIMIT)

    offset = payload.get("offset")
    if isinstance(offset, (int, float)) and int(offset) >= 0:
        cleaned["offset"] = int(offset)

    if isinstance(payload.get("want_clips"), bool):
        cleaned["want_clips"] = payload["want_clips"]

    return cleaned


class GeminiSpecGenerator:
    """
    Sinh `QuerySpec` bằng Google Gemini ở chế độ structured output.

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

    def _build_prompt(
        self,
        user_query: str,
        *,
        now: datetime,
        history: Optional[Sequence[dict]] = None,
        previous_spec: Optional[dict] = None,
        correction: Optional[str] = None,
    ) -> str:
        parts = [
            _SPEC_INSTRUCTIONS,
            f"Mốc thời gian hiện tại: {now.strftime('%Y-%m-%d %H:%M:%S')} (giờ Việt Nam, UTC+7).",
        ]

        if history:
            lines = []
            for turn in history[-4:]:
                role = "Người dùng" if turn.get("role") == "user" else "Trợ lý"
                content = str(turn.get("text") or "").strip().replace("\n", " ")
                if content:
                    lines.append(f"{role}: {content[:200]}")
            if lines:
                parts.append(
                    "Ngữ cảnh hội thoại gần đây (dùng để hiểu câu hỏi rút gọn như "
                    '"còn nữa không", "lọc theo camera cổng"):\n' + "\n".join(lines)
                )

        if previous_spec:
            parts.append(
                "Truy vấn của lượt trước (JSON). Nếu câu hỏi mới là câu hỏi tiếp nối, "
                "hãy sửa đổi truy vấn này thay vì dựng lại từ đầu:\n"
                + json.dumps(previous_spec, ensure_ascii=False)
            )

        if correction:
            parts.append(
                "Lần trả lời trước của bạn không dùng được: "
                f"{correction}\nHãy trả lại JSON đúng schema."
            )

        parts.append(f"Câu hỏi: {user_query}\nJSON:")
        return "\n\n".join(parts)

    def generate_spec(
        self,
        user_query: str,
        *,
        now: Optional[datetime] = None,
        history: Optional[Sequence[dict]] = None,
        previous_spec: Optional[dict] = None,
        correction: Optional[str] = None,
    ) -> Optional[QuerySpec]:
        if not self.available():
            return None

        prompt = self._build_prompt(
            user_query,
            now=now or datetime.now(ICT_TZ),
            history=history,
            previous_spec=previous_spec,
            correction=correction,
        )
        try:
            from google.genai import types

            client = self._get_client()
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_SPEC_JSON_SCHEMA,
                    temperature=0.0,
                ),
            )
            raw = getattr(response, "text", None)
        except ImportError:
            logger.warning("Chưa cài `google-genai`; dùng Rule Engine thay thế")
            return None
        except Exception:
            logger.exception("Gọi Gemini thất bại; dùng Rule Engine thay thế")
            return None

        return self.parse_spec(raw)

    @staticmethod
    def parse_spec(raw: Optional[str]) -> Optional[QuerySpec]:
        """Chuỗi JSON thô -> `QuerySpec`. Trả `None` khi không dùng được."""
        if not raw or not str(raw).strip():
            return None

        text_value = str(raw).strip()
        # Model đôi khi vẫn bọc kết quả trong ```json ... ``` dù đã bật JSON mode.
        if text_value.startswith("```"):
            text_value = re.sub(r"^```[a-zA-Z]*\s*", "", text_value)
            text_value = re.sub(r"\s*```$", "", text_value).strip()

        try:
            payload = json.loads(text_value)
        except (ValueError, TypeError):
            logger.warning("Gemini không trả về JSON hợp lệ, bỏ qua")
            return None

        # Một số phiên bản trả về mảng chứa đúng một object.
        if isinstance(payload, list) and len(payload) == 1:
            payload = payload[0]

        try:
            return QuerySpec.model_validate(_coerce_spec_payload(payload))
        except Exception:
            logger.warning("JSON của Gemini không khớp QuerySpec, bỏ qua", exc_info=True)
            return None


# ------------------------------------------------------------------ Rule Engine

_OBJECT_CLASS_KEYWORDS = {
    ObjectClassKey.CONTAINER: ("container", "thung hang"),
    ObjectClassKey.TRUCK: ("xe tai", "xe container", "truck"),
    ObjectClassKey.FORKLIFT: ("xe nang", "forklift"),
    ObjectClassKey.CRANE: ("xe cau", "can cau", "crane"),
    ObjectClassKey.CAR: ("xe con", "xe hoi", "o to", "car"),
    ObjectClassKey.MOTORBIKE: ("xe may", "mo to", "motorbike"),
    ObjectClassKey.BICYCLE: ("xe dap", "bicycle"),
    ObjectClassKey.PERSON: ("nguoi", "cong nhan", "person"),
}

_VIOLATION_KEYWORDS = ("vi pham", "xam nhap", "khu vuc cam", "canh bao", "muc 3", "nghiem trong")
_GATE_KEYWORDS = ("ra vao", "qua cong", "vao cong", "ra cong", "bien so", "bien kiem soat", "lpr")
_LIST_KEYWORDS = ("liet ke", "cho toi xem", "dua toi", "xem clip", "clip", "video", "bang chung")
_MORE_KEYWORDS = ("con nua", "con khong", "tiep di", "tiep theo", "xem them", "con gi nua")

# "loại nào", "loại xe nào", "loại phương tiện nào" — cùng một ý định thống kê.
# Dùng regex thay vì danh sách chuỗi cố định vì phần đệm ở giữa quá nhiều biến thể.
_BREAKDOWN_RE = re.compile(
    r"(loai\s+(?:\w+\s+){0,2}nao|camera\s+nao|ngay\s+nao"
    r"|phan bo|thong ke theo|nhom theo|theo camera|theo ngay|theo loai)"
)


def _extract_leading_count(normalized: str) -> Optional[int]:
    """"đưa tôi 2 clip" -> 2. Chỉ nhận số nhỏ để không nuốt nhầm biển số."""
    match = re.search(r"\b(\d{1,2})\s*(clip|video|su kien|ket qua|cai|dong)", normalized)
    if match:
        return max(1, min(int(match.group(1)), MAX_LIMIT))
    return None


def _resolve_time_range(normalized: str) -> TimeRange:
    if "hom qua" in normalized:
        return TimeRange.YESTERDAY
    if "tuan" in normalized:
        return TimeRange.WEEK
    if "thang" in normalized:
        return TimeRange.MONTH
    if "hom nay" in normalized or "hien tai" in normalized:
        return TimeRange.TODAY
    return TimeRange.ALL


def rule_spec_from_question(
    normalized: str, previous_spec: Optional[QuerySpec] = None
) -> QuerySpec:
    """
    Nhánh dự phòng: dựng `QuerySpec` bằng từ khóa tiếng Việt, không cần mạng.

    Trả về *cùng kiểu* với nhánh LLM, nên toàn bộ phần biên dịch, diễn giải và
    gắn clip phía sau chỉ có một đường chạy duy nhất.
    """
    # "còn nữa không" là câu hỏi tiếp nối: giữ nguyên bộ lọc cũ, chỉ đẩy offset.
    if previous_spec is not None and any(k in normalized for k in _MORE_KEYWORDS):
        return previous_spec.model_copy(
            update={
                "metric": Metric.LIST,
                "offset": previous_spec.offset + previous_spec.limit,
                "want_clips": True,
            }
        )

    fields: dict[str, Any] = {"time_range": _resolve_time_range(normalized)}

    if any(k in normalized for k in _VIOLATION_KEYWORDS):
        fields["event_type"] = [EventTypeKey.ZONE_VIOLATION, EventTypeKey.RESTRICTED_ACCESS]
        # Câu hỏi về vi phạm luôn cần bằng chứng, kể cả khi chỉ hỏi số lượng:
        # "có 12 vi phạm" mà không xem được clip nào thì không dùng để xử lý ca trực.
        fields["want_clips"] = True
    elif any(k in normalized for k in _GATE_KEYWORDS):
        fields["event_type"] = [EventTypeKey.LPR_PASSAGE]

    if "muc 3" in normalized or "nghiem trong" in normalized:
        fields["min_severity"] = 3

    if "xe quen" in normalized:
        fields["tag_label"] = [TagLabel.KNOWN]
    elif "danh sach den" in normalized:
        fields["tag_label"] = [TagLabel.BLACKLISTED]
    elif "xe la" in normalized or "bien so la" in normalized:
        fields["tag_label"] = [TagLabel.UNKNOWN]

    # Nhãn quen/lạ/danh sách đen gắn với biển số, mà biển số chỉ đọc được ở cổng.
    # Không chốt lại event_type thì câu trả lời hiện ra là "sự kiện" chung chung
    # trong khi người hỏi đang nói về lượt xe ra vào.
    if "tag_label" in fields and "event_type" not in fields:
        fields["event_type"] = [EventTypeKey.LPR_PASSAGE]

    # Bộ lọc loại đối tượng chỉ áp khi câu hỏi *không* nói về nhóm biển số: "xe lạ"
    # là thuộc tính đăng ký, không phải lớp thị giác.
    if "tag_label" not in fields:
        for class_key, keywords in _OBJECT_CLASS_KEYWORDS.items():
            if any(k in normalized for k in keywords):
                fields["object_class"] = [class_key]
                break

    requested = _extract_leading_count(normalized)
    if _BREAKDOWN_RE.search(normalized):
        fields["metric"] = Metric.BREAKDOWN
        if "camera" in normalized:
            fields["group_by"] = GroupBy.CAMERA
        elif "ngay" in normalized:
            fields["group_by"] = GroupBy.DAY
        else:
            fields["group_by"] = GroupBy.OBJECT_CLASS
    elif "bien so nao" in normalized or "bien so ra vao" in normalized:
        fields["metric"] = Metric.TOP_PLATES
    elif requested is not None or any(k in normalized for k in _LIST_KEYWORDS):
        fields["metric"] = Metric.LIST
        fields["limit"] = requested or 5
    else:
        fields["metric"] = Metric.COUNT

    return QuerySpec(**fields)


# ----------------------------------------------------------------------- agent


def _clip_label(row: Any) -> str:
    mapping = row._mapping
    bits = [class_display_name(mapping.get("lop_doi_tuong"))]
    if mapping.get("bien_so"):
        bits.append(str(mapping["bien_so"]))
    if mapping.get("khu_vuc"):
        bits.append(str(mapping["khu_vuc"]))
    elif mapping.get("camera"):
        bits.append(str(mapping["camera"]))
    return " · ".join(bits)


def _collect_clips(rows: Sequence[Any]) -> list[dict]:
    """
    Dựng danh sách clip bằng chứng từ các dòng kết quả.

    Khử trùng lặp theo URL: nhiều sự kiện khác nhau vẫn có thể trỏ về cùng một
    file video nguồn, và hiển thị hai trình phát y hệt nhau chỉ làm người xem
    tưởng trợ lý đang lặp lại chính nó.
    """
    clips: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        mapping = row._mapping
        url = mapping.get("clip_url")
        if not url or url in seen:
            continue
        seen.add(url)
        timestamp = mapping.get("thoi_diem")
        clips.append(
            {
                "event_id": mapping.get("event_id"),
                "url": url,
                "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp or ""),
                "camera": mapping.get("camera"),
                "label": _clip_label(row),
            }
        )
        if len(clips) >= MAX_CLIPS:
            break
    return clips


class LLMQAAgent:
    """Trợ lý hỏi đáp sự kiện (ADR-004 rev.2)."""

    def __init__(self, llm: Optional[GeminiSpecGenerator] = None):
        self._llm = llm if llm is not None else GeminiSpecGenerator()
        logger.info(
            "Initialized LLMQAAgent (llm=%s, model=%s)",
            "on" if self._llm.available() else "off",
            self._llm.model,
        )

    # ------------------------------------------------------------- sinh spec

    def _spec_from_llm(
        self,
        user_query: str,
        *,
        history: Optional[Sequence[dict]],
        previous_spec: Optional[dict],
    ) -> Optional[QuerySpec]:
        """Gọi LLM, thử lại đúng một lần khi output không dựng được spec."""
        try:
            spec = self._llm.generate_spec(
                user_query, history=history, previous_spec=previous_spec
            )
            if spec is not None:
                return spec
            if not self._llm.available():
                return None
            logger.info("QA: spec lượt 1 không hợp lệ, thử lại một lần")
            return self._llm.generate_spec(
                user_query,
                history=history,
                previous_spec=previous_spec,
                correction="JSON không parse được hoặc không khớp schema QuerySpec.",
            )
        except Exception:
            # GeminiSpecGenerator đã tự nuốt lỗi, nhưng generator có thể được thay
            # bằng cài đặt khác; không để lỗi provider làm hỏng cả câu trả lời.
            logger.exception("Generator spec ném lỗi; chuyển sang Rule Engine")
            return None

    # ------------------------------------------------------------- thực thi

    def _broaden_hint(self, spec: QuerySpec, session: Session) -> str:
        """
        Kết quả rỗng vì *khung thời gian*, hay vì thật sự không có dữ liệu?

        Trả lời "không có gì" khi dữ liệu chỉ nằm ngoài cửa sổ thời gian là đúng
        nhưng vô ích. Câu gợi ý này được dựng bằng một truy vấn đếm xác định, không
        gọi thêm LLM — nới bộ lọc bằng LLM có nguy cơ đổi luôn ý nghĩa câu hỏi.
        """
        if spec.time_range is TimeRange.ALL:
            return ""

        probe = compile_spec(
            spec.model_copy(update={"metric": Metric.COUNT, "time_range": TimeRange.ALL})
        )
        try:
            row = session.execute(text(probe.sql), probe.params).fetchone()
        except Exception:
            logger.exception("Không chạy được truy vấn đối chứng khoảng thời gian")
            session.rollback()
            return ""

        total = (row._mapping.get("so_su_kien") if row is not None else 0) or 0
        if not total:
            return ""
        return (
            f" Trên toàn bộ dữ liệu đã ghi nhận thì có {total} sự kiện như vậy — "
            "bạn có thể hỏi lại theo tuần hoặc tháng."
        )

    def _run(self, compiled: CompiledQuery, session: Session) -> dict:
        spec = compiled.spec
        rows = session.execute(text(compiled.sql), compiled.params).fetchall()
        answer = render_answer(spec, rows, compiled.scope)

        clips: list[dict] = []
        if rows_have_data(spec, rows):
            if spec.metric is Metric.LIST:
                clips = _collect_clips(rows)
            elif compiled.evidence_sql:
                evidence_rows = session.execute(
                    text(compiled.evidence_sql), compiled.params
                ).fetchall()
                clips = _collect_clips(evidence_rows)
        else:
            answer += self._broaden_hint(spec, session)

        return {
            "answer": answer,
            "sql_query": compiled.sql,
            "clips": clips,
            # Giữ lại trường cũ cho client chưa cập nhật; luôn là clip đầu tiên.
            "clip_url": clips[0]["url"] if clips else None,
            "spec": spec.model_dump(mode="json"),
        }

    def answer_question(
        self,
        user_query: str,
        session: Optional[Session] = None,
        *,
        history: Optional[Sequence[dict]] = None,
        previous_spec: Optional[dict] = None,
    ) -> dict:
        """
        Trả lời câu hỏi tiếng Việt bằng SQL thật chạy trên CSDL sự kiện.

        Thử nhánh LLM trước, rơi xuống Rule Engine khi nhánh LLM không dùng được.
        Trả về dict đúng `QueryResponse`: `answer`, `sql_query`, `clips`,
        `clip_url`, `spec`.
        """
        normalized = _strip_accents(user_query or "")

        # Chặn trước cả hai nhánh: câu chào hỏi không có ý định truy vấn dữ liệu,
        # nên không mở session, không sinh spec và không kèm clip bằng chứng.
        if _is_chitchat(normalized):
            logger.info("QA branch=chitchat")
            return {
                "answer": _CHITCHAT_ANSWER,
                "sql_query": None,
                "clips": [],
                "clip_url": None,
                "spec": None,
            }

        owns_session = session is None
        if owns_session:
            from backend.database.engine import SessionLocal

            session = SessionLocal()
        try:
            spec = self._spec_from_llm(
                user_query, history=history, previous_spec=previous_spec
            )
            branch = "llm"
            if spec is None:
                previous = None
                if previous_spec:
                    try:
                        previous = QuerySpec.model_validate(_coerce_spec_payload(previous_spec))
                    except Exception:
                        previous = None
                spec = rule_spec_from_question(normalized, previous_spec=previous)
                branch = "rules"

            compiled = compile_spec(spec)
            try:
                result = self._run(compiled, session)
            except Exception as exc:
                logger.exception("Thực thi truy vấn thất bại (branch=%s)", branch)
                session.rollback()
                return {
                    "answer": f"Không truy vấn được dữ liệu sự kiện: {exc}",
                    "sql_query": compiled.sql,
                    "clips": [],
                    "clip_url": None,
                    "spec": spec.model_dump(mode="json"),
                }

            logger.info(
                "QA branch=%s metric=%s scope=%s clips=%d",
                branch,
                spec.metric.value,
                compiled.scope.label,
                len(result["clips"]),
            )
            return result
        finally:
            if owns_session:
                session.close()

"""
QuerySpec — hợp đồng truy vấn có kiểu giữa LLM và CSDL sự kiện (ADR-004 rev.2).

Kiến trúc cũ để LLM sinh thẳng SQL. Cách đó buộc mô hình phải biết những thứ nó
không có cách nào biết chắc: tên cột, giá trị enum thật đang nằm trong DB, cách
join `vehicles`. Khi dữ liệu lệch (ví dụ `object_class` từng lưu tên tiếng Việt),
mô hình không báo lỗi — nó trả về 0 dòng và câu trả lời sai một cách im lặng.

Module này đảo ngược trách nhiệm:

* LLM chỉ trả về một `QuerySpec` — mô tả *ý định* bằng enum đã cố định.
* Backend biên dịch spec thành SQL tham số hóa. Backend là nơi duy nhất biết
  schema, nên schema đổi thì chỉ sửa ở đây.

Hệ quả: không còn SQL thô do mô hình sinh ra, nên cũng không cần lớp regex kiểm
duyệt câu lệnh; mọi truy vấn đều read-only theo cấu trúc.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional, Sequence

from pydantic import BaseModel, Field, model_validator

# Sự kiện được ghi theo giờ Việt Nam (xem `datetime.now(ICT_TZ)` trong
# backend/app/api/v1/events.py), nên "hôm nay" phải tính theo cùng múi giờ đó,
# không phải UTC của máy chủ.
ICT_TZ = timezone(timedelta(hours=7))

# Trần cứng cho số dòng trả về: một spec mơ hồ không được kéo cả bảng vào bộ nhớ.
MAX_LIMIT = 50

# Số clip bằng chứng tối đa đính kèm một câu trả lời.
MAX_CLIPS = 5


class Metric(str, Enum):
    """Dạng câu trả lời người dùng đang cần."""

    COUNT = "count"          # "có bao nhiêu…"
    LIST = "list"            # "liệt kê…", "cho tôi xem…"
    BREAKDOWN = "breakdown"  # "phân bố theo…", "loại nào nhiều nhất"
    TOP_PLATES = "top_plates"  # "biển số nào ra vào nhiều nhất"


class EventTypeKey(str, Enum):
    LPR_PASSAGE = "LPR_PASSAGE"
    ZONE_VIOLATION = "ZONE_VIOLATION"
    RESTRICTED_ACCESS = "RESTRICTED_ACCESS"


class ObjectClassKey(str, Enum):
    CONTAINER = "container"
    TRUCK = "truck"
    FORKLIFT = "forklift"
    CRANE = "crane"
    CAR = "car"
    MOTORBIKE = "motorbike"
    BICYCLE = "bicycle"
    PERSON = "person"


class TagLabel(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    BLACKLISTED = "blacklisted"


class TimeRange(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


class GroupBy(str, Enum):
    OBJECT_CLASS = "object_class"
    CAMERA = "camera"
    DAY = "day"
    EVENT_TYPE = "event_type"


class QuerySpec(BaseModel):
    """
    Ý định truy vấn đã được chuẩn hóa. Đây là *toàn bộ* những gì LLM được phép
    quyết định — mọi giá trị nằm ngoài enum đều bị Pydantic loại từ vòng ngoài.
    """

    metric: Metric = Metric.COUNT
    event_type: list[EventTypeKey] = Field(default_factory=list)
    object_class: list[ObjectClassKey] = Field(default_factory=list)
    tag_label: list[TagLabel] = Field(default_factory=list)
    min_severity: Optional[int] = Field(default=None, ge=1, le=3)
    license_plate: Optional[str] = None
    camera_id: Optional[str] = None
    time_range: TimeRange = TimeRange.ALL
    group_by: Optional[GroupBy] = None
    limit: int = Field(default=5, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)
    want_clips: bool = False

    @model_validator(mode="after")
    def _reconcile_metric_and_group_by(self) -> "QuerySpec":
        """
        Giữ `metric` và `group_by` nhất quán.

        LLM hay trả về `group_by` kèm `metric=count` khi người dùng hỏi "loại xe
        nào vi phạm nhiều nhất". Ý định thật là breakdown, nên nâng cấp thay vì
        lặng lẽ bỏ `group_by` đi.
        """
        if self.group_by is not None and self.metric is Metric.COUNT:
            object.__setattr__(self, "metric", Metric.BREAKDOWN)
        if self.metric is Metric.BREAKDOWN and self.group_by is None:
            object.__setattr__(self, "group_by", GroupBy.OBJECT_CLASS)
        if self.metric is Metric.LIST:
            # Liệt kê sự kiện thì bằng chứng luôn có nghĩa; đỡ phụ thuộc vào việc
            # LLM có nhớ bật cờ hay không.
            object.__setattr__(self, "want_clips", True)
        return self


# --------------------------------------------------------------------- thời gian


class TimeScope:
    """Khoảng thời gian đã giải, kèm cách diễn đạt lại cho câu trả lời."""

    __slots__ = ("label", "start", "end")

    def __init__(self, label: str, start: Optional[datetime], end: Optional[datetime]):
        self.label = label
        self.start = start
        self.end = end

    def params(self) -> dict:
        if self.start is None:
            return {}
        # SQLAlchemy lưu DateTime của SQLite dạng chuỗi naive; bỏ tzinfo để so sánh
        # cùng hệ quy chiếu với giá trị đã ghi.
        return {
            "ts_start": self.start.replace(tzinfo=None),
            "ts_end": self.end.replace(tzinfo=None),
        }


def resolve_time_scope(time_range: TimeRange, now: Optional[datetime] = None) -> TimeScope:
    current = now or datetime.now(ICT_TZ)
    midnight = current.replace(hour=0, minute=0, second=0, microsecond=0)

    if time_range is TimeRange.TODAY:
        return TimeScope("hôm nay", midnight, midnight + timedelta(days=1))
    if time_range is TimeRange.YESTERDAY:
        return TimeScope("hôm qua", midnight - timedelta(days=1), midnight)
    if time_range is TimeRange.WEEK:
        return TimeScope("7 ngày qua", midnight - timedelta(days=6), midnight + timedelta(days=1))
    if time_range is TimeRange.MONTH:
        return TimeScope("30 ngày qua", midnight - timedelta(days=29), midnight + timedelta(days=1))
    return TimeScope("toàn bộ dữ liệu đã ghi nhận", None, None)


# --------------------------------------------------------------------- biên dịch

_EVENT_TYPE_VN = {
    EventTypeKey.LPR_PASSAGE: "lượt xe qua cổng",
    EventTypeKey.ZONE_VIOLATION: "vi phạm khu vực",
    EventTypeKey.RESTRICTED_ACCESS: "xâm nhập khu vực hạn chế",
}

_TAG_LABEL_VN = {
    TagLabel.KNOWN: "xe quen",
    TagLabel.UNKNOWN: "xe lạ",
    TagLabel.BLACKLISTED: "xe trong danh sách đen",
}

_OBJECT_CLASS_VN = {
    ObjectClassKey.CONTAINER: "Container",
    ObjectClassKey.TRUCK: "Xe tải",
    ObjectClassKey.FORKLIFT: "Xe nâng",
    ObjectClassKey.CRANE: "Xe cẩu",
    ObjectClassKey.CAR: "Xe con",
    ObjectClassKey.MOTORBIKE: "Xe máy",
    ObjectClassKey.BICYCLE: "Xe đạp",
    ObjectClassKey.PERSON: "Người",
}

_SEVERITY_VN = {1: "Mức 1 (thấp)", 2: "Mức 2 (trung bình)", 3: "Mức 3 (nghiêm trọng)"}

_GROUP_BY_SQL = {
    GroupBy.OBJECT_CLASS: "e.object_class",
    GroupBy.CAMERA: "COALESCE(c.name, e.camera_id)",
    GroupBy.DAY: "date(e.timestamp)",
    GroupBy.EVENT_TYPE: "e.event_type",
}

_GROUP_BY_VN = {
    GroupBy.OBJECT_CLASS: "loại đối tượng",
    GroupBy.CAMERA: "camera",
    GroupBy.DAY: "ngày",
    GroupBy.EVENT_TYPE: "loại sự kiện",
}

_LIST_COLUMNS = """\
    e.id AS event_id,
    e.timestamp AS thoi_diem,
    e.event_type AS loai_su_kien,
    e.severity_level AS muc_do,
    e.license_plate AS bien_so,
    e.object_class AS lop_doi_tuong,
    e.video_clip_url AS clip_url,
    COALESCE(c.name, e.camera_id) AS camera,
    z.name AS khu_vuc"""


class CompiledQuery:
    """SQL đã dựng cho một `QuerySpec`, kèm truy vấn bằng chứng dùng *cùng* bộ lọc."""

    __slots__ = ("sql", "params", "evidence_sql", "scope", "spec")

    def __init__(
        self,
        *,
        sql: str,
        params: dict,
        evidence_sql: Optional[str],
        scope: TimeScope,
        spec: QuerySpec,
    ):
        self.sql = sql
        self.params = params
        self.evidence_sql = evidence_sql
        self.scope = scope
        self.spec = spec


def _build_where(spec: QuerySpec, scope: TimeScope) -> tuple[str, dict]:
    """Dựng mệnh đề WHERE dùng chung cho cả truy vấn chính lẫn truy vấn clip."""
    clauses: list[str] = ["1 = 1"]
    params: dict[str, Any] = {}

    if spec.event_type:
        keys = [f"et{i}" for i in range(len(spec.event_type))]
        clauses.append("e.event_type IN (" + ", ".join(f":{k}" for k in keys) + ")")
        params.update({k: v.value for k, v in zip(keys, spec.event_type)})

    if spec.object_class:
        keys = [f"oc{i}" for i in range(len(spec.object_class))]
        clauses.append("e.object_class IN (" + ", ".join(f":{k}" for k in keys) + ")")
        params.update({k: v.value for k, v in zip(keys, spec.object_class)})

    if spec.tag_label:
        keys = [f"tag{i}" for i in range(len(spec.tag_label))]
        clauses.append(
            "e.license_plate IN (SELECT v.license_plate FROM vehicles v WHERE v.tag_label IN ("
            + ", ".join(f":{k}" for k in keys)
            + "))"
        )
        params.update({k: v.value for k, v in zip(keys, spec.tag_label)})

    if spec.min_severity is not None:
        clauses.append("e.severity_level >= :min_severity")
        params["min_severity"] = spec.min_severity

    if spec.license_plate:
        clauses.append("e.license_plate = :license_plate")
        params["license_plate"] = spec.license_plate.strip().upper()

    if spec.camera_id:
        clauses.append("e.camera_id = :camera_id")
        params["camera_id"] = spec.camera_id

    if scope.start is not None:
        clauses.append("e.timestamp >= :ts_start AND e.timestamp < :ts_end")
        params.update(scope.params())

    return " AND ".join(clauses), params


_FROM_CLAUSE = """\
FROM events e
LEFT JOIN cameras c ON c.id = e.camera_id
LEFT JOIN zones z ON z.id = e.zone_id"""


def compile_spec(spec: QuerySpec, now: Optional[datetime] = None) -> CompiledQuery:
    """
    Biên dịch `QuerySpec` thành SQL tham số hóa.

    Truy vấn bằng chứng dùng **đúng bộ lọc** của truy vấn chính. Đó là điểm mấu
    chốt: clip đính kèm không thể lạc đề so với câu hỏi, vì cả hai đi ra từ cùng
    một mệnh đề WHERE.
    """
    scope = resolve_time_scope(spec.time_range, now=now)
    where, params = _build_where(spec, scope)

    if spec.metric is Metric.COUNT:
        sql = (
            "SELECT\n"
            "    COUNT(*) AS so_su_kien,\n"
            "    COUNT(DISTINCT e.camera_id) AS so_camera,\n"
            "    COUNT(DISTINCT e.license_plate) AS so_bien_so,\n"
            "    MAX(e.severity_level) AS muc_cao_nhat\n"
            f"{_FROM_CLAUSE}\n"
            f"WHERE {where}"
        )
    elif spec.metric is Metric.LIST:
        sql = (
            f"SELECT\n{_LIST_COLUMNS}\n"
            f"{_FROM_CLAUSE}\n"
            f"WHERE {where}\n"
            "ORDER BY e.timestamp DESC\n"
            "LIMIT :row_limit OFFSET :row_offset"
        )
        params["row_limit"] = spec.limit
        params["row_offset"] = spec.offset
    elif spec.metric is Metric.BREAKDOWN:
        group_expr = _GROUP_BY_SQL[spec.group_by or GroupBy.OBJECT_CLASS]
        sql = (
            f"SELECT\n    {group_expr} AS nhom,\n    COUNT(*) AS so_su_kien\n"
            f"{_FROM_CLAUSE}\n"
            f"WHERE {where}\n"
            "GROUP BY nhom\n"
            "ORDER BY so_su_kien DESC\n"
            "LIMIT :row_limit"
        )
        params["row_limit"] = spec.limit
    else:  # Metric.TOP_PLATES
        sql = (
            "SELECT\n"
            "    e.license_plate AS bien_so,\n"
            "    COUNT(*) AS so_luot,\n"
            "    MAX(e.timestamp) AS lan_gan_nhat\n"
            f"{_FROM_CLAUSE}\n"
            f"WHERE {where} AND e.license_plate IS NOT NULL AND e.license_plate <> ''\n"
            "GROUP BY e.license_plate\n"
            "ORDER BY so_luot DESC, bien_so ASC\n"
            "LIMIT :row_limit"
        )
        params["row_limit"] = spec.limit

    evidence_sql = None
    if spec.want_clips and spec.metric is not Metric.LIST:
        evidence_sql = (
            f"SELECT\n{_LIST_COLUMNS}\n"
            f"{_FROM_CLAUSE}\n"
            f"WHERE {where} AND e.video_clip_url IS NOT NULL AND e.video_clip_url <> ''\n"
            "ORDER BY e.timestamp DESC\n"
            "LIMIT :clip_limit"
        )
        params["clip_limit"] = MAX_CLIPS

    return CompiledQuery(sql=sql, params=params, evidence_sql=evidence_sql, scope=scope, spec=spec)


# ------------------------------------------------------------------- diễn giải


def describe_filters(spec: QuerySpec) -> str:
    """
    Dựng cụm danh từ tiếng Việt mô tả bộ lọc, ví dụ "vi phạm khu vực của Xe nâng".

    Renderer dùng cụm này thay vì đoán ngữ nghĩa từ bí danh cột như kiến trúc cũ —
    spec đã nói rõ người dùng hỏi gì, không việc gì phải suy diễn ngược.
    """
    subject = "sự kiện"
    if spec.event_type:
        subject = " và ".join(_EVENT_TYPE_VN[t] for t in spec.event_type)

    qualifiers: list[str] = []
    if spec.object_class:
        qualifiers.append("của " + ", ".join(_OBJECT_CLASS_VN[o] for o in spec.object_class))
    if spec.tag_label:
        qualifiers.append("thuộc nhóm " + ", ".join(_TAG_LABEL_VN[t] for t in spec.tag_label))
    if spec.license_plate:
        qualifiers.append(f"của biển số {spec.license_plate.strip().upper()}")
    if spec.min_severity is not None and spec.min_severity > 1:
        qualifiers.append(f"từ mức {spec.min_severity} trở lên")
    if spec.camera_id:
        qualifiers.append(f"trên camera {spec.camera_id}")

    return " ".join([subject, *qualifiers])


def _fmt_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M %d/%m")
    text = str(value or "")
    # SQLite trả DATETIME dạng chuỗi ISO; cắt phần micro giây cho gọn.
    return text[:16].replace("T", " ")


def _row_get(row: Any, key: str) -> Any:
    return row._mapping.get(key)


def class_display_name(value: Any) -> str:
    """Khoá lớp -> tên hiển thị. Giá trị lạ (dữ liệu cũ chưa chuẩn hoá) giữ nguyên."""
    if value in ObjectClassKey._value2member_map_:
        return _OBJECT_CLASS_VN[ObjectClassKey(value)]
    return str(value or "đối tượng")


def render_answer(spec: QuerySpec, rows: Sequence[Any], scope: TimeScope) -> str:
    """Dựng câu trả lời tiếng Việt từ *ý định đã biết* cộng với dữ liệu thật."""
    subject = describe_filters(spec)
    period = scope.label

    if spec.metric is Metric.COUNT:
        row = rows[0] if rows else None
        total = (_row_get(row, "so_su_kien") if row is not None else 0) or 0
        if total == 0:
            return f"Không ghi nhận {subject} nào trong {period}."

        parts = [f"Ghi nhận {total} {subject} trong {period}"]
        cameras = (_row_get(row, "so_camera") or 0) if row is not None else 0
        if cameras:
            parts.append(f"trên {cameras} camera")
        plates = (_row_get(row, "so_bien_so") or 0) if row is not None else 0
        if plates and spec.event_type == [EventTypeKey.LPR_PASSAGE]:
            parts.append(f"với {plates} biển số khác nhau")
        answer = ", ".join(parts) + "."

        max_sev = (_row_get(row, "muc_cao_nhat") or 0) if row is not None else 0
        if max_sev >= 2:
            answer += f" Mức nghiêm trọng cao nhất: {_SEVERITY_VN.get(max_sev, f'Mức {max_sev}')}."
        return answer

    if spec.metric is Metric.LIST:
        if not rows:
            return f"Không có {subject} nào trong {period}."
        lines = []
        for row in rows:
            bits = [
                _fmt_timestamp(_row_get(row, "thoi_diem")),
                class_display_name(_row_get(row, "lop_doi_tuong")),
            ]
            if _row_get(row, "bien_so"):
                bits.append(f"biển số {_row_get(row, 'bien_so')}")
            if _row_get(row, "camera"):
                bits.append(f"camera {_row_get(row, 'camera')}")
            if _row_get(row, "khu_vuc"):
                bits.append(str(_row_get(row, "khu_vuc")))
            lines.append("• " + " · ".join(bits))
        header = f"{len(rows)} {subject} gần nhất trong {period}"
        if spec.offset:
            header = f"{len(rows)} {subject} tiếp theo trong {period}"
        return header + ":\n" + "\n".join(lines)

    if spec.metric is Metric.BREAKDOWN:
        if not rows:
            return f"Không có {subject} nào trong {period} để thống kê."
        group_label = _GROUP_BY_VN[spec.group_by or GroupBy.OBJECT_CLASS]
        lines = []
        for row in rows:
            name = _row_get(row, "nhom")
            if spec.group_by is GroupBy.OBJECT_CLASS:
                name = class_display_name(name)
            elif spec.group_by is GroupBy.EVENT_TYPE and name in EventTypeKey._value2member_map_:
                name = _EVENT_TYPE_VN[EventTypeKey(name)]
            lines.append(f"• {name}: {_row_get(row, 'so_su_kien')}")
        return f"Phân bố {subject} theo {group_label} trong {period}:\n" + "\n".join(lines)

    # Metric.TOP_PLATES
    if not rows:
        return f"Chưa đọc được biển số nào trong {period}."
    listed = ", ".join(f"{_row_get(r, 'bien_so')} ({_row_get(r, 'so_luot')} lượt)" for r in rows)
    return f"Biển số xuất hiện nhiều nhất trong {period}: {listed}."


def rows_have_data(spec: QuerySpec, rows: Sequence[Any]) -> bool:
    """
    Kết quả có phản ánh sự kiện có thật không?

    `COUNT(*) = 0` về mặt kỹ thuật là "có một dòng" nhưng về mặt nghiệp vụ là
    *không có sự kiện nào* — không được đính kèm clip bằng chứng cho nó.
    """
    if not rows:
        return False
    if spec.metric is Metric.COUNT:
        return bool((_row_get(rows[0], "so_su_kien") or 0))
    return True

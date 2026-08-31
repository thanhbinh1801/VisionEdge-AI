"""
Kiểm thử Tab 4 — AI Chatbot Assistant (TASK-013, TASK-029, ADR-004 rev.2).

Trọng tâm sau khi đổi trục sang QuerySpec:

* LLM chỉ sinh `QuerySpec`; SQL do backend dựng, nên không có đường nào để câu
  lệnh ghi lọt xuống CSDL.
* Clip bằng chứng đi ra từ *đúng bộ lọc* của câu hỏi, không phải "sự kiện mới
  nhất có clip".
* Một câu trả lời có thể kèm nhiều clip, và các clip trùng URL bị khử.
* Bộ lọc lớp đối tượng so khớp theo khoá tiếng Anh đã chuẩn hoá.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.services.qa_agent import (
    ICT_TZ,
    GeminiSpecGenerator,
    LLMQAAgent,
    _is_chitchat,
    _strip_accents,
    rule_spec_from_question,
)
from backend.app.services.query_spec import (
    EventTypeKey,
    GroupBy,
    Metric,
    ObjectClassKey,
    QuerySpec,
    TagLabel,
    TimeRange,
    compile_spec,
)
from backend.database.engine import get_sqlite_engine, init_db
from backend.database.migrations import normalize_object_class
from backend.database.models import Camera, Vehicle, Zone
from backend.database.models import Event as EventModel

VIOLATION_CLIP = "/media/clips/clip_BAI-KIEM_1787716332.mp4"
VIOLATION_CLIP_2 = "/media/clips/clip_BAI-KIEM_1787716400.mp4"
GATE_CLIP = "/media/clips/clip_GATE-01_1787716999.mp4"


def _now() -> datetime:
    return datetime.now(ICT_TZ).replace(tzinfo=None)


class StubLLM:
    """Thay Gemini trong test: không có mạng, không cần khóa API."""

    def __init__(self, *specs, available=True, raises=None):
        self.model = "stub-model"
        self._specs = list(specs)
        self._available = available
        self._raises = raises
        self.calls: list[dict] = []

    def available(self) -> bool:
        return self._available

    def generate_spec(self, user_query, *, now=None, history=None, previous_spec=None, correction=None):
        self.calls.append(
            {
                "query": user_query,
                "history": history,
                "previous_spec": previous_spec,
                "correction": correction,
            }
        )
        if self._raises is not None:
            raise self._raises
        if not self._available:
            return None
        if not self._specs:
            return None
        return self._specs.pop(0)


@pytest.fixture(autouse=True)
def disable_llm_by_default(monkeypatch):
    """
    Mặc định tắt nhánh Gemini cho toàn bộ test.

    Nếu máy chạy test có `GEMINI_API_KEY` thật trong .env, các test Rule Engine sẽ
    lặng lẽ gọi mạng và mất tính tất định. Test nào cần nhánh LLM thì tự truyền
    `StubLLM` vào `LLMQAAgent`.
    """
    monkeypatch.setattr(
        "backend.app.services.qa_agent.settings.GEMINI_API_KEY", None, raising=False
    )


@pytest.fixture()
def session(tmp_path):
    """CSDL SQLite riêng cho từng test, dựng từ schema.sql thật."""
    db_path = tmp_path / "qa.db"
    engine = get_sqlite_engine(f"sqlite:///{db_path.as_posix()}")
    init_db(target_engine=engine)
    maker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = maker()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _seed(db, *, violation_clip=VIOLATION_CLIP):
    """
    Dữ liệu nền: 1 xe quen, 1 xe lạ, 2 vi phạm zone mức 3, 2 lượt LPR.

    Lượt LPR mới nhất *có clip và mới hơn* mọi vi phạm. Đó là bẫy cố ý: kiến trúc
    cũ gắn clip bằng "sự kiện mới nhất có clip" nên sẽ trả clip cổng cho câu hỏi
    về vi phạm khu vực.
    """
    now = _now()
    # schema.sql đã seed sẵn camera/zone/event mẫu; dọn sạch để phép đếm trong test
    # chỉ phản ánh đúng các bản ghi bên dưới.
    db.query(EventModel).delete()
    db.query(Zone).delete()
    db.query(Vehicle).delete()
    db.commit()

    db.merge(Camera(id="GATE-01", name="Cổng vào", location="Cổng chính", stream_url="/videos/GATE-01.mp4"))
    db.merge(Camera(id="BAI-KIEM", name="Bãi kiểm", location="Bãi kiểm hóa", stream_url="/videos/BAI-KIEM.mp4"))
    db.add(
        Zone(
            id="zone-1",
            camera_id="BAI-KIEM",
            name="Khu vực cấm",
            vertices=[[0, 0], [100, 0], [100, 100]],
            allowed_classes=[],
            forbidden_classes=["person", "forklift"],
        )
    )
    db.add(Vehicle(id="veh-1", license_plate="51A-123.45", tag_label="known"))
    db.add(Vehicle(id="veh-2", license_plate="29B-999.99", tag_label="unknown"))
    db.flush()

    db.add(
        EventModel(
            id="evt-lpr-known",
            timestamp=now - timedelta(minutes=30),
            camera_id="GATE-01",
            event_type="LPR_PASSAGE",
            severity_level=1,
            license_plate="51A-123.45",
            object_class="truck",
            confidence=0.91,
        )
    )
    db.add(
        EventModel(
            id="evt-violation-old",
            timestamp=now - timedelta(minutes=20),
            camera_id="BAI-KIEM",
            zone_id="zone-1",
            event_type="ZONE_VIOLATION",
            severity_level=3,
            object_class="person",
            confidence=0.71,
            video_clip_url=VIOLATION_CLIP_2 if violation_clip else None,
        )
    )
    db.add(
        EventModel(
            id="evt-violation",
            timestamp=now - timedelta(minutes=10),
            camera_id="BAI-KIEM",
            zone_id="zone-1",
            event_type="ZONE_VIOLATION",
            severity_level=3,
            object_class="forklift",
            confidence=0.77,
            video_clip_url=violation_clip,
        )
    )
    # Mới nhất, có clip, nhưng KHÔNG phải vi phạm.
    db.add(
        EventModel(
            id="evt-lpr-unknown",
            timestamp=now - timedelta(minutes=1),
            camera_id="GATE-01",
            event_type="LPR_PASSAGE",
            severity_level=2,
            license_plate="29B-999.99",
            object_class="car",
            confidence=0.88,
            video_clip_url=GATE_CLIP,
        )
    )
    db.commit()


# ------------------------------------------------- CR-005: chuẩn hoá object_class


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Xe nâng", "forklift"),
        ("xe nang", "forklift"),
        ("Xe tải", "truck"),
        ("Người", "person"),
        ("Container", "container"),
        ("Xe con", "car"),
        ("Xe máy", "motorbike"),
        # Dữ liệu bẩn: pipeline cũ ghi kèm mã phương tiện.
        ("Xe nâng FL-01", "forklift"),
        ("Xe container 15R-158.45", "container"),
        ("Xe hơi trắng", "car"),
        # Đã là khoá chuẩn thì giữ nguyên.
        ("forklift", "forklift"),
        ("person", "person"),
    ],
)
def test_object_class_is_normalized_to_canonical_key(raw, expected):
    assert normalize_object_class(raw) == expected


def test_unrecognized_object_class_is_left_alone():
    """Không nhận ra thì trả None để caller giữ nguyên, không đoán bừa."""
    assert normalize_object_class("máy bay trực thăng") is None
    assert normalize_object_class("") is None
    assert normalize_object_class(None) is None


def test_xe_container_is_not_swallowed_by_xe_con():
    """Regression: so khớp chuỗi con phải ưu tiên tên dài nhất."""
    assert normalize_object_class("Xe container") == "container"


# ------------------------------------------------------------------- QuerySpec


def test_group_by_upgrades_count_to_breakdown():
    """LLM hay trả group_by kèm metric=count; ý định thật là breakdown."""
    spec = QuerySpec(metric=Metric.COUNT, group_by=GroupBy.CAMERA)

    assert spec.metric is Metric.BREAKDOWN
    assert spec.group_by is GroupBy.CAMERA


def test_breakdown_without_group_by_defaults_to_object_class():
    assert QuerySpec(metric=Metric.BREAKDOWN).group_by is GroupBy.OBJECT_CLASS


def test_list_metric_always_wants_clips():
    assert QuerySpec(metric=Metric.LIST).want_clips is True


def test_limit_is_capped():
    with pytest.raises(ValueError):
        QuerySpec(metric=Metric.LIST, limit=5000)


def test_invalid_enum_value_is_rejected():
    with pytest.raises(ValueError):
        QuerySpec(metric=Metric.COUNT, object_class=["may_bay"])


# -------------------------------------------------------------------- compiler


def test_compiled_sql_is_always_a_select():
    for metric in Metric:
        compiled = compile_spec(QuerySpec(metric=metric, want_clips=True))
        assert compiled.sql.strip().upper().startswith("SELECT")


def test_filter_values_are_bound_parameters_not_inlined():
    """Giá trị bộ lọc phải đi qua tham số — đó là lý do không cần lọc SQL injection."""
    compiled = compile_spec(
        QuerySpec(metric=Metric.COUNT, object_class=[ObjectClassKey.FORKLIFT])
    )

    assert "forklift" not in compiled.sql
    assert "forklift" in compiled.params.values()


def test_evidence_query_reuses_the_same_where_clause(session):
    """Clip và số liệu phải đi ra từ cùng một mệnh đề WHERE."""
    compiled = compile_spec(
        QuerySpec(
            metric=Metric.COUNT,
            event_type=[EventTypeKey.ZONE_VIOLATION],
            want_clips=True,
        )
    )

    assert compiled.evidence_sql is not None
    assert "e.event_type IN (:et0)" in compiled.sql
    assert "e.event_type IN (:et0)" in compiled.evidence_sql


# ------------------------------------------------------------ Rule Engine specs


def test_rule_spec_for_unknown_vehicle_question():
    spec = rule_spec_from_question(_strip_accents("Hôm nay có bao nhiêu xe lạ vào?"))

    assert spec.tag_label == [TagLabel.UNKNOWN]
    assert spec.time_range is TimeRange.TODAY
    assert spec.metric is Metric.COUNT


def test_rule_spec_for_violation_question_covers_both_event_types():
    spec = rule_spec_from_question(_strip_accents("Có vi phạm khu vực cấm nào không?"))

    assert spec.event_type == [EventTypeKey.ZONE_VIOLATION, EventTypeKey.RESTRICTED_ACCESS]
    assert spec.want_clips is True


def test_rule_spec_extracts_requested_clip_count():
    """Regression: "đưa tôi 2 clip" phải thành list limit=2, không phải count."""
    spec = rule_spec_from_question(_strip_accents("Đưa tôi 2 clip vi phạm"))

    assert spec.metric is Metric.LIST
    assert spec.limit == 2


def test_rule_spec_maps_vietnamese_object_name_to_english_key():
    spec = rule_spec_from_question(_strip_accents("Xe nâng hoạt động thế nào tuần này?"))

    assert spec.object_class == [ObjectClassKey.FORKLIFT]
    assert spec.time_range is TimeRange.WEEK


def test_rule_spec_does_not_confuse_unknown_vehicle_with_object_class():
    """"xe lạ" là nhãn đăng ký, không phải một lớp thị giác."""
    spec = rule_spec_from_question(_strip_accents("có bao nhiêu xe lạ"))

    assert spec.object_class == []
    assert spec.tag_label == [TagLabel.UNKNOWN]


def test_rule_spec_follow_up_advances_offset():
    previous = QuerySpec(metric=Metric.LIST, limit=2, offset=0)

    spec = rule_spec_from_question(_strip_accents("còn nữa không?"), previous_spec=previous)

    assert spec.offset == 2
    assert spec.limit == 2


# ---------------------------------------------------------------- end-to-end


def test_answer_reflects_seeded_rows_and_is_not_hardcoded(session):
    """Regression BUG-001: trước đây mọi câu hỏi đều trả 'đã ghi nhận 15 sự kiện'."""
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có tất cả bao nhiêu sự kiện?", session=session)

    assert "15" not in res["answer"]
    assert "4 sự kiện" in res["answer"]
    assert "2 camera" in res["answer"]


def test_count_tracks_database_state(session):
    _seed(session)
    agent = LLMQAAgent()
    before = agent.answer_question("Hôm nay có bao nhiêu sự kiện?", session=session)

    session.add(
        EventModel(
            id="evt-extra",
            timestamp=_now() - timedelta(minutes=5),
            camera_id="GATE-01",
            event_type="LPR_PASSAGE",
            severity_level=1,
            license_plate="51A-123.45",
            object_class="car",
            confidence=0.8,
        )
    )
    session.commit()

    after = agent.answer_question("Hôm nay có bao nhiêu sự kiện?", session=session)
    assert "4 sự kiện" in before["answer"]
    assert "5 sự kiện" in after["answer"]


def test_different_questions_produce_different_sql_and_answers(session):
    _seed(session)
    agent = LLMQAAgent()

    a = agent.answer_question("Hôm nay có bao nhiêu xe lạ vào?", session=session)
    b = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert a["answer"] != b["answer"]
    assert a["sql_query"] != b["sql_query"]


def test_unknown_vehicle_question_counts_only_unknown_tag(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có bao nhiêu xe lạ vào?", session=session)

    assert "1 lượt xe qua cổng" in res["answer"]
    assert "xe lạ" in res["answer"]


def test_violation_question_reports_severity(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "2 vi phạm khu vực" in res["answer"]
    assert "Mức 3" in res["answer"]


def test_object_class_question_matches_normalized_key(session):
    """
    Regression: câu hỏi "xe nâng" phải tìm ra sự kiện lưu dưới khoá 'forklift'.

    Trước CR-005, cột lưu tên tiếng Việt còn bộ lọc dùng khoá tiếng Anh, nên câu
    hỏi này luôn trả về 0 dù dữ liệu có sẵn.
    """
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Xe nâng hoạt động thế nào hôm nay?", session=session)

    assert "Xe nâng" in res["answer"]
    assert "1 sự kiện" in res["answer"]


def test_question_without_accents_still_matches(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("hom nay co bao nhieu xe la vao", session=session)

    assert "xe lạ" in res["answer"]
    assert "1 lượt xe qua cổng" in res["answer"]


def test_empty_database_reports_no_data_instead_of_fake_count(session):
    session.query(EventModel).delete()
    session.commit()
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có bao nhiêu sự kiện?", session=session)

    assert "Không ghi nhận" in res["answer"]
    assert "15" not in res["answer"]


def test_time_scope_excludes_older_events(session):
    _seed(session)
    session.add(
        EventModel(
            id="evt-old",
            timestamp=_now() - timedelta(days=3),
            camera_id="GATE-01",
            event_type="LPR_PASSAGE",
            severity_level=1,
            license_plate="51A-123.45",
            object_class="car",
            confidence=0.8,
        )
    )
    session.commit()
    agent = LLMQAAgent()

    today = agent.answer_question("Hôm nay có bao nhiêu sự kiện?", session=session)
    all_time = agent.answer_question("Tổng cộng có bao nhiêu sự kiện?", session=session)

    assert "4 sự kiện" in today["answer"]
    assert "5 sự kiện" in all_time["answer"]


def test_breakdown_lists_groups_with_vietnamese_labels(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Loại xe nào vi phạm nhiều nhất?", session=session)

    assert "Xe nâng: 1" in res["answer"]
    assert "Người: 1" in res["answer"]


def test_top_plates_lists_plates_by_frequency(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Biển số nào ra vào nhiều nhất?", session=session)

    assert "51A-123.45" in res["answer"]
    assert "29B-999.99" in res["answer"]


def test_executed_sql_is_read_only(session):
    _seed(session)
    agent = LLMQAAgent()

    for question in ("Có bao nhiêu xe lạ?", "Có vi phạm nào không?", "Xe nâng thế nào?"):
        sql = agent.answer_question(question, session=session)["sql_query"]
        assert sql.strip().upper().startswith("SELECT")


# ------------------------------------------------------------- clip evidence


def test_violation_answer_returns_real_clip_url_from_db(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert res["clip_url"] == VIOLATION_CLIP


def test_clip_never_comes_from_an_unrelated_event_type(session):
    """
    Regression cốt lõi của ADR-004 rev.2.

    `evt-lpr-unknown` mới hơn mọi vi phạm và có clip. Kiến trúc cũ gắn "clip của
    sự kiện mới nhất" nên trả clip cổng cho câu hỏi về vi phạm khu vực.
    """
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    urls = [c["url"] for c in res["clips"]]
    assert GATE_CLIP not in urls
    assert set(urls) == {VIOLATION_CLIP, VIOLATION_CLIP_2}


def test_list_question_returns_multiple_distinct_clips(session):
    """Regression: "đưa tôi 2 clip" từng trả về đúng một trình phát."""
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Đưa tôi 2 clip vi phạm", session=session)

    assert len(res["clips"]) == 2
    assert len({c["url"] for c in res["clips"]}) == 2


def test_duplicate_clip_urls_are_collapsed(session):
    """
    Nhiều sự kiện trỏ về cùng một file video nguồn — chỉ hiện một trình phát.

    Đây đúng là hiện tượng người dùng báo: hai dòng kết quả cùng
    "/videos/BAI_KIEM.mp4".
    """
    _seed(session, violation_clip=VIOLATION_CLIP)
    session.query(EventModel).filter(EventModel.id == "evt-violation-old").update(
        {"video_clip_url": VIOLATION_CLIP}
    )
    session.commit()
    agent = LLMQAAgent()

    res = agent.answer_question("Đưa tôi 5 clip vi phạm", session=session)

    assert [c["url"] for c in res["clips"]] == [VIOLATION_CLIP]


def test_clips_carry_event_identity_for_verification(session):
    _seed(session)
    agent = LLMQAAgent()

    clip = agent.answer_question("Đưa tôi 1 clip vi phạm", session=session)["clips"][0]

    assert clip["event_id"] == "evt-violation"
    assert "Xe nâng" in clip["label"]
    assert clip["timestamp"]


def test_clip_list_is_empty_when_no_evidence_exists(session):
    """Regression BUG-001: trước đây luôn trả /media/clips/sample_evidence.mp4."""
    _seed(session, violation_clip=None)
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert res["clips"] == []
    assert res["clip_url"] is None
    assert "sample_evidence" not in str(res)


def test_no_clip_attached_when_nothing_matches(session):
    _seed(session)
    session.query(EventModel).delete()
    session.commit()
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "Không ghi nhận" in res["answer"]
    assert res["clips"] == []


def test_media_clips_mount_serves_file_instead_of_404(tmp_path):
    """Regression BUG-001: /media chưa từng được mount nên mọi clip đều 404."""
    from fastapi.staticfiles import StaticFiles

    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    (clips_dir / "clip_demo.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    app = FastAPI()
    app.mount("/media/clips", StaticFiles(directory=str(clips_dir)), name="media-clips")
    client = TestClient(app)

    res = client.get("/media/clips/clip_demo.mp4")

    assert res.status_code == 200
    assert res.content.startswith(b"\x00\x00\x00\x18ftyp")


def test_real_app_mounts_media_clips_route():
    """Ứng dụng thật phải khai báo route /media/clips."""
    from backend.main import app

    mounted = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/media/clips" in mounted
    assert "/media/crops" in mounted


# ------------------------------------------------------- gợi ý nới khung thời gian


def test_empty_today_result_points_at_data_outside_the_window(session):
    """
    Trả lời "không có gì" khi dữ liệu chỉ nằm ngoài cửa sổ thời gian là đúng nhưng
    vô ích — phải nói cho người trực biết dữ liệu nằm ở đâu.
    """
    _seed(session)
    session.query(EventModel).update({"timestamp": _now() - timedelta(days=10)})
    session.commit()
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có bao nhiêu vi phạm?", session=session)

    assert "Không ghi nhận" in res["answer"]
    assert "toàn bộ dữ liệu đã ghi nhận thì có 2 sự kiện" in res["answer"]


def test_no_broaden_hint_when_there_is_genuinely_no_data(session):
    """Không có dữ liệu ở đâu cả thì đừng gợi ý hỏi lại — sẽ thành dắt mũi."""
    session.query(EventModel).delete()
    session.commit()
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có bao nhiêu vi phạm?", session=session)

    assert "bạn có thể hỏi lại" not in res["answer"]


# ----------------------------------------------------------------- API contract


def test_assistant_endpoint_returns_query_response_schema(session, monkeypatch):
    _seed(session)

    from backend.app.api.v1 import assistant as assistant_module

    # Endpoint dùng session mặc định của tiến trình; ép nó dùng session test.
    monkeypatch.setattr(
        assistant_module.agent,
        "answer_question",
        lambda q, **kw: LLMQAAgent().answer_question(q, session=session, **kw),
    )

    app = FastAPI()
    app.include_router(assistant_module.router, prefix="/api/v1/assistant")
    client = TestClient(app)

    res = client.post("/api/v1/assistant/query", json={"query": "Có vi phạm nào không?"})

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"answer", "sql_query", "clips", "clip_url", "spec"}
    assert "2 vi phạm khu vực" in body["answer"]
    assert body["clip_url"] == VIOLATION_CLIP
    assert len(body["clips"]) == 2
    assert body["spec"]["metric"] == "count"


def test_assistant_endpoint_forwards_history_and_previous_spec(session, monkeypatch):
    """P3: ngữ cảnh hội thoại phải đi tới được agent, không bị endpoint nuốt."""
    from backend.app.api.v1 import assistant as assistant_module

    captured = {}

    def _fake(query, **kwargs):
        captured.update({"query": query, **kwargs})
        return {"answer": "ok", "sql_query": None, "clips": [], "clip_url": None, "spec": None}

    monkeypatch.setattr(assistant_module.agent, "answer_question", _fake)

    app = FastAPI()
    app.include_router(assistant_module.router, prefix="/api/v1/assistant")
    client = TestClient(app)

    client.post(
        "/api/v1/assistant/query",
        json={
            "query": "còn nữa không",
            "history": [{"role": "user", "text": "đưa tôi 2 clip vi phạm"}],
            "previous_spec": {"metric": "list", "limit": 2},
        },
    )

    assert captured["history"] == [{"role": "user", "text": "đưa tôi 2 clip vi phạm"}]
    assert captured["previous_spec"] == {"metric": "list", "limit": 2}


# ------------------------------------------------------- nhánh LLM (TASK-029)


def test_llm_spec_takes_priority_over_rule_engine(session):
    _seed(session)
    agent = LLMQAAgent(
        llm=StubLLM(QuerySpec(metric=Metric.COUNT, object_class=[ObjectClassKey.CAR]))
    )

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    # Rule Engine cho câu này sẽ trả "2 vi phạm khu vực"; nhánh LLM phải thắng.
    assert "Xe con" in res["answer"]
    assert "vi phạm khu vực" not in res["answer"]


def test_llm_branch_receives_history_and_previous_spec(session):
    _seed(session)
    llm = StubLLM(QuerySpec(metric=Metric.COUNT))
    agent = LLMQAAgent(llm=llm)

    agent.answer_question(
        "còn nữa không",
        session=session,
        history=[{"role": "user", "text": "đưa tôi 2 clip vi phạm"}],
        previous_spec={"metric": "list", "limit": 2},
    )

    assert llm.calls[0]["history"] == [{"role": "user", "text": "đưa tôi 2 clip vi phạm"}]
    assert llm.calls[0]["previous_spec"] == {"metric": "list", "limit": 2}


def test_llm_is_retried_once_when_first_spec_is_unusable(session):
    """P4: một lượt sửa sai trước khi bỏ cuộc."""
    _seed(session)
    llm = StubLLM(None, QuerySpec(metric=Metric.COUNT, object_class=[ObjectClassKey.FORKLIFT]))
    agent = LLMQAAgent(llm=llm)

    res = agent.answer_question("Xe nâng thế nào?", session=session)

    assert len(llm.calls) == 2
    assert llm.calls[1]["correction"] is not None
    assert "Xe nâng" in res["answer"]


def test_falls_back_to_rules_when_no_api_key(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM(QuerySpec(metric=Metric.COUNT), available=False))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "2 vi phạm khu vực" in res["answer"]


def test_no_retry_when_llm_is_unavailable(session):
    """Không có khóa API thì đừng tốn lượt gọi thứ hai."""
    _seed(session)
    llm = StubLLM(available=False)
    agent = LLMQAAgent(llm=llm)

    agent.answer_question("Có vi phạm nào không?", session=session)

    assert len(llm.calls) == 1


def test_falls_back_to_rules_when_generator_raises(session):
    """Generator ném lỗi cũng không được làm hỏng câu trả lời."""
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM(raises=RuntimeError("quota exceeded")))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "2 vi phạm khu vực" in res["answer"]
    assert "quota exceeded" not in res["answer"], "lỗi hạ tầng không được lộ ra người dùng"


def test_falls_back_to_rules_when_generator_returns_nothing(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM(None, None))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "2 vi phạm khu vực" in res["answer"]


def test_rule_fallback_still_understands_follow_up_from_previous_spec(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM(available=False))

    res = agent.answer_question(
        "còn nữa không?",
        session=session,
        previous_spec={
            "metric": "list",
            "event_type": ["ZONE_VIOLATION", "RESTRICTED_ACCESS"],
            "limit": 1,
            "offset": 0,
        },
    )

    assert res["spec"]["offset"] == 1
    assert res["clips"][0]["event_id"] == "evt-violation-old"


# --------------------------------------------------------- parse spec từ LLM


@pytest.mark.parametrize("raw", [None, "", "   ", "khong phai json", "{", "[]"])
def test_parse_spec_rejects_unusable_output(raw):
    assert GeminiSpecGenerator.parse_spec(raw) is None


def test_parse_spec_strips_markdown_fence():
    spec = GeminiSpecGenerator.parse_spec('```json\n{"metric":"count"}\n```')

    assert spec is not None
    assert spec.metric is Metric.COUNT


def test_parse_spec_drops_hallucinated_enum_values_but_keeps_valid_ones():
    """Một giá trị bịa không được làm hỏng cả spec."""
    spec = GeminiSpecGenerator.parse_spec(
        '{"metric":"count","object_class":["forklift","may_bay"],"time_range":"week"}'
    )

    assert spec.object_class == [ObjectClassKey.FORKLIFT]
    assert spec.time_range is TimeRange.WEEK


def test_parse_spec_normalizes_case_of_enum_values():
    spec = GeminiSpecGenerator.parse_spec(
        '{"metric":"COUNT","event_type":["zone_violation"],"time_range":"TODAY"}'
    )

    assert spec.metric is Metric.COUNT
    assert spec.event_type == [EventTypeKey.ZONE_VIOLATION]
    assert spec.time_range is TimeRange.TODAY


def test_parse_spec_clamps_oversized_limit():
    spec = GeminiSpecGenerator.parse_spec('{"metric":"list","limit":9999}')

    assert spec.limit == 50


def test_parse_spec_ignores_sql_injection_attempts_entirely():
    """
    Không còn đường nào để câu lệnh ghi đi vào CSDL.

    Spec không có trường nào nhận SQL, nên chuỗi độc chỉ có thể nằm trong
    `license_plate` — và giá trị đó luôn đi qua tham số bound.
    """
    spec = GeminiSpecGenerator.parse_spec(
        '{"metric":"count","license_plate":"x\'; DROP TABLE events; --"}'
    )

    compiled = compile_spec(spec)
    assert "DROP" not in compiled.sql.upper()
    assert compiled.params["license_plate"] == "X'; DROP TABLE EVENTS; --"


def test_write_statement_from_llm_cannot_reach_the_database(session):
    """Dù model có cố trả về SQL, spec không có chỗ nào chứa được nó."""
    _seed(session)
    spec = GeminiSpecGenerator.parse_spec('{"metric":"count","camera_id":"DELETE FROM events"}')
    agent = LLMQAAgent(llm=StubLLM(spec))

    agent.answer_question("Xoá hết sự kiện đi", session=session)

    assert session.query(EventModel).count() == 4, "dữ liệu không được phép bị xoá"


def test_generator_is_unavailable_without_key():
    assert GeminiSpecGenerator(api_key=None).available() is False
    assert GeminiSpecGenerator(api_key="   ").available() is False
    assert GeminiSpecGenerator(api_key="abc").available() is True


def test_generator_returns_none_without_key_and_never_calls_network():
    assert GeminiSpecGenerator(api_key="").generate_spec("Có bao nhiêu xe lạ?") is None


def test_generator_swallows_client_errors(monkeypatch):
    """Lỗi từ SDK phải quy về None để agent fallback, không được ném lên trên."""
    gen = GeminiSpecGenerator(api_key="fake-key", model="stub")
    monkeypatch.setattr(
        gen, "_get_client", lambda: (_ for _ in ()).throw(RuntimeError("network down"))
    )

    assert gen.generate_spec("Có bao nhiêu xe lạ?") is None


def test_prompt_teaches_event_type_mapping_and_carries_context():
    gen = GeminiSpecGenerator(api_key="fake-key", model="stub")

    prompt = gen._build_prompt(
        "còn nữa không",
        now=datetime(2026, 8, 27, 17, 0, tzinfo=ICT_TZ),
        history=[{"role": "user", "text": "đưa tôi 2 clip vi phạm"}],
        previous_spec={"metric": "list", "limit": 2},
    )

    assert "ZONE_VIOLATION" in prompt
    assert "forklift=Xe nâng" in prompt
    assert "đưa tôi 2 clip vi phạm" in prompt
    assert '"metric": "list"' in prompt or '"metric":"list"' in prompt
    assert "2026-08-27 17:00" in prompt


# ------------------------------------------------------------- chitchat / greeting


@pytest.mark.parametrize(
    "question",
    [
        "hi",
        "Hi!",
        "hello",
        "Hello ban",
        "Xin chào",
        "xin chao",
        "Chào bạn",
        "Bạn là ai?",
        "bạn làm được gì?",
        "trợ giúp",
        "help",
        "hướng dẫn",
        "Cảm ơn",
        "",
    ],
)
def test_chitchat_is_detected(question):
    assert _is_chitchat(_strip_accents(question)) is True


@pytest.mark.parametrize(
    "question",
    [
        "Hôm nay có bao nhiêu sự kiện?",
        "Có vi phạm khu vực cấm nào không?",
        "Hôm nay có bao nhiêu xe lạ vào?",
        "Xe nâng hoạt động thế nào hôm nay?",
        "Biển số nào ra vào nhiều nhất?",
        "hom nay co bao nhieu xe la vao",
        "Đưa tôi 2 clip vi phạm",
    ],
)
def test_real_questions_are_not_treated_as_chitchat(question):
    assert _is_chitchat(_strip_accents(question)) is False


@pytest.mark.parametrize("greeting", ["hi", "Xin chào", "hello", "Bạn là ai?", "trợ giúp"])
def test_greeting_returns_friendly_answer_without_sql_or_clip(session, greeting):
    """Regression TASK-029/BUG-001: 'hi' từng trả 'Kết quả: 839.' kèm clip 10s."""
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question(greeting, session=session)

    assert res["sql_query"] is None
    assert res["clips"] == []
    assert "Kết quả: " not in res["answer"]
    assert "839" not in res["answer"]
    assert "Trợ lý AI giám sát an ninh" in res["answer"]
    assert "vi phạm khu vực cấm" in res["answer"]


def test_greeting_never_reaches_the_llm_branch(session):
    """Câu chào không được phép tiêu tốn một lượt gọi Gemini."""
    _seed(session)
    llm = StubLLM(QuerySpec(metric=Metric.COUNT))
    agent = LLMQAAgent(llm=llm)

    res = agent.answer_question("hi", session=session)

    assert llm.calls == []
    assert res["sql_query"] is None
    assert res["clips"] == []


def test_greeting_works_without_any_session():
    """Chitchat không được chạm CSDL, nên không cần session nào cả."""
    agent = LLMQAAgent()

    res = agent.answer_question("xin chào")

    assert res["sql_query"] is None
    assert res["clips"] == []
    assert res["spec"] is None
    assert "Xin chào" in res["answer"]

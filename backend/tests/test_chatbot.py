"""
Kiểm thử Tab 4 — AI Chatbot Assistant (TASK-013, BUG-001).

Trọng tâm: câu trả lời phải sinh ra từ SQL chạy thật trên CSDL, không phải chuỗi
viết cứng; và clip bằng chứng phải phục vụ được qua HTTP thay vì trả 404.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.services.qa_agent import (
    ICT_TZ,
    GeminiSqlGenerator,
    LLMQAAgent,
    _is_chitchat,
    _render_llm_rows,
    _sanitize_llm_sql,
    _strip_accents,
)
from backend.database.engine import get_sqlite_engine, init_db
from backend.database.models import Camera, Vehicle, Zone
from backend.database.models import Event as EventModel


def _now() -> datetime:
    return datetime.now(ICT_TZ).replace(tzinfo=None)


class StubLLM:
    """Thay Gemini trong test: không có mạng, không cần khóa API."""

    def __init__(self, sql=None, *, available=True, raises=None):
        self.model = "stub-model"
        self._sql = sql
        self._available = available
        self._raises = raises
        self.calls = []

    def available(self) -> bool:
        return self._available

    def generate_sql(self, user_query, now=None):
        self.calls.append(user_query)
        if self._raises is not None:
            raise self._raises
        if not self._available:
            return None
        return self._sql


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


def _seed(db, *, clip_url="/media/clips/clip_GATE-01_1787716332.mp4"):
    """Dữ liệu nền: 1 xe quen, 1 xe lạ, 1 vi phạm zone mức 3, 1 lượt LPR."""
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
            id="evt-lpr-unknown",
            timestamp=now - timedelta(minutes=20),
            camera_id="GATE-01",
            event_type="LPR_PASSAGE",
            severity_level=2,
            license_plate="29B-999.99",
            object_class="car",
            confidence=0.88,
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
            video_clip_url=clip_url,
        )
    )
    db.commit()


# --------------------------------------------------------------------- Text-to-SQL


def test_answer_is_not_hardcoded_and_reflects_seeded_rows(session):
    """Regression BUG-001: trước đây mọi câu hỏi đều trả 'đã ghi nhận 15 sự kiện'."""
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có tất cả bao nhiêu sự kiện?", session=session)

    assert "15" not in res["answer"], "câu trả lời vẫn là hằng số viết cứng cũ"
    assert "3 sự kiện" in res["answer"]
    assert "2 camera" in res["answer"]


def test_count_tracks_database_state(session):
    """Thêm một bản ghi thì con số trong câu trả lời phải đổi theo."""
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
    assert "3 sự kiện" in before["answer"]
    assert "4 sự kiện" in after["answer"]


def test_different_questions_produce_different_sql_and_answers(session):
    """Regression BUG-001: hai câu hỏi khác nhau từng trả về response giống hệt."""
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

    assert "1 xe lạ" in res["answer"]
    assert "vehicles" in res["sql_query"]
    assert "unknown" not in res["answer"]


def test_known_vehicle_question_uses_known_tag(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có bao nhiêu xe quen vào?", session=session)

    assert "1 xe quen" in res["answer"]


def test_violation_question_reports_severity(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "1 vi phạm khu vực" in res["answer"]
    assert "Mức 3" in res["answer"]
    assert "ZONE_VIOLATION" in res["sql_query"]


def test_object_class_question_matches_vietnamese_name(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Xe nâng hoạt động thế nào hôm nay?", session=session)

    assert "Xe nâng" in res["answer"]
    assert "1 sự kiện" in res["answer"]


def test_question_without_accents_still_matches(session):
    """Người dùng gõ không dấu vẫn phải rơi đúng intent."""
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("hom nay co bao nhieu xe la vao", session=session)

    assert "1 xe lạ" in res["answer"]


def test_empty_database_reports_no_data_instead_of_fake_count(session):
    session.query(EventModel).delete()
    session.commit()
    agent = LLMQAAgent()

    res = agent.answer_question("Hôm nay có bao nhiêu sự kiện?", session=session)

    assert "Chưa có sự kiện nào" in res["answer"]
    assert "15" not in res["answer"]


def test_time_scope_excludes_older_events(session):
    """Sự kiện của hôm qua không được tính vào câu hỏi 'hôm nay'."""
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

    assert "3 sự kiện" in today["answer"]
    assert "4 sự kiện" in all_time["answer"]


def test_executed_sql_is_read_only(session):
    _seed(session)
    agent = LLMQAAgent()

    for question in ("Có bao nhiêu xe lạ?", "Có vi phạm nào không?", "Xe nâng thế nào?"):
        sql = agent.answer_question(question, session=session)["sql_query"]
        assert sql.strip().upper().startswith("SELECT")


# ------------------------------------------------------------------- clip evidence


def test_violation_answer_returns_real_clip_url_from_db(session):
    _seed(session)
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert res["clip_url"] == "/media/clips/clip_GATE-01_1787716332.mp4"


def test_clip_url_is_null_when_no_evidence_exists(session):
    """Regression BUG-001: trước đây luôn trả /media/clips/sample_evidence.mp4."""
    _seed(session, clip_url=None)
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert res["clip_url"] is None
    assert "sample_evidence" not in str(res)


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


# ----------------------------------------------------------------- API contract


def test_assistant_endpoint_returns_query_response_schema(session, monkeypatch):
    _seed(session)

    from backend.app.api.v1 import assistant as assistant_module

    # Endpoint dùng session mặc định của tiến trình; ép nó dùng session test.
    monkeypatch.setattr(
        assistant_module.agent,
        "answer_question",
        lambda q: LLMQAAgent().answer_question(q, session=session),
    )

    app = FastAPI()
    app.include_router(assistant_module.router, prefix="/api/v1/assistant")
    client = TestClient(app)

    res = client.post("/api/v1/assistant/query", json={"query": "Có vi phạm nào không?"})

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"answer", "sql_query", "clip_url"}
    assert "1 vi phạm khu vực" in body["answer"]
    assert body["clip_url"] == "/media/clips/clip_GATE-01_1787716332.mp4"


# ------------------------------------------------------- Gemini LLM branch (TASK-029)


def test_llm_branch_executes_generated_sql_against_real_db(session):
    """SQL do Gemini sinh ra phải được chạy thật, không chỉ đính kèm response."""
    _seed(session)
    llm = StubLLM("SELECT COUNT(*) AS tong FROM events LIMIT 10")
    agent = LLMQAAgent(llm=llm)

    res = agent.answer_question("Có bao nhiêu sự kiện tất cả?", session=session)

    assert llm.calls == ["Có bao nhiêu sự kiện tất cả?"]
    assert res["sql_query"] == "SELECT COUNT(*) AS tong FROM events LIMIT 10"
    assert "3" in res["answer"]


def test_llm_branch_takes_priority_over_rule_engine(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM("SELECT 42 AS con_so LIMIT 1"))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    # Rule Engine cho câu này sẽ trả "1 vi phạm khu vực"; nhánh LLM phải thắng.
    assert "42" in res["answer"]
    assert "vi phạm khu vực" not in res["answer"]


def test_falls_back_to_rules_when_no_api_key(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM("SELECT 42 AS x LIMIT 1", available=False))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "1 vi phạm khu vực" in res["answer"]
    assert "ZONE_VIOLATION" in res["sql_query"]


def test_falls_back_to_rules_when_generator_raises(session):
    """Generator ném lỗi cũng không được làm hỏng câu trả lời."""
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM(raises=RuntimeError("quota exceeded")))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "1 vi phạm khu vực" in res["answer"]
    assert "quota exceeded" not in res["answer"], "lỗi hạ tầng không được lộ ra người dùng"


def test_falls_back_to_rules_when_generator_returns_none(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM(None))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "1 vi phạm khu vực" in res["answer"]


def test_falls_back_to_rules_when_generated_sql_is_invalid(session):
    """SQL sai cột vẫn phải cho câu trả lời, không được ném lỗi ra người dùng."""
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM("SELECT cot_khong_ton_tai FROM events LIMIT 1"))

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "1 vi phạm khu vực" in res["answer"]
    assert "ZONE_VIOLATION" in res["sql_query"]


def test_falls_back_to_rules_when_llm_returns_write_statement(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM("DELETE FROM events"))

    res = agent.answer_question("Xoá hết sự kiện đi", session=session)

    assert res["sql_query"].strip().upper().startswith("SELECT")
    assert session.query(EventModel).count() == 3, "dữ liệu không được phép bị xoá"


def test_llm_branch_still_returns_real_clip_url(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM("SELECT COUNT(*) AS tong FROM events LIMIT 5"))

    res = agent.answer_question("Tổng cộng bao nhiêu sự kiện?", session=session)

    assert res["clip_url"] == "/media/clips/clip_GATE-01_1787716332.mp4"


# --------------------------------------------------------- SQL sanitizer (TASK-029)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "DELETE FROM events",
        "DROP TABLE events",
        "UPDATE events SET severity_level = 1",
        "SELECT 1; DROP TABLE events",
        "PRAGMA table_info(events)",
        "Xin lỗi, tôi không thể tạo SQL cho câu hỏi này.",
    ],
)
def test_sanitizer_rejects_unsafe_or_non_select(raw):
    assert _sanitize_llm_sql(raw) is None


def test_sanitizer_strips_markdown_fence():
    cleaned = _sanitize_llm_sql("```sql\nSELECT COUNT(*) FROM events LIMIT 5\n```")

    assert cleaned == "SELECT COUNT(*) FROM events LIMIT 5"


def test_sanitizer_appends_limit_when_model_forgets():
    cleaned = _sanitize_llm_sql("SELECT id FROM events")

    assert "LIMIT 50" in cleaned


def test_sanitizer_keeps_existing_limit():
    cleaned = _sanitize_llm_sql("SELECT id FROM events LIMIT 7")

    assert cleaned.count("LIMIT") == 1
    assert cleaned.endswith("LIMIT 7")


def test_sanitizer_drops_trailing_semicolon():
    assert _sanitize_llm_sql("SELECT 1 AS x LIMIT 1;") == "SELECT 1 AS x LIMIT 1"


# ---------------------------------------------------------- generator guardrails


def test_generator_is_unavailable_without_key():
    assert GeminiSqlGenerator(api_key=None).available() is False
    assert GeminiSqlGenerator(api_key="   ").available() is False
    assert GeminiSqlGenerator(api_key="abc").available() is True


def test_generator_returns_none_without_key_and_never_calls_network():
    assert GeminiSqlGenerator(api_key="").generate_sql("Có bao nhiêu xe lạ?") is None


def test_generator_swallows_client_errors(monkeypatch):
    """Lỗi từ SDK phải quy về None để agent fallback, không được ném lên trên."""
    gen = GeminiSqlGenerator(api_key="fake-key", model="stub")
    monkeypatch.setattr(
        gen, "_get_client", lambda: (_ for _ in ()).throw(RuntimeError("network down"))
    )

    assert gen.generate_sql("Có bao nhiêu xe lạ?") is None


def test_generator_sanitizes_model_output(monkeypatch):
    class FakeModels:
        def generate_content(self, model, contents):
            assert "SentriAI" in contents
            assert "Có bao nhiêu xe lạ?" in contents
            return type("R", (), {"text": "```sql\nSELECT COUNT(*) FROM vehicles\n```"})()

    gen = GeminiSqlGenerator(api_key="fake-key", model="stub")
    monkeypatch.setattr(gen, "_get_client", lambda: type("C", (), {"models": FakeModels()})())

    assert gen.generate_sql("Có bao nhiêu xe lạ?") == "SELECT COUNT(*) FROM vehicles\nLIMIT 50"


# ------------------------------------------------------------- answer rendering


def test_render_rows_handles_empty_result():
    assert "Không có dữ liệu" in _render_llm_rows([])


class _FakeRow:
    """Giả lập Row của SQLAlchemy: `_render_llm_rows` chỉ cần `._mapping`."""

    def __init__(self, mapping):
        self._mapping = mapping


def test_render_single_count_is_a_full_vietnamese_sentence():
    """Regression TASK-029/BUG-001: kết quả COUNT từng bị in cụt thành 'Kết quả: 839.'."""
    answer = _render_llm_rows([_FakeRow({"tong": 839})])

    assert answer.startswith("Ghi nhận 839 sự kiện")
    assert not answer.startswith("Kết quả:")


def test_render_zero_count_says_no_events_instead_of_printing_zero():
    answer = _render_llm_rows([_FakeRow({"tong": 0})])

    assert "Không có sự kiện nào" in answer
    assert "Kết quả: 0" not in answer


def test_render_multi_row_result_lists_items_readably():
    answer = _render_llm_rows(
        [_FakeRow({"plate": "51A-123.45", "total": 3}), _FakeRow({"plate": "29B-999.99", "total": 1})]
    )

    assert "Tôi tìm thấy 2 kết quả" in answer
    assert "51A-123.45" in answer
    assert "29B-999.99" in answer


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
    assert res["clip_url"] is None
    assert "Kết quả: " not in res["answer"]
    assert "839" not in res["answer"]
    assert "Trợ lý AI giám sát an ninh" in res["answer"]
    assert "vi phạm khu vực cấm" in res["answer"]


def test_greeting_never_reaches_the_llm_branch(session):
    """Câu chào không được phép tiêu tốn một lượt gọi Gemini."""
    _seed(session)
    llm = StubLLM("SELECT COUNT(*) AS tong FROM events LIMIT 1")
    agent = LLMQAAgent(llm=llm)

    res = agent.answer_question("hi", session=session)

    assert llm.calls == []
    assert res["sql_query"] is None
    assert res["clip_url"] is None


def test_greeting_works_without_any_session():
    """Chitchat không được chạm CSDL, nên không cần session nào cả."""
    agent = LLMQAAgent()

    res = agent.answer_question("xin chào")

    assert res == {
        "answer": res["answer"],
        "sql_query": None,
        "clip_url": None,
    }
    assert "Xin chào" in res["answer"]


# --------------------------------------------------- clip evidence gating (TASK-029/BUG-001)


def test_llm_branch_omits_clip_when_count_is_zero(session):
    """Không có sự kiện thì không được đính kèm clip 'bằng chứng' của sự kiện khác."""
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM("SELECT COUNT(*) AS tong FROM events WHERE id = 'khong-ton-tai' LIMIT 1"))

    res = agent.answer_question("Có vi phạm mức 3 nào không?", session=session)

    assert "Không có sự kiện nào" in res["answer"]
    assert res["clip_url"] is None


def test_llm_branch_omits_clip_when_result_set_is_empty(session):
    _seed(session)
    agent = LLMQAAgent(llm=StubLLM("SELECT id FROM events WHERE id = 'khong-ton-tai' LIMIT 5"))

    res = agent.answer_question("Liệt kê sự kiện của camera không tồn tại", session=session)

    assert "Không có dữ liệu" in res["answer"]
    assert res["clip_url"] is None


def test_rule_branch_omits_clip_when_nothing_matches(session):
    """Rule Engine cũng phải tuân cùng quy tắc gắn clip."""
    _seed(session)
    session.query(EventModel).delete()
    session.commit()
    agent = LLMQAAgent()

    res = agent.answer_question("Có vi phạm khu vực cấm nào không?", session=session)

    assert "Không có vi phạm khu vực nào" in res["answer"]
    assert res["clip_url"] is None


# ------------------------------------------------------------------- LLM prompting


def test_llm_prompt_teaches_zone_violation_filter(monkeypatch):
    """Prompt phải dạy Gemini lọc đúng event_type thay vì đếm cả bảng events."""
    captured = {}

    class FakeModels:
        def generate_content(self, model, contents):
            captured["contents"] = contents
            return type("R", (), {"text": "SELECT 1 AS x LIMIT 1"})()

    gen = GeminiSqlGenerator(api_key="fake-key", model="stub")
    monkeypatch.setattr(gen, "_get_client", lambda: type("C", (), {"models": FakeModels()})())
    gen.generate_sql("Có vi phạm khu vực cấm nào không?")

    prompt = captured["contents"]
    assert "'ZONE_VIOLATION', 'RESTRICTED_ACCESS'" in prompt
    assert "giám sát an ninh cổng" in prompt
    assert "đều phải có WHERE" in prompt

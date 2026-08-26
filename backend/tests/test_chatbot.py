import os
from datetime import datetime, timedelta

import pytest

from backend.app.services.qa_agent import (
    LLMQAAgent,
    ReadOnlyViolation,
    RuleBasedTranslator,
    SQLPlan,
    assert_read_only,
)
from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.database.models import Camera, Event

TEST_DB_URL = "sqlite:///./test_chatbot.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path="docs/contracts/db/schema.sql", target_engine=engine)
    yield engine
    engine.dispose()
    if os.path.exists("test_chatbot.db"):
        try:
            os.remove("test_chatbot.db")
        except PermissionError:
            pass


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    session.add(Camera(id="CAM-QA", name="QA Cam", location="Bãi", stream_url="url"))
    now = datetime.utcnow()
    session.add_all([
        Event(
            id="evt-qa-1",
            timestamp=now - timedelta(minutes=5),
            camera_id="CAM-QA",
            event_type="ZONE_VIOLATION",
            severity_level=3,
            object_class="Xe máy",
            confidence=0.96,
            video_clip_url="/media/clips/evt-qa-1.mp4",
        ),
        Event(
            id="evt-qa-2",
            timestamp=now - timedelta(minutes=30),
            camera_id="CAM-QA",
            event_type="ZONE_VIOLATION",
            severity_level=1,
            object_class="Container",
            confidence=0.98,
            video_clip_url="/media/clips/evt-qa-2.mp4",
        ),
    ])
    session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# --- Ranh giới chỉ đọc ------------------------------------------------------
#
# Trợ lý dựng SQL rồi chạy thẳng trên CSDL sản xuất. Bộ test này khoá lại ranh
# giới đó, vì một translator LLM cắm vào sau sẽ đi qua đúng hàm này.

@pytest.mark.parametrize("sql", [
    "DELETE FROM events",
    "UPDATE events SET severity_level = 1",
    "DROP TABLE events",
    "SELECT * FROM events; DROP TABLE events",
    "PRAGMA table_info(events)",
])
def test_assert_read_only_rejects_write_statements(sql):
    with pytest.raises(ReadOnlyViolation):
        assert_read_only(sql)


def test_assert_read_only_rejects_other_tables():
    """Trợ lý chỉ được đọc `events`, không được chạm vào vehicles hay zones."""
    with pytest.raises(ReadOnlyViolation):
        assert_read_only("SELECT * FROM vehicles")


def test_assert_read_only_accepts_plain_select():
    assert_read_only("SELECT id FROM events WHERE severity_level = :s")


def test_user_text_never_reaches_sql():
    """Câu hỏi chứa cú pháp SQL vẫn chỉ thành giá trị bind, không thành câu lệnh."""
    plan = RuleBasedTranslator().translate("có bao nhiêu xe máy'; DROP TABLE events;--")
    assert plan is not None
    assert "DROP" not in plan.sql.upper()
    assert_read_only(plan.sql)


# --- Dịch câu hỏi -----------------------------------------------------------

def test_count_question_becomes_count_query():
    plan = RuleBasedTranslator().translate("Hôm nay có bao nhiêu vi phạm?")
    assert plan is not None
    assert plan.intent == "count"
    assert plan.params["severity_level"] == 3
    assert "since" in plan.params


def test_object_and_camera_filters_are_extracted():
    plan = RuleBasedTranslator().translate("Có xe máy nào vào bãi kiểm không?")
    assert plan is not None
    assert plan.params["object_class"] == "%Xe máy%"
    assert plan.params["camera_id"] == "BAI-KIEM"


def test_license_plate_is_extracted():
    plan = RuleBasedTranslator().translate("Xe 15R-158.45 vào lúc nào?")
    assert plan is not None
    assert plan.params["license_plate"] == "15R-158.45"


def test_unmatched_question_returns_none_instead_of_guessing():
    """
    Không khớp luật nào thì trả None để tầng trên fallback.

    Trả về một truy vấn "toàn bộ sự kiện" sẽ nguy hiểm hơn: câu trả lời trông như
    đã hiểu đúng câu hỏi trong khi thực ra chưa hiểu gì.
    """
    assert RuleBasedTranslator().translate("thời tiết hôm nay thế nào") is None


# --- Trả lời từ dữ liệu thật ------------------------------------------------

def test_answer_counts_real_rows_not_canned_text(db_session):
    """Nhánh cũ trả cứng 'đã ghi nhận 15 sự kiện' bất kể CSDL có gì."""
    res = LLMQAAgent().answer_question("Có bao nhiêu vi phạm?", db=db_session)

    assert "1" in res["answer"]
    assert "15" not in res["answer"]
    assert res["sql_query"].lower().startswith("select count(*)")


def test_answer_attaches_event_id_and_clip_as_evidence(db_session):
    res = LLMQAAgent().answer_question("Có bao nhiêu vi phạm?", db=db_session)

    assert res["event_id"] == "evt-qa-1"
    assert res["clip_url"] == "/media/clips/evt-qa-1.mp4"


def test_list_question_returns_newest_event_first(db_session):
    res = LLMQAAgent().answer_question("Xe máy nào vừa vào khu vực cấm?", db=db_session)

    assert res["event_id"] == "evt-qa-1"
    assert "Xe máy" in res["answer"]


def test_no_match_returns_null_evidence_not_a_fake_clip(db_session):
    """Không có sự kiện khớp thì không được bịa ra clip chứng cứ."""
    res = LLMQAAgent().answer_question("Có bao nhiêu xe đạp vi phạm?", db=db_session)

    assert res["event_id"] is None
    assert res["clip_url"] is None


def test_fallback_when_question_cannot_be_translated(db_session):
    res = LLMQAAgent().answer_question("kể chuyện cười đi", db=db_session)

    assert res["sql_query"] is None
    assert res["event_id"] is None
    assert "chưa hiểu" in res["answer"].lower()


def test_agent_without_db_returns_fallback_not_crash():
    res = LLMQAAgent().answer_question("Có bao nhiêu vi phạm?", db=None)

    assert res["event_id"] is None
    assert res["answer"] == LLMQAAgent.NO_DB_ANSWER


def test_custom_translator_seam_is_used():
    """Chỗ cắm cho tầng LLM của ADR-004: translator thay được mà không đụng agent."""

    class StubTranslator:
        def translate(self, question):
            return SQLPlan(sql="SELECT COUNT(*) AS total FROM events", intent="count")

    agent = LLMQAAgent(translator=StubTranslator())
    assert isinstance(agent.translator, StubTranslator)

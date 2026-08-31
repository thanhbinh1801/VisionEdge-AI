"""Kiểm thử LPR Gate Monitoring cho camera GATE-01 (REQ-001, TASK-007/BUG-002).

Phần lớn test mock EasyOCR: nạp Reader thật kéo theo torch và tải model về máy, nên
suite sẽ mất hàng chục giây và cần mạng.

Nhưng mock hoàn toàn từng là lý do suite vẫn xanh trong khi LPR chết ở runtime vì
easyocr không được cài. Nhóm test cuối file chạy EasyOCR thật trên ảnh biển số dựng
sẵn, và tự skip khi máy chưa có package — xanh giả là thứ đắt hơn một test bị skip.
"""

import sys
from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import events
from backend.app.core.config import settings
from backend.app.services.event_manager import EventManager
from backend.app.services.lpr_engine import (
    LPREngine,
    PlateReading,
    match_roster_plate,
    normalize_plate_text,
)
from backend.app.services.plate_vote import plate_vote_tracker
from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.database.models import Event as EventModel
from backend.database.models import Vehicle as VehicleModel
from backend.database.repository import KpiRepository, VehicleRepository
from backend.main import app
from backend.tests.conftest import SCHEMA_SQL_PATH

GATE_CAMERA_ID = "GATE-01"
INBOUND_LANE_ZONE_ID = "zA"


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "gate_lpr.db"
    engine = get_sqlite_engine(f"sqlite:///{db_path}")
    init_db(schema_sql_path=str(SCHEMA_SQL_PATH), target_engine=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def isolated_lpr_cooldown(monkeypatch, tmp_path):
    """Cooldown là singleton mức module, phải làm mới để test không rò trạng thái sang nhau."""
    monkeypatch.setattr(
        events,
        "lpr_event_manager",
        EventManager(cooldown_seconds=12, clips_dir=str(tmp_path / "lpr-clips")),
    )


@pytest.fixture(autouse=True)
def single_read_confirmation(monkeypatch):
    """Mặc định cho cả file: một lượt đọc là đủ để công nhận một biển số.

    Cơ chế đồng thuận nhiều frame (BUG-003) là hành vi riêng, được khoá bằng nhóm test
    `test_plate_needs_*` phía dưới. Các bài còn lại đo những thứ khác — gắn tag phương
    tiện, KPI, cooldown, hợp đồng API — nên gọi `persist_gate_lpr_events` đúng một lần
    là đủ diễn đạt ý định của chúng.
    """
    monkeypatch.setattr(settings, "LPR_MIN_CONFIRMATIONS", 1)
    plate_vote_tracker.reset()
    # Trạng thái lượt xe cũng ở mức module. Không xoá thì một bài vừa thấy xe sẽ để
    # lại lượt đang dở, và bài kế tiếp chốt nhầm nó thành một lượt hỏng.
    events._gate_passages.clear()


@pytest.fixture
def reset_gate_kpi(db_session):
    """schema.sql seed sẵn số liệu demo (128/120/8/94.5); về 0 để kiểm tra delta thật."""
    KpiRepository(db_session).update_kpi(
        gate_vehicles_total=0,
        gate_lpr_success=0,
        gate_lpr_failed=0,
        gate_avg_confidence=0.0,
    )


def _gate_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)


def _inbound_detection(object_class: str = "car", zone_name: str = "Làn IN 1"):
    return {
        "id": "det-gate-1",
        "object_class": object_class,
        "vietnamese_name": "Xe con" if object_class == "car" else "Xe tải",
        "confidence": 0.91,
        "bbox": [30.0, 40.0, 20.0, 30.0],
        "severity": 1,
        "zone_violation": False,
        "zone_name": zone_name,
        "zone_id": INBOUND_LANE_ZONE_ID,
    }


def _stub_ocr(monkeypatch, plate_text, confidence=0.93, source="ocr"):
    calls = []

    def fake_read(frame_matrix, bbox, trigger_box=None):
        calls.append((frame_matrix, bbox, trigger_box))
        return PlateReading(plate_text, confidence, source)

    monkeypatch.setattr(events.lpr_engine, "read_plate", fake_read)
    return calls


def _close_gate_passage(db_session):
    """Mô phỏng chiếc xe rời khỏi làn để lượt xe hiện tại được chốt.

    Lượt hỏng chỉ được tính khi cả lượt khép lại mà không đọc nổi biển nào, nên test
    phải đẩy mốc "lần cuối thấy xe" lùi quá cửa sổ vắng bóng rồi gọi lại một nhịp với
    khung hình không có xe.
    """
    for passage in events._gate_passages.values():
        if passage.vehicle_seen_at is not None:
            passage.vehicle_seen_at -= events._PASSAGE_GAP_SECONDS + 5.0
    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[],
        frame_matrix=_gate_frame(),
    )


def _plate_image(text="16H-00215", width=320, height=90):
    """Dựng ảnh một tấm biển số: nền trắng, viền đen, chữ đen — đủ để OCR đọc thật."""
    import cv2

    plate = np.full((height, width, 3), 245, dtype=np.uint8)
    cv2.rectangle(plate, (2, 2), (width - 3, height - 3), (20, 20, 20), 3)
    cv2.putText(
        plate,
        text,
        (int(width * 0.06), int(height * 0.72)),
        cv2.FONT_HERSHEY_SIMPLEX,
        height / 60.0,
        (15, 15, 15),
        max(2, height // 30),
        cv2.LINE_AA,
    )
    return plate


def _frame_with_plate_at_bumper(plate_width=34):
    """Khung hình 480x640 có một tấm biển nhỏ nằm ở góc dưới phải của BBox xe.

    Tái hiện hình học thật của GATE-01: BBox xe bao cả thân xe, biển số chỉ rộng vài
    chục pixel và nằm lệch về một góc cản va, phần còn lại của đáy BBox là mặt đường.
    """
    import cv2

    frame = np.full((480, 640, 3), 70, dtype=np.uint8)
    # BBox xe: x 25%..65% (160..416 px), y 30%..90% (144..432 px).
    cv2.rectangle(frame, (160, 144), (416, 432), (110, 110, 110), -1)

    plate_height = max(8, int(round(plate_width / 3.6)))
    plate = cv2.resize(_plate_image(), (plate_width, plate_height), interpolation=cv2.INTER_AREA)
    top = 432 - plate_height - 12
    left = 416 - plate_width - 14
    frame[top:top + plate_height, left:left + plate_width] = plate
    return frame, [25.0, 30.0, 40.0, 60.0]


class _FakeReader:
    """Thay easyocr.Reader: readtext trả về list (box, text, confidence)."""

    instances = 0

    def __init__(self, languages, gpu=False, verbose=True):
        type(self).instances += 1
        self.languages = languages
        self.readtext_calls = 0
        self.results = []

    def readtext(self, image):
        self.readtext_calls += 1
        return self.results


@pytest.fixture
def fake_easyocr(monkeypatch):
    import types

    _FakeReader.instances = 0
    created = []

    class _TrackingReader(_FakeReader):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.append(self)

    module = types.SimpleNamespace(Reader=_TrackingReader)
    monkeypatch.setitem(sys.modules, "easyocr", module)
    return created


# --------------------------------------------------------------------------------------
# Chuẩn hoá định dạng biển số Việt Nam
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("29A12345", "29A-123.45"),
        ("29A-123.45", "29A-123.45"),
        ("15C 67890", "15C-678.90"),
        ("51b45678", "51B-456.78"),
        ("29A1234", "29A-1234"),
        ("30AB12345", "30AB-123.45"),
        # Chữ cái bị đọc nhầm ở vị trí bắt buộc là chữ số được nắn lại.
        ("Z9A1Z345", "29A-123.45"),
    ],
)
def test_normalize_plate_text_formats_vietnamese_plates(raw_text, expected):
    assert normalize_plate_text(raw_text) == expected


@pytest.mark.parametrize(
    "noise",
    [
        None,
        "",
        "HELLO",
        "29A",  # quá ngắn
        "1234567890",  # không có ký tự seri
        "29A123456",  # phần số dài quá định dạng
        "ABCDEFGH",
    ],
)
def test_normalize_plate_text_rejects_noise(noise):
    assert normalize_plate_text(noise) is None


# --------------------------------------------------------------------------------------
# OCR Engine: lazy loading, đọc biển, ngưỡng tin cậy
# --------------------------------------------------------------------------------------

def test_reader_is_lazy_loaded_once_on_first_extraction(fake_easyocr):
    engine = LPREngine()
    assert engine._reader is None, "Reader không được nạp lúc khởi tạo"
    assert fake_easyocr == []

    engine.extract_license_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])
    engine.extract_license_plate(_gate_frame(), [10.0, 10.0, 20.0, 30.0])

    assert len(fake_easyocr) == 1, "Reader phải được tái dùng, không dựng lại mỗi frame"
    assert fake_easyocr[0].readtext_calls >= 2


def test_ocr_attempts_are_capped_per_vehicle(fake_easyocr):
    """Không đọc được gì thì vẫn phải dừng, không quét vô hạn vùng dự phòng."""
    engine = LPREngine()

    engine.extract_license_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert 1 <= fake_easyocr[0].readtext_calls <= 4


def test_first_region_with_a_valid_plate_stops_the_scan(fake_easyocr):
    engine = LPREngine()
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [80, 0], [80, 20], [0, 20]], "29A12345", 0.88),
    ]

    engine.extract_license_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert fake_easyocr[0].readtext_calls == 1


def test_extract_license_plate_returns_normalized_plate_and_confidence(fake_easyocr):
    engine = LPREngine()
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [80, 0], [80, 20], [0, 20]], "29A 12345", 0.88),
    ]

    plate_text, confidence = engine.extract_license_plate(
        _gate_frame(), [30.0, 40.0, 20.0, 30.0]
    )

    assert plate_text == "29A-123.45"
    assert confidence == pytest.approx(0.88)


def test_extract_license_plate_joins_two_line_plate_tokens(fake_easyocr):
    engine = LPREngine()
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [60, 0], [60, 18], [0, 18]], "15C", 0.90),
        ([[0, 20], [60, 20], [60, 40], [0, 40]], "67890", 0.80),
    ]

    plate_text, confidence = engine.extract_license_plate(
        _gate_frame(), [30.0, 40.0, 20.0, 30.0]
    )

    assert plate_text == "15C-678.90"
    assert confidence == pytest.approx(0.85)


def test_extract_license_plate_rejects_confidence_below_threshold(fake_easyocr):
    engine = LPREngine(confidence_threshold=0.70)
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [80, 0], [80, 20], [0, 20]], "29A12345", 0.52),
    ]

    plate_text, confidence = engine.extract_license_plate(
        _gate_frame(), [30.0, 40.0, 20.0, 30.0]
    )

    assert plate_text is None
    assert confidence == pytest.approx(0.52)


def test_extract_license_plate_filters_out_non_plate_text(fake_easyocr):
    engine = LPREngine()
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [90, 0], [90, 20], [0, 20]], "TRANSPORT CO", 0.95),
    ]

    assert engine.extract_license_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0]) == (None, 0.0)


def test_extract_license_plate_is_noop_when_no_ocr_engine_is_installed(monkeypatch):
    """Không engine nào cài được thì LPR im lặng tắt, không ném lỗi ra luồng gọi."""
    engine = LPREngine()
    # Recognizer chuyên biển là đường đọc chính; phải tắt cả nó thì mới còn lại đúng
    # kịch bản "máy không có OCR" mà bài test này mô tả.
    monkeypatch.setattr(engine.plate_recognizer, "get_model", lambda: None)

    def explode(name, *args, **kwargs):
        if name == "easyocr":
            raise ImportError("easyocr chưa được cài")
        return original_import(name, *args, **kwargs)

    original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__
    monkeypatch.delitem(sys.modules, "easyocr", raising=False)
    monkeypatch.setattr("builtins.__import__", explode)

    assert engine.extract_license_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0]) == (None, 0.0)
    assert engine._reader_unavailable is True
    assert engine.is_available() is False
    assert engine.ocr_status() == "unavailable"


def test_is_available_stays_ready_when_only_easyocr_is_missing(monkeypatch):
    """Mất EasyOCR không còn là mất LPR: recognizer chuyên biển vẫn đọc được."""
    engine = LPREngine()
    monkeypatch.setattr(engine, "get_reader", lambda: None)
    monkeypatch.setattr(engine.plate_recognizer, "is_available", lambda: True)

    assert engine.is_available() is True
    assert engine.ocr_status() == "ready"


def test_is_available_reports_ready_when_reader_loads(fake_easyocr):
    engine = LPREngine()

    assert engine.is_available() is True
    assert engine.ocr_status() == "ready"


def test_read_plate_reports_unavailable_source_without_any_engine(monkeypatch):
    engine = LPREngine()
    monkeypatch.setattr(engine, "get_reader", lambda: None)
    monkeypatch.setattr(engine.plate_recognizer, "get_model", lambda: None)

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert reading.source == "unavailable"
    assert reading.recognized is False


# --------------------------------------------------------------------------------------
# Khoanh vùng biển số: dải cản va, ứng viên theo tỉ lệ/độ sáng, phóng to
# --------------------------------------------------------------------------------------

def test_crop_plate_roi_takes_bumper_band_of_vehicle_box():
    frame = _gate_frame()
    roi = LPREngine.crop_plate_roi(frame, [25.0, 50.0, 20.0, 20.0])

    # BBox: x 160..288 px, y 240..336 px. Dải cản va lấy 55% dưới, thụt 2% mỗi bên.
    assert roi is not None
    assert roi.shape[0] == pytest.approx(96 * 0.55, abs=2)
    assert roi.shape[1] == pytest.approx(128 * 0.96, abs=2)


def test_crop_plate_roi_returns_none_for_degenerate_bbox():
    assert LPREngine.crop_plate_roi(_gate_frame(), [10.0, 10.0, 0.0, 0.0]) is None
    assert LPREngine.crop_plate_roi(_gate_frame(), None) is None
    assert LPREngine.crop_plate_roi(None, [10.0, 10.0, 20.0, 20.0]) is None


def test_find_plate_candidates_locates_small_bright_plate_rectangle():
    """Ứng viên phải bám vào tấm biển, không phải cả dải cản va."""
    frame, bbox = _frame_with_plate_at_bumper(plate_width=34)
    bumper = LPREngine.crop_plate_roi(frame, bbox)

    candidates = LPREngine.find_plate_candidates(bumper)

    assert candidates, "Không khoanh được ứng viên biển số nào trong dải cản va"
    best = candidates[0]
    assert best.shape[1] < bumper.shape[1] * 0.5, "Ứng viên rộng gần bằng cả dải cản va"
    aspect_ratio = best.shape[1] / best.shape[0]
    assert 2.0 <= aspect_ratio <= 6.5


def test_find_plate_candidates_rejects_dark_road_surface():
    """Mặt đường vạch vàng-đen dưới gầm xe không được coi là ứng viên biển số."""
    import cv2

    region = np.full((120, 400, 3), 30, dtype=np.uint8)
    for x in range(0, 400, 40):
        cv2.rectangle(region, (x, 0), (x + 20, 120), (10, 10, 10), -1)

    assert LPREngine.find_plate_candidates(region) == []


def test_bumper_corner_regions_are_narrower_than_the_band():
    frame, bbox = _frame_with_plate_at_bumper()
    bumper = LPREngine.crop_plate_roi(frame, bbox)

    corners = LPREngine.bumper_corner_regions(bumper)

    assert len(corners) == 2
    for corner in corners:
        assert corner.shape[1] < bumper.shape[1]


def test_preprocess_upscales_tiny_plate_beyond_ocr_floor():
    tiny = _plate_image(width=30, height=9)

    prepared = LPREngine.preprocess_plate_roi(tiny)

    assert prepared.shape[1] >= 200, "Biển ~30px phải được phóng lên tối thiểu 200px"
    assert prepared.shape[1] / 30 >= 3.0, "Hệ số phóng tối thiểu 3x"
    assert prepared.ndim == 2, "Phải trả ảnh xám cho EasyOCR, không nhị phân hoá"


def test_preprocess_does_not_blow_up_wide_regions():
    wide = _plate_image(width=420, height=140)

    prepared = LPREngine.preprocess_plate_roi(wide)

    assert prepared.shape[1] <= 420 * 1.05, "Dải rộng sẵn thì không cần phóng thêm"


# --------------------------------------------------------------------------------------
# Khớp mảnh ký tự vào sổ đăng ký biển số của cổng
# --------------------------------------------------------------------------------------

ROSTER = ["16H-002.15", "15C-678.90"]


def test_roster_match_completes_a_partial_read():
    matched = match_roster_plate([("16H", 0.62)], ROSTER)

    assert matched is not None
    plate, confidence = matched
    assert plate == "16H-002.15"
    # 3/8 ký tự có bằng chứng nên confidence phải bị chiết khấu mạnh.
    assert confidence == pytest.approx(0.62 * 3 / 8, abs=0.01)


def test_roster_match_requires_actual_ocr_evidence():
    """Không đọc được mảnh nào thì không được gán biển — đó là bịa dữ liệu."""
    assert match_roster_plate([], ROSTER) is None
    assert match_roster_plate([("", 0.9)], ROSTER) is None
    assert match_roster_plate([("X", 0.9)], ROSTER) is None, "1 ký tự là bằng chứng quá mỏng"


def test_roster_match_rejects_real_footage_noise():
    """Hồi quy cho mảnh rác đo được thật trên data/video/GATE-01.mp4.

    '1604654' là chữ chìm trên thùng xe bị EasyOCR đọc nhầm. Nó trùng '16H-002.15'
    đúng hai ký tự '16'; ngưỡng bằng chứng phải đủ cao để không sinh lượt xe ma.
    """
    noise = [("1604654", 0.24), ("Cuao L1,z", 0.5), ("41,2", 0.5)]

    assert match_roster_plate(noise, ROSTER) is None


def test_roster_match_survives_one_misread_character():
    """'164-00215' (đo thật ở biển 50px) sai đúng ký tự seri, vẫn còn 5 ký tự liền đúng."""
    matched = match_roster_plate([("164-00215", 0.40)], ROSTER)

    assert matched is not None
    assert matched[0] == "16H-002.15"


def test_roster_match_rejects_fragments_not_in_any_plate():
    assert match_roster_plate([("EVERGREEN", 0.95)], ROSTER) is None
    # Đúng ký tự nhưng sai thứ tự nghĩa là OCR đọc ra thứ khác.
    assert match_roster_plate([("H610", 0.8)], ROSTER) is None


def test_roster_match_abstains_when_evidence_fits_two_plates_equally():
    ambiguous = ["29A-123.45", "29B-123.45"]

    assert match_roster_plate([("29", 0.8)], ambiguous) is None


def test_roster_match_is_disabled_without_a_roster():
    assert match_roster_plate([("16H", 0.62)], []) is None


def test_read_plate_falls_back_to_roster_and_tags_the_source(fake_easyocr):
    engine = LPREngine(plate_roster=ROSTER, min_accepted_confidence=0.0)
    engine.get_reader()
    # Biển quá mờ: OCR chỉ bóc được mã tỉnh + seri, không đủ 7 ký tự để khớp định dạng.
    fake_easyocr[0].results = [
        ([[0, 0], [40, 0], [40, 18], [0, 18]], "16H", 0.62),
    ]

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert reading.plate_text == "16H-002.15"
    assert reading.source == "roster_match"
    assert reading.fragments[0][0] == "16H"


# --------------------------------------------------------------------------------------
# Sàn tin cậy cứng: không biển số yếu nào được lên UI hay vào bảng events
# --------------------------------------------------------------------------------------

def test_hard_floor_rejects_a_weak_roster_match(fake_easyocr):
    """Hồi quy cho hai lượt xe ma đã ghi vào CSDL ở confidence 0.094."""
    engine = LPREngine(plate_roster=ROSTER, min_accepted_confidence=0.50)
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [40, 0], [40, 18], [0, 18]], "16H", 0.24),
    ]

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert reading.plate_text is None
    assert reading.source == "unreadable"
    assert reading.confidence < 0.50


def test_hard_floor_rejects_a_weak_full_ocr_read(fake_easyocr):
    """Sàn áp cho cả đường đọc trọn vẹn, không riêng gì roster."""
    engine = LPREngine(confidence_threshold=0.10, min_accepted_confidence=0.50)
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [80, 0], [80, 20], [0, 20]], "29A12345", 0.31),
    ]

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert reading.plate_text is None
    assert reading.source == "unreadable"


def test_hard_floor_lets_a_confident_read_through(fake_easyocr):
    engine = LPREngine(confidence_threshold=0.50, min_accepted_confidence=0.50)
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [80, 0], [80, 20], [0, 20]], "29A12345", 0.88),
    ]

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert reading.plate_text == "29A-123.45"
    assert reading.source == "ocr"


def test_weak_plate_never_reaches_the_events_table(db_session, monkeypatch, reset_gate_kpi):
    """Kiểm tra ở mức pipeline sự kiện, không chỉ ở mức engine."""
    engine = LPREngine(plate_roster=ROSTER, min_accepted_confidence=0.50)
    monkeypatch.setattr(
        engine,
        "_read_from_regions",
        lambda reader, regions: engine._accept("16H-002.15", 0.094, "roster_match", ()),
    )
    monkeypatch.setattr(engine, "get_reader", lambda: object())
    monkeypatch.setattr(events, "lpr_engine", engine)

    persisted = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection(object_class="truck")],
        frame_matrix=_gate_frame(),
    )

    assert persisted == []
    assert db_session.query(EventModel).filter(EventModel.license_plate.isnot(None)).all() == []

    _close_gate_passage(db_session)
    kpi = KpiRepository(db_session).get_kpi()
    assert kpi.gate_lpr_failed == 1
    assert kpi.gate_lpr_success == 0


# --------------------------------------------------------------------------------------
# LPR Trigger Box: ô cố định ngắm sẵn vào tầm biển số ở vị trí dừng bốt
# --------------------------------------------------------------------------------------

def test_crop_trigger_box_cuts_the_declared_rectangle():
    frame = _gate_frame()  # 480x640

    roi = LPREngine.crop_trigger_box(frame, [86.0, 76.0, 9.0, 16.0])

    assert roi is not None
    assert roi.shape[1] == pytest.approx(640 * 0.09, abs=2)
    assert roi.shape[0] == pytest.approx(480 * 0.16, abs=2)


def test_crop_trigger_box_clamps_to_frame_bounds():
    roi = LPREngine.crop_trigger_box(_gate_frame(), [95.0, 95.0, 20.0, 20.0])

    assert roi is not None
    assert roi.shape[0] > 0 and roi.shape[1] > 0


def test_crop_trigger_box_rejects_degenerate_input():
    assert LPREngine.crop_trigger_box(_gate_frame(), None) is None
    assert LPREngine.crop_trigger_box(_gate_frame(), [10.0, 10.0, 0.0, 5.0]) is None
    assert LPREngine.crop_trigger_box(None, [10.0, 10.0, 5.0, 5.0]) is None


def test_trigger_box_runs_exactly_one_ocr_pass(fake_easyocr):
    """Cả điểm của trigger box: một lượt OCR trên ô nhỏ thay vì 4 lượt quét cản va."""
    engine = LPREngine()
    engine.get_reader()

    engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0], trigger_box=[86.0, 76.0, 9.0, 16.0])

    assert fake_easyocr[0].readtext_calls == 1


def test_trigger_box_reads_only_inside_the_box(fake_easyocr):
    """Vùng đưa vào OCR phải là ô đã khai báo, không phải dải cản va của BBox xe."""
    engine = LPREngine()
    engine.get_reader()
    seen = []
    fake_easyocr[0].readtext = lambda image: seen.append(image.shape) or []

    engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0], trigger_box=[86.0, 76.0, 9.0, 16.0])

    # Ô 9%x16% của khung 640x480 = 58x77 px, phóng lên >=200px chiều ngang.
    assert len(seen) == 1
    assert seen[0][1] >= 200


def test_read_plate_falls_back_to_bumper_scan_without_a_trigger_box(fake_easyocr):
    """Làn chưa đo được toạ độ ô ngắm vẫn phải chạy được, không im lặng bỏ qua."""
    engine = LPREngine()
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [80, 0], [80, 20], [0, 20]], "29A12345", 0.88),
    ]

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0], trigger_box=None)

    assert reading.plate_text == "29A-123.45"


def test_events_pipeline_uses_the_trigger_box_of_the_matching_lane(db_session, monkeypatch):
    monkeypatch.setattr(
        events.settings, "GATE_LPR_TRIGGER_BOXES", '{"zA": [10.0, 20.0, 5.0, 6.0]}'
    )
    seen = []

    def fake_read(frame_matrix, bbox, trigger_box=None):
        seen.append(trigger_box)
        return PlateReading(None, 0.0, "unreadable")

    monkeypatch.setattr(events.lpr_engine, "read_plate", fake_read)
    other_lane = _inbound_detection(zone_name="Làn IN 2")
    other_lane["zone_id"] = "zB"

    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection(), other_lane],
        frame_matrix=_gate_frame(),
    )

    # zA có ô ngắm; zB chưa khai báo nên phải nhận None để lùi về quét cản va.
    assert seen == [[10.0, 20.0, 5.0, 6.0], None]


def test_read_plate_prefers_a_real_full_read_over_the_roster(fake_easyocr):
    engine = LPREngine(plate_roster=ROSTER)
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [80, 0], [80, 20], [0, 20]], "29A12345", 0.88),
    ]

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert reading.plate_text == "29A-123.45"
    assert reading.source == "ocr"


def test_read_plate_stays_unreadable_when_nothing_matches(fake_easyocr):
    engine = LPREngine(plate_roster=ROSTER)
    engine.get_reader()
    fake_easyocr[0].results = [
        ([[0, 0], [90, 0], [90, 20], [0, 20]], "EVERGREEN", 0.95),
    ]

    reading = engine.read_plate(_gate_frame(), [30.0, 40.0, 20.0, 30.0])

    assert reading.plate_text is None
    assert reading.source == "unreadable"


# --------------------------------------------------------------------------------------
# Pipeline sự kiện cổng: LPR_PASSAGE, phân loại tag, cooldown
# --------------------------------------------------------------------------------------

def test_unknown_plate_creates_severity_2_event_and_vehicle_row(db_session, monkeypatch):
    _stub_ocr(monkeypatch, "29A-123.45", confidence=0.93)

    persisted = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection()],
        frame_matrix=_gate_frame(),
    )

    assert len(persisted) == 1
    event = persisted[0]
    assert event.event_type == "LPR_PASSAGE"
    assert event.camera_id == GATE_CAMERA_ID
    assert event.license_plate == "29A-123.45"
    assert event.severity_level == 2
    assert event.confidence == pytest.approx(0.93)
    assert event.lane_id == "Làn IN 1"
    assert event.zone_id == INBOUND_LANE_ZONE_ID
    assert event.bbox == [30.0, 40.0, 20.0, 30.0]

    vehicle = VehicleRepository(db_session).get_by_plate("29A-123.45")
    assert vehicle is not None
    assert vehicle.tag_label == "unknown"


def test_known_plate_is_classified_severity_1(db_session, monkeypatch):
    db_session.add(
        VehicleModel(
            id="veh-known-01",
            license_plate="15C-678.90",
            vehicle_type="truck",
            tag_label="known",
        )
    )
    db_session.commit()
    _stub_ocr(monkeypatch, "15C-678.90")

    persisted = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection(object_class="truck")],
        frame_matrix=_gate_frame(),
    )

    assert persisted[0].severity_level == 1
    # Lượt xe qua cổng không được hạ nhãn đã gán về 'unknown'.
    assert VehicleRepository(db_session).get_by_plate("15C-678.90").tag_label == "known"


def test_blacklisted_plate_is_classified_severity_3(db_session, monkeypatch):
    db_session.add(
        VehicleModel(
            id="veh-black-01",
            license_plate="51B-456.78",
            vehicle_type="car",
            tag_label="blacklisted",
        )
    )
    db_session.commit()
    _stub_ocr(monkeypatch, "51B-456.78")

    persisted = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection()],
        frame_matrix=_gate_frame(),
    )

    assert persisted[0].severity_level == 3
    assert VehicleRepository(db_session).get_by_plate("51B-456.78").tag_label == "blacklisted"


def test_cooldown_suppresses_duplicate_plate_within_window(db_session, monkeypatch):
    _stub_ocr(monkeypatch, "29A-123.45")
    detection = _inbound_detection()

    first = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection],
        frame_matrix=_gate_frame(),
    )
    # Frame kế tiếp của cùng một lượt xe.
    second = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection],
        frame_matrix=_gate_frame(),
    )

    assert len(first) == 1
    assert second == []
    stored = (
        db_session.query(EventModel)
        .filter(EventModel.license_plate == "29A-123.45")
        .all()
    )
    assert len(stored) == 1


def test_cooldown_is_per_plate_not_per_lane(db_session, monkeypatch):
    """Xe lấn ranh hai làn IN vẫn chỉ được ghi một lượt."""
    _stub_ocr(monkeypatch, "29A-123.45")

    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection(zone_name="Làn IN 1")],
        frame_matrix=_gate_frame(),
    )
    lane_two = _inbound_detection(zone_name="Làn IN 2")
    lane_two["zone_id"] = "zB"
    second = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[lane_two],
        frame_matrix=_gate_frame(),
    )

    assert second == []


def test_expired_cooldown_allows_the_next_passage(db_session, monkeypatch):
    _stub_ocr(monkeypatch, "29A-123.45")
    detection = _inbound_detection()

    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection],
        frame_matrix=_gate_frame(),
    )
    # Đẩy dấu thời gian lùi quá cửa sổ 12s thay vì sleep thật.
    for key in events.lpr_event_manager._cooldown_cache:
        events.lpr_event_manager._cooldown_cache[key] -= 20.0

    second = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection],
        frame_matrix=_gate_frame(),
    )

    assert len(second) == 1


def test_plate_needs_repeated_reads_before_it_becomes_a_passage(db_session, monkeypatch):
    """Đọc được một lần thì chưa đủ; phải đủ số lần đồng thuận mới ghi lượt xe."""
    monkeypatch.setattr(settings, "LPR_MIN_CONFIRMATIONS", 3)
    _stub_ocr(monkeypatch, "29A-123.45")
    detection = _inbound_detection()

    def run_once():
        return events.persist_gate_lpr_events(
            db_session,
            camera_id=GATE_CAMERA_ID,
            detections=[detection],
            frame_matrix=_gate_frame(),
        )

    assert run_once() == [], "Lượt đọc thứ nhất chưa đủ bằng chứng"
    assert run_once() == [], "Lượt đọc thứ hai vẫn chưa đủ"
    third = run_once()

    assert len(third) == 1
    assert third[0].license_plate == "29A-123.45"


def test_one_off_misread_never_becomes_a_passage(db_session, monkeypatch):
    """Chuỗi ma đọc trúng một lần rồi biến mất thì không được ghi thành lượt xe.

    Dựng lại đúng ca đo được trên clip cổng: chiếc `15H-032.03` bị đồng hồ camera in đè
    lên dòng trên của tấm biển hai dòng, sinh ra các biến thể `55H-032.03` (0.715) và
    `11H-032.03` (0.978). Chú ý con số thứ hai — nó tự tin hơn cả nhiều lần đọc đúng,
    nên siết ngưỡng confidence không loại được nó; chỉ số lần lặp mới loại được.
    """
    monkeypatch.setattr(settings, "LPR_MIN_CONFIRMATIONS", 3)
    detection = _inbound_detection()
    reads = iter([
        ("15H-032.03", 0.99),
        ("55H-032.03", 0.715),
        ("15H-032.03", 1.0),
        ("11H-032.03", 0.978),
        ("15H-032.03", 0.983),
    ])

    def fake_read(frame_matrix, bbox, trigger_box=None):
        plate, confidence = next(reads)
        return PlateReading(plate, confidence, "plate_ocr")

    monkeypatch.setattr(events.lpr_engine, "read_plate", fake_read)

    persisted = []
    for _ in range(5):
        persisted.extend(
            events.persist_gate_lpr_events(
                db_session,
                camera_id=GATE_CAMERA_ID,
                detections=[detection],
                frame_matrix=_gate_frame(),
            )
        )

    plates = [event.license_plate for event in persisted]
    assert plates == ["15H-032.03"], f"Chuỗi ma đã lọt vào sổ: {plates}"


def test_repeat_passage_is_recorded_again_so_the_live_list_keeps_moving(db_session, monkeypatch):
    """Cùng một biển đi qua lần nữa vẫn sinh sự kiện mới sau khi hết cooldown.

    Đã có lúc việc chặn trùng nằm ở tầng ghi dữ liệu — biển nào từng thấy thì thôi không
    ghi nữa — và cái giá phải trả là bảng "Biển số đã nhận diện" đóng băng vĩnh viễn ở
    lần cuối mỗi xe được thấy. Chặn trùng giờ nằm ở tầng đếm KPI
    (`GET /events/gate-kpi` đếm biển số phân biệt), nên tầng dữ liệu phải ghi đủ.
    """
    _stub_ocr(monkeypatch, "29A-123.45")
    detection = _inbound_detection()

    first = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection],
        frame_matrix=_gate_frame(),
    )
    for key in events.lpr_event_manager._cooldown_cache:
        events.lpr_event_manager._cooldown_cache[key] -= 20.0

    second = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection],
        frame_matrix=_gate_frame(),
    )

    assert len(first) == 1
    assert len(second) == 1, "Lượt qua cổng sau phải được ghi, nếu không danh sách sẽ chết"


def test_non_inbound_zone_and_non_vehicle_classes_are_never_read_by_bbox(db_session, monkeypatch):
    """Người, xe đạp và xe ngoài làn không bao giờ được đưa bbox của mình vào OCR.

    Vẫn còn đúng một lượt quét toàn khung (bbox None): camera cổng ngắm cận cảnh nên khi
    xe áp sát, YOLO mất dấu nó và bbox không còn là thứ đáng tin để bám theo — xem ghi
    chú ở `persist_gate_lpr_events`. Điều bài test này khoá là OCR không được chạy *theo
    bbox của đối tượng ngoài phạm vi LPR*.
    """
    calls = _stub_ocr(monkeypatch, "29A-123.45")

    outside_lane = _inbound_detection(zone_name="Bãi chờ")
    no_zone = _inbound_detection(zone_name=None)
    pedestrian = _inbound_detection(zone_name="Làn IN 1")
    pedestrian["object_class"] = "person"
    bicycle = _inbound_detection(zone_name="Làn IN 2")
    bicycle["object_class"] = "bicycle"

    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[outside_lane, no_zone, pedestrian, bicycle],
        frame_matrix=_gate_frame(),
    )

    read_bboxes = [bbox for _frame, bbox, _trigger in calls]
    assert read_bboxes == [None], "Chỉ được phép quét toàn khung, không đọc theo bbox nào"


def test_other_cameras_never_run_lpr(db_session, monkeypatch):
    calls = _stub_ocr(monkeypatch, "29A-123.45")

    persisted = events.persist_gate_lpr_events(
        db_session,
        camera_id="BAI-KIEM",
        detections=[_inbound_detection()],
        frame_matrix=_gate_frame(),
    )

    assert persisted == []
    assert calls == []


# --------------------------------------------------------------------------------------
# KPI realtime cache
# --------------------------------------------------------------------------------------

def test_successful_read_updates_gate_kpi_counters(db_session, monkeypatch, reset_gate_kpi):
    _stub_ocr(monkeypatch, "29A-123.45", confidence=0.90)

    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection()],
        frame_matrix=_gate_frame(),
    )

    kpi = KpiRepository(db_session).get_kpi()
    assert kpi.gate_vehicles_total == 1
    assert kpi.gate_lpr_success == 1
    assert kpi.gate_lpr_failed == 0
    assert kpi.gate_avg_confidence == pytest.approx(90.0)


def test_unreadable_plate_counts_as_failed_passage(db_session, monkeypatch, reset_gate_kpi):
    monkeypatch.setattr(
        events.lpr_engine,
        "read_plate",
        lambda frame, bbox, trigger_box=None: PlateReading(None, 0.41, "unreadable"),
    )
    detection = _inbound_detection()

    persisted = events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection, detection],
        frame_matrix=_gate_frame(),
    )

    assert persisted == []

    # Chiếc xe đứng nhiều frame vẫn chỉ là một lượt: lượt hỏng chốt lúc nó rời làn.
    _close_gate_passage(db_session)
    kpi = KpiRepository(db_session).get_kpi()
    assert kpi.gate_vehicles_total == 1
    assert kpi.gate_lpr_failed == 1
    assert kpi.gate_lpr_success == 0


def test_frames_right_after_a_successful_read_are_not_counted_as_failures(
    db_session, monkeypatch, reset_gate_kpi
):
    """Khúc đầu và khúc đuôi của cùng một lượt xe không được tính là lượt hỏng.

    Một chiếc xe qua cổng mất nhiều giây: lúc mới vào tấm biển chưa tới tầm, lúc đi khỏi
    thì đã ra khỏi tầm, chỉ khúc giữa mới đọc được. Trước khi có ràng buộc này, chính
    chiếc xe vừa đọc thành công lại tự cộng thêm lượt "không đọc được" cho hai khúc kia
    — đo trên máy đang chạy: 154 lượt hỏng trong 41 phút trên một clip chỉ có 5 xe, tất
    cả đều đọc được.
    """
    detection = _inbound_detection()
    _stub_ocr(monkeypatch, "29A-123.45")
    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[detection],
        frame_matrix=_gate_frame(),
    )

    # Ngay sau đó tấm biển ra khỏi tầm, nhưng chiếc xe vẫn còn trong làn.
    monkeypatch.setattr(
        events.lpr_engine,
        "read_plate",
        lambda frame, bbox, trigger_box=None: PlateReading(None, 0.2, "unreadable"),
    )
    for _ in range(3):
        events.persist_gate_lpr_events(
            db_session,
            camera_id=GATE_CAMERA_ID,
            detections=[detection],
            frame_matrix=_gate_frame(),
        )

    kpi = KpiRepository(db_session).get_kpi()
    assert kpi.gate_lpr_success == 1
    assert kpi.gate_lpr_failed == 0, "Cùng một lượt xe không được vừa đọc được vừa hỏng"


def test_average_confidence_accumulates_across_passages(db_session, monkeypatch, reset_gate_kpi):
    _stub_ocr(monkeypatch, "29A-123.45", confidence=0.80)
    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection()],
        frame_matrix=_gate_frame(),
    )

    _stub_ocr(monkeypatch, "15C-678.90", confidence=0.90)
    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection()],
        frame_matrix=_gate_frame(),
    )

    kpi = KpiRepository(db_session).get_kpi()
    assert kpi.gate_vehicles_total == 2
    assert kpi.gate_lpr_success == 2
    assert kpi.gate_avg_confidence == pytest.approx(85.0)


# --------------------------------------------------------------------------------------
# API contract: GET /api/v1/events?camera_id=GATE-01
# --------------------------------------------------------------------------------------

def test_events_endpoint_returns_lpr_passages_for_gate_camera(db_session, monkeypatch):
    _stub_ocr(monkeypatch, "29A-123.45", confidence=0.93)
    events.persist_gate_lpr_events(
        db_session,
        camera_id=GATE_CAMERA_ID,
        detections=[_inbound_detection()],
        frame_matrix=_gate_frame(),
    )
    # Sự kiện của camera khác không được lọt vào danh sách cổng.
    db_session.add(
        EventModel(
            id="evt-area-noise-01",
            timestamp=datetime(2026, 8, 26, 8, 0, 0, tzinfo=timezone.utc),
            camera_id="BAI-KIEM",
            event_type="ZONE_VIOLATION",
            severity_level=3,
            object_class="Người",
            confidence=0.88,
        )
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[events.get_db] = override_get_db
    try:
        response = TestClient(app).get(
            "/api/v1/events", params={"camera_id": GATE_CAMERA_ID}
        )
    finally:
        app.dependency_overrides.pop(events.get_db, None)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    row = payload[0]
    assert row["event_type"] == "LPR_PASSAGE"
    assert row["camera_id"] == GATE_CAMERA_ID
    assert row["license_plate"] == "29A-123.45"
    assert row["severity_level"] == 2
    # `lane_id` là tên làn chép lại từ detection lúc ghi sự kiện, còn `zone_name` được
    # tra ngược từ bảng zones theo zone_id — nên nó mang tên zone hiện hành trong seed.
    assert row["lane_id"] == "Làn IN 1"
    assert row["zone_name"] == "Làn IN"
    assert row["confidence"] == pytest.approx(0.93)


def test_gate_kpi_counts_every_passage_not_just_the_latest_page(db_session, reset_gate_kpi):
    """KPI đếm trên toàn bộ bảng events, không phải trên trang 20 dòng của dashboard.

    Đây là hồi quy cho đúng triệu chứng đã gặp: dashboard tự đếm trên mảng sự kiện vừa
    tải về, mà mảng đó bị chặn ở `limit = 20`, nên "Lượt xe qua cổng" đứng cứng ở 20 dù
    cơ sở dữ liệu có bao nhiêu lượt đi nữa.
    """
    for index in range(25):
        db_session.add(
            EventModel(
                id=f"evt-kpi-{index:02d}",
                timestamp=datetime(2026, 8, 31, 9, 0, index, tzinfo=timezone.utc),
                camera_id=GATE_CAMERA_ID,
                event_type="LPR_PASSAGE",
                severity_level=2,
                license_plate=f"29A-100.{index:02d}",
                object_class="truck",
                confidence=0.90,
            )
        )
    # Cùng một chiếc xe đi qua lần nữa ở vòng lặp video sau: thêm bản ghi, không thêm xe.
    db_session.add(
        EventModel(
            id="evt-kpi-repeat",
            timestamp=datetime(2026, 8, 31, 9, 5, 0, tzinfo=timezone.utc),
            camera_id=GATE_CAMERA_ID,
            event_type="LPR_PASSAGE",
            severity_level=2,
            license_plate="29A-100.00",
            object_class="truck",
            confidence=0.90,
        )
    )
    # Vi phạm zone của chính camera này không phải một lượt xe qua cổng.
    db_session.add(
        EventModel(
            id="evt-kpi-noise",
            timestamp=datetime(2026, 8, 31, 9, 1, 0, tzinfo=timezone.utc),
            camera_id=GATE_CAMERA_ID,
            event_type="ZONE_VIOLATION",
            severity_level=3,
            object_class="person",
            confidence=0.80,
        )
    )
    KpiRepository(db_session).update_kpi(gate_lpr_failed=4)
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[events.get_db] = override_get_db
    try:
        response = TestClient(app).get(
            "/api/v1/events/gate-kpi", params={"camera_id": GATE_CAMERA_ID}
        )
    finally:
        app.dependency_overrides.pop(events.get_db, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["lpr_success"] == 25, (
        "Phải vượt trần 20 dòng của dashboard, và đếm theo biển số phân biệt nên lượt "
        "đi qua lần thứ hai của cùng một xe không làm tăng con số"
    )
    assert payload["lpr_failed"] == 4
    assert payload["vehicles_total"] == 29
    # Event.confidence lưu thang 0-1, KPI hiển thị phần trăm.
    assert payload["avg_confidence"] == pytest.approx(90.0)


def test_live_detections_reports_ocr_status_for_gate_camera(db_session, monkeypatch):
    """UI phải phân biệt được 'không có xe' với 'OCR engine hỏng'."""
    monkeypatch.setattr(events.lpr_engine, "ocr_status", lambda: "unavailable")
    monkeypatch.setattr(events, "_resolve_video_path_or_503", lambda camera_id: "fake.mp4")
    monkeypatch.setattr(events, "get_camera_pipeline", lambda *args, **kwargs: _NoFramePipeline())

    def override_get_db():
        yield db_session

    app.dependency_overrides[events.get_db] = override_get_db
    try:
        client = TestClient(app)
        gate = client.get("/api/v1/events/live-detections", params={"camera_id": GATE_CAMERA_ID})
        yard = client.get("/api/v1/events/live-detections", params={"camera_id": "BAI-KIEM"})
    finally:
        app.dependency_overrides.pop(events.get_db, None)

    assert gate.status_code == 200
    assert gate.headers["X-OCR-Status"] == "unavailable"
    # Camera khác không dùng LPR: hỏi trạng thái ở đó chỉ tổ nạp model EasyOCR vô ích.
    assert "X-OCR-Status" not in yard.headers


class _NoFramePipeline:
    """Pipeline không có frame: đủ để kiểm tra header mà không cần decode video thật."""

    def update_zones(self, zones, zone_version):
        return None

    def get_latest_snapshot(self):
        return None


# --------------------------------------------------------------------------------------
# EasyOCR thật. Mock hoàn toàn từng khiến suite xanh trong khi runtime LPR đã chết vì
# thiếu package — nhóm này là hàng rào chặn đúng kiểu hỏng đó.
# --------------------------------------------------------------------------------------

easyocr_installed = pytest.mark.skipif(
    __import__("importlib.util", fromlist=["util"]).find_spec("easyocr") is None,
    reason="easyocr chưa được cài trong môi trường này",
)


@pytest.fixture(scope="module")
def real_engine():
    """Một Reader thật dùng chung cả module: mỗi lần dựng mất vài giây.

    Sàn cứng hạ về 0 ở đây để đo được năng lực thô của pipeline OCR. Sàn production
    (MIN_ACCEPTED_PLATE_CONFIDENCE) được kiểm riêng ở nhóm test phía trên.
    """
    engine = LPREngine(confidence_threshold=0.30, plate_roster=ROSTER, min_accepted_confidence=0.0)
    if not engine.is_available():
        pytest.skip("Không khởi tạo được EasyOCR Reader")
    return engine


@easyocr_installed
def test_real_easyocr_reader_initializes():
    engine = LPREngine()

    assert engine.is_available() is True, "easyocr đã cài thì Reader phải dựng được"
    assert engine.ocr_status() == "ready"


@easyocr_installed
def test_real_ocr_reads_a_clean_plate_end_to_end(real_engine):
    """Biển rõ nét, đúng vị trí cản va: phải ra chuỗi đúng định dạng Việt Nam."""
    frame, bbox = _frame_with_plate_at_bumper(plate_width=150)

    reading = real_engine.read_plate(frame, bbox)

    assert reading.recognized, f"Không đọc được biển; mảnh OCR thu được: {reading.fragments}"
    assert reading.plate_text == "16H-002.15"


@easyocr_installed
def test_real_ocr_recovers_a_degraded_plate_through_the_roster(real_engine):
    """Biển 50px: EasyOCR đọc lệch vài ký tự, roster phải cứu được lượt xe này.

    Đo thật trên pipeline: ở 50px EasyOCR trả '164-00215' cho biển 16H-002.15 — sai
    đúng một ký tự. Đây là ca mà cơ chế khớp roster tồn tại để xử lý.
    """
    frame, bbox = _frame_with_plate_at_bumper(plate_width=50)

    reading = real_engine.read_plate(frame, bbox)

    assert reading.plate_text == "16H-002.15"
    assert reading.source == "roster_match"
    # Bằng chứng chỉ có một phần nên confidence phải thấp hơn hẳn một lượt đọc trọn vẹn.
    assert reading.confidence < 0.70


@easyocr_installed
def test_real_ocr_localizes_but_cannot_read_a_30px_plate(real_engine):
    """Giới hạn vật lý, ghi lại bằng test để không ai kỳ vọng sai.

    Ở 34px (đúng cỡ biển sau container trong data/video/GATE-01.mp4), khâu khoanh vùng
    + phóng to vẫn tìm ra tấm biển và bóc được ký tự, nhưng nội dung sai hoàn toàn —
    9px chiều cao không còn đủ thông tin. Hệ thống phải nhận là không đọc được chứ
    không được gán bừa một biển trong roster.
    """
    frame, bbox = _frame_with_plate_at_bumper(plate_width=34)

    reading = real_engine.read_plate(frame, bbox)

    assert reading.fragments, "Khâu khoanh vùng + phóng to phải bóc được ký tự ở 34px"
    assert reading.plate_text is None
    assert reading.source == "unreadable"

"""
Bảo vệ bộ toạ độ polygon zone đã vẽ tay cho footage cảng HATECO.

Toạ độ này nằm ở **hai nơi** — `docs/contracts/db/schema.sql` (seed cho checkout
sạch) và `backend/scripts/seed_area_demo.py` (seed lại khi đã có CSDL). Hai nguồn
lệch nhau thì tuỳ cách khởi tạo mà zone sẽ khác nhau, và triệu chứng là "cảnh báo
sai chỗ" — rất khó lần ra. Test này khoá chúng phải khớp.

Phần kiểm hình học bắt những lỗi làm zone im lặng mất tác dụng: toạ độ tràn ngoài
0-100, đa giác suy biến, hoặc một lớp vừa được phép vừa bị cấm.
"""

import os

import pytest

from backend.database.engine import get_sqlite_engine, init_db, SessionLocal
from backend.database.repository import ZoneRepository
from backend.app.services.vision_pipeline import CANONICAL_8_OBJECT_CLASSES
from backend.scripts.seed_area_demo import ALL_ZONES

TEST_DB_URL = "sqlite:///./test_zone_geometry.db"
CAMERAS = ["GATE-01", "BAI-KIEM", "XUONG-AN-NINH"]
EXPECTED_ZONE_IDS = {"zA", "zB", "zK1", "zK2", "zK3", "zX1", "zX2"}


@pytest.fixture(scope="module")
def schema_zones():
    """Zone đúng như một bản checkout sạch dựng ra từ schema.sql."""
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path="docs/contracts/db/schema.sql", target_engine=engine)
    db = SessionLocal(bind=engine)
    try:
        zones = {}
        for camera_id in CAMERAS:
            for zone in ZoneRepository(db).get_by_camera(camera_id):
                zones[zone.id] = zone
        yield zones
    finally:
        db.close()
        engine.dispose()
        if os.path.exists("test_zone_geometry.db"):
            try:
                os.remove("test_zone_geometry.db")
            except PermissionError:
                pass


def as_points(vertices):
    return [(float(v["x"]), float(v["y"])) if isinstance(v, dict) else (float(v[0]), float(v[1]))
            for v in vertices]


def polygon_area(points):
    """Diện tích theo công thức shoelace; 0 nghĩa là đa giác suy biến."""
    total = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


# --- Hai nguồn seed phải khớp -------------------------------------------------

def test_schema_and_seed_define_the_same_zone_set(schema_zones):
    seed_ids = {z.id for z in ALL_ZONES}
    assert seed_ids == EXPECTED_ZONE_IDS
    assert set(schema_zones) == EXPECTED_ZONE_IDS


@pytest.mark.parametrize("zone", ALL_ZONES, ids=lambda z: z.id)
def test_seed_zone_matches_schema_sql(zone, schema_zones):
    """
    Sửa toạ độ ở một nơi mà quên nơi kia là cách chắc chắn nhất để làm mất công
    vẽ tay — checkout sạch sẽ dựng lại bộ cũ mà không báo gì.
    """
    from_schema = schema_zones[zone.id]
    assert as_points(zone.vertices) == as_points(from_schema.vertices)
    assert zone.camera_id == from_schema.camera_id
    assert zone.name == from_schema.name
    assert sorted(zone.allowed_classes) == sorted(from_schema.allowed_classes)
    assert sorted(zone.forbidden_classes) == sorted(from_schema.forbidden_classes)


# --- Hình học -----------------------------------------------------------------

@pytest.mark.parametrize("zone", ALL_ZONES, ids=lambda z: z.id)
def test_vertices_are_percentages_within_frame(zone):
    """Quy ước xuyên suốt dự án: toạ độ zone là phần trăm 0-100 của khung hình."""
    points = as_points(zone.vertices)
    assert len(points) >= 3, f"{zone.id} không đủ 3 đỉnh"
    for x, y in points:
        assert 0.0 <= x <= 100.0, f"{zone.id} có x={x} ngoài [0,100]"
        assert 0.0 <= y <= 100.0, f"{zone.id} có y={y} ngoài [0,100]"


@pytest.mark.parametrize("zone", ALL_ZONES, ids=lambda z: z.id)
def test_polygon_covers_meaningful_area(zone):
    """
    Đa giác suy biến vẫn lưu được vào CSDL và vẫn vẽ ra được trên SVG, nhưng
    point_in_polygon sẽ không bao giờ khớp — zone im lặng mất tác dụng.
    """
    area = polygon_area(as_points(zone.vertices))
    assert area > 1.0, f"{zone.id} chỉ phủ {area:.2f}% diện tích khung hình"


@pytest.mark.parametrize("zone", ALL_ZONES, ids=lambda z: z.id)
def test_vertices_stay_below_horizon(zone):
    """
    Không đỉnh nào được nằm ở nửa trên khung hình.

    Bộ toạ độ cũ có zK3 trùm lên bầu trời và mặt biển — vô nghĩa về mặt giám sát
    và chỉ tổ bắt nhầm tàu, cẩu bờ ở xa. Cả ba camera đều nhìn xuống mặt sân, nên
    y < 30 luôn là dấu hiệu polygon vẽ trượt lên đường chân trời.
    """
    highest = min(y for _x, y in as_points(zone.vertices))
    assert highest >= 30.0, f"{zone.id} có đỉnh ở y={highest}, nhiều khả năng đã trùm lên trời"


# --- Luật phân loại -----------------------------------------------------------

@pytest.mark.parametrize("zone", ALL_ZONES, ids=lambda z: z.id)
def test_classes_belong_to_canonical_taxonomy(zone):
    for cls_name in list(zone.allowed_classes) + list(zone.forbidden_classes):
        assert cls_name in CANONICAL_8_OBJECT_CLASSES, \
            f"{zone.id} tham chiếu lớp '{cls_name}' ngoài taxonomy 8 lớp"


@pytest.mark.parametrize("zone", ALL_ZONES, ids=lambda z: z.id)
def test_allowed_and_forbidden_do_not_overlap(zone):
    """
    Trùng nhau thì `cls in forbidden` thắng trong vision_pipeline, tức là phần
    allowed bị vô hiệu một cách âm thầm.
    """
    overlap = set(zone.allowed_classes) & set(zone.forbidden_classes)
    assert not overlap, f"{zone.id} vừa cho phép vừa cấm: {sorted(overlap)}"


def test_person_is_only_restricted_on_walkway_zones():
    """
    Quyết định sản phẩm (2026-08-21): vùng bãi/thao tác **không** cấm `person`.

    Cảnh cảng lúc nào cũng có công nhân; cấm person ở đó biến sổ cảnh báo thành
    một danh sách toàn 'Người' lặp lại, che mất vi phạm đáng chú ý. Chiều ngược
    lại mới là cái cần bắt: máy móc nặng lấn vào lối đi bộ.
    """
    for zone in ALL_ZONES:
        assert "person" not in zone.forbidden_classes, \
            f"{zone.id} cấm person — xem lại quyết định về forbidden_classes"

    walkway = next(z for z in ALL_ZONES if z.id == "zX2")
    assert "person" in walkway.allowed_classes
    for machine in ("forklift", "crane", "truck", "container"):
        assert machine in walkway.forbidden_classes

"""
Seed dữ liệu demo cho camera bãi (BAI-KIEM, XUONG-AN-NINH) và cổng (GATE-01).

Chạy từ thư mục gốc dự án (VisionEdge-AI/):
    .venv/Scripts/python.exe backend/scripts/seed_area_demo.py            # thêm cái còn thiếu
    .venv/Scripts/python.exe backend/scripts/seed_area_demo.py --reset-zones  # ghi đè zone

`--reset-zones` ghi đè toạ độ/luật của các zone liệt kê dưới đây bằng giá trị
trong file này. Dùng khi vừa chỉnh polygon và muốn đưa CSDL về đúng bản seed.
Không đụng tới zone do người dùng tự tạo trên UI.

Sau khi seed, **luôn render lại ảnh xác minh** rồi mở ra xem:
    .venv/Scripts/python.exe backend/scripts/render_zone_overlay.py

------------------------------------------------------------------------------
Toạ độ polygon là phần trăm 0-100 của khung hình, vẽ cho footage CCTV cảng
HATECO Hải Phòng (bộ clip 60 giây do backend/scripts/prepare_demo_videos.py cắt).
Bộ toạ độ trước đây được vẽ cho footage cũ nên không còn bám vật thể nào —
zK3 khi đó trùm lên bầu trời, zX2 "lối đi bộ" lại nằm trên khu công trường.

Cách vẽ bộ hiện tại: chạy YOLO trên toàn bộ ba clip (lấy mẫu mỗi 25 frame), gom
tâm bbox theo lớp, rồi vẽ polygon bám đúng vùng **thực sự có đối tượng đi qua**
thay vì vùng trông có vẻ hợp lý. Quỹ đạo đo được:

    BAI-KIEM       xe nâng container chạy chéo, tâm (43,56) -> (21,82)
    XUONG-AN-NINH  máy móc ở bãi phải (62,65); người đi bộ dải trái (31,56)-(44,95)
    GATE-01        xe làn 1 tâm ~(22,74); xe làn 2 tâm ~(80,56)-(83,54)

Luật: vùng lối đi bộ cấm máy móc, vùng bãi/thao tác cấm phương tiện cá nhân.
Cố tình **không cấm `person`** ở các zone bãi — cảnh cảng lúc nào cũng có công
nhân nên cấm person sẽ biến sổ cảnh báo thành một danh sách toàn 'Người' lặp lại,
che mất những vi phạm đáng chú ý.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

# Console Windows mặc định cp1252, không mã hoá nổi tiếng Việt — thiếu dòng này
# thì script chết giữa chừng ở câu print đầu tiên, sau khi đã sửa dữ liệu nhưng
# trước khi kịp commit.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from backend.database.engine import SessionLocal, init_db
from backend.database.models import Camera, Zone

# Phương tiện cá nhân: không có việc gì trong khu vực khai thác container.
PERSONAL_VEHICLES = ["car", "motorbike", "bicycle"]
# Máy móc nặng: không được lấn vào lối dành cho người đi bộ.
HEAVY_MACHINERY = ["forklift", "crane", "truck", "container"]

CAMERAS = [
    Camera(
        id="BAI-KIEM",
        name="Camera Bãi Kiểm An Ninh",
        location="Bãi kiểm hóa container",
        stream_url="/videos/BAI-KIEM.mp4",
        status="online",
        fps=25.0,
    ),
    Camera(
        id="XUONG-AN-NINH",
        name="Camera Xưởng An Ninh",
        location="Xưởng an ninh nội bộ",
        stream_url="/videos/XUONG-AN-NINH.mp4",
        status="online",
        fps=16.0,
    ),
]

ZONES = [
    # Dãy container lạnh bên phải khung — nơi xe nâng đưa container tới kiểm hoá.
    Zone(
        id="zK1", camera_id="BAI-KIEM", name="Zone bãi kiểm hoá",
        vertices=[{"x": 54, "y": 42}, {"x": 89, "y": 44}, {"x": 93, "y": 78}, {"x": 55, "y": 80}],
        allowed_classes=["container", "forklift", "truck", "crane", "person"],
        forbidden_classes=list(PERSONAL_VEHICLES),
        color="#30D158",
    ),
    # Bám vạch kẻ vàng chia làn in sẵn trên mặt sân. Phủ trọn quỹ đạo đo được của
    # xe nâng container: tâm bbox đi từ (43,56) xuống (21,82).
    Zone(
        id="zK2", camera_id="BAI-KIEM", name="Zone làn di chuyển",
        vertices=[{"x": 38, "y": 42}, {"x": 52, "y": 42}, {"x": 40, "y": 100}, {"x": 10, "y": 100}],
        allowed_classes=["container", "forklift", "truck", "crane", "person"],
        forbidden_classes=list(PERSONAL_VEHICLES),
        color="#FF9F0A",
    ),
    # Bãi container xếp chồng bên trái. Đỉnh dừng ở y=38 — cao hơn nữa là đường
    # chân trời và mặt biển, đặt zone lên đó thì chỉ tổ bắt nhầm.
    Zone(
        id="zK3", camera_id="BAI-KIEM", name="Zone bãi container",
        vertices=[{"x": 0, "y": 40}, {"x": 26, "y": 38}, {"x": 30, "y": 66}, {"x": 0, "y": 72}],
        allowed_classes=["container", "forklift", "truck", "crane", "person"],
        forbidden_classes=list(PERSONAL_VEHICLES),
        color="#EF4444",
    ),
    # Bãi container bên phải, nơi xe nâng và xe tải thực sự làm việc.
    Zone(
        id="zX1", camera_id="XUONG-AN-NINH", name="Zone máy móc xưởng",
        vertices=[{"x": 50, "y": 40}, {"x": 99, "y": 44}, {"x": 99, "y": 92}, {"x": 54, "y": 96}],
        allowed_classes=["container", "forklift", "truck", "crane", "person"],
        forbidden_classes=list(PERSONAL_VEHICLES),
        color="#EF4444",
    ),
    # Dải dọc giữa dãy container trắng và bãi — đo được người đi bộ ở (31,56) và
    # (44,95). Đây là zone duy nhất cấm máy móc, và cũng là nguồn cảnh báo chính.
    Zone(
        id="zX2", camera_id="XUONG-AN-NINH", name="Zone lối đi bộ",
        vertices=[{"x": 22, "y": 48}, {"x": 50, "y": 44}, {"x": 54, "y": 96}, {"x": 24, "y": 100}],
        allowed_classes=["person"],
        forbidden_classes=list(HEAVY_MACHINERY),
        color="#30D158",
    ),
]

# Hai làn vào của cổng HATECO (nhãn "Cvao L1,2" in trên khung hình).
#
# Camera cổng đặt rất thấp và sát làn, nên xe đi làn 2 khi tới gần sẽ phủ kín góc
# phải khung hình — tâm bbox của nó nằm ở khoảng (80,56), tức là trên nóc thùng
# container chứ không phải dưới bánh xe. Vì `evaluate_bbox_center_in_zone` xét
# đúng cái tâm đó, hai polygon dưới đây được kéo cao lên tới y≈36 thay vì chỉ ôm
# phần mặt đường. Ôm sát mặt đường trông "đúng" hơn trên ảnh nhưng lại để lọt
# chính những xe cần nhận dạng.
GATE_ZONES = [
    Zone(
        id="zA", camera_id="GATE-01", name="Làn IN 1",
        vertices=[{"x": 30, "y": 40}, {"x": 47, "y": 40}, {"x": 38, "y": 100}, {"x": 2, "y": 100}],
        allowed_classes=["container", "truck"],
        forbidden_classes=list(PERSONAL_VEHICLES),
        color="#30d158",
    ),
    Zone(
        id="zB", camera_id="GATE-01", name="Làn IN 2",
        vertices=[{"x": 52, "y": 38}, {"x": 80, "y": 34}, {"x": 99, "y": 98}, {"x": 58, "y": 100}],
        allowed_classes=["container", "truck"],
        forbidden_classes=list(PERSONAL_VEHICLES),
        color="#2f9bff",
    ),
]

ALL_ZONES = ZONES + GATE_ZONES


def main():
    parser = argparse.ArgumentParser(description="Seed camera và zone demo.")
    parser.add_argument("--reset-zones", action="store_true",
                        help="Ghi đè toạ độ và luật của zone seed bằng giá trị trong file này.")
    args = parser.parse_args()

    init_db(schema_sql_path=os.path.join(ROOT, "docs", "contracts", "db", "schema.sql"))
    db = SessionLocal()
    try:
        for cam in CAMERAS:
            if db.get(Camera, cam.id) is None:
                db.add(cam)
                print(f"[+] Thêm camera {cam.id}")
        db.commit()

        for zone in ALL_ZONES:
            existing = db.get(Zone, zone.id)
            if existing is None:
                db.add(zone)
                print(f"[+] Thêm zone {zone.id} ({zone.camera_id}) — {zone.name}")
            elif args.reset_zones:
                existing.name = zone.name
                existing.vertices = zone.vertices
                existing.allowed_classes = zone.allowed_classes
                existing.forbidden_classes = zone.forbidden_classes
                existing.color = zone.color
                existing.is_active = True
                print(f"[~] Cập nhật zone {zone.id} ({zone.camera_id}) — {zone.name}")
            else:
                print(f"[=] Bỏ qua zone {zone.id} (đã có; dùng --reset-zones để ghi đè)")
        db.commit()
        print("Seed hoàn tất.")
        print("Nhớ chạy backend/scripts/render_zone_overlay.py và mở ảnh ra xem.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

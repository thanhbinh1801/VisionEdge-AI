"""Xoá các lượt xe ma do lỗi đọc sai một frame lẻ (TASK-007/BUG-003).

Trước khi có cơ chế đồng thuận nhiều frame, một chuỗi biển đọc sai ở đúng một khung
hình cũng được ghi thẳng vào bảng `events` như một phương tiện chưa từng thấy. Những
bản ghi đó vẫn nằm lại sau khi lỗi được sửa, và chúng vừa hiện trên dashboard vừa được
tính vào KPI.

Script này chỉ xoá những biển số được liệt kê tường minh ở `GHOST_PLATES`. Không tự suy
đoán biển nào là ma: một biển số hợp lệ nhưng lạ có thể là xe thật mới vào cảng, và xoá
nhầm dữ liệu thật thì không khôi phục được.

Chạy:
    python backend/scripts/purge_ghost_plates.py --dry-run
    python backend/scripts/purge_ghost_plates.py
"""

import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Các chuỗi ma đã xác minh trên clip demo, đều là biến thể đọc sai của hai xe thật:
#   15H-032.03 (biển vuông hai dòng, bị đồng hồ camera in đè lên dòng trên)
#   35H-093.47 (bị nuốt mất một ký tự)
GHOST_PLATES = [
    "55H-032.03",
    "16H-032.03",
    "11H-032.23",
    "11H-032.03",
    "15D-032.03",
    "35H-0934",
]

GATE_CAMERA_ID = "GATE-01"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in ra, không xoá")
    args = parser.parse_args()

    from sqlalchemy import bindparam, text

    from backend.app.core.config import settings
    from backend.database.engine import SessionLocal

    # `IN` với danh sách phải khai báo expanding, nếu không SQLAlchemy truyền cả tuple
    # vào như một giá trị đơn và mệnh đề không khớp gì cả.
    plates_param = bindparam("plates", expanding=True)

    print(f"CSDL: {settings.DATABASE_URL}\n")
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                "SELECT license_plate, COUNT(*) AS n FROM events "
                "WHERE event_type = 'LPR_PASSAGE' AND camera_id = :cam "
                "AND license_plate IN :plates GROUP BY license_plate"
            ).bindparams(plates_param),
            {"cam": GATE_CAMERA_ID, "plates": GHOST_PLATES},
        ).all()

        if not rows:
            print("Không còn lượt xe ma nào trong bảng events.")
        for plate, count in rows:
            print(f"  {plate}: {count} bản ghi")
        total = sum(count for _plate, count in rows)

        if args.dry_run:
            print(f"\n[dry-run] Sẽ xoá {total} bản ghi.")
            return 0

        if total:
            db.execute(
                text(
                    "DELETE FROM events WHERE event_type = 'LPR_PASSAGE' "
                    "AND camera_id = :cam AND license_plate IN :plates"
                ).bindparams(bindparam("plates", expanding=True)),
                {"cam": GATE_CAMERA_ID, "plates": GHOST_PLATES},
            )

        # Phương tiện được tạo tự động khi gặp biển lạ lần đầu; xoá luôn để danh sách
        # phương tiện không còn xe ma.
        vehicles = db.execute(
            text("DELETE FROM vehicles WHERE license_plate IN :plates").bindparams(
                bindparam("plates", expanding=True)
            ),
            {"plates": GHOST_PLATES},
        ).rowcount

        # Bộ đếm "không đọc được" trong kpi_realtime_cache tích luỹ từ thời mọi khung
        # hình trống cũng bị tính là một lượt xe hỏng. Con số đó không tái dựng lại được
        # từ dữ liệu nào cả, nên đưa về 0 và để nó đếm lại từ hành vi đã sửa.
        db.execute(text("UPDATE kpi_realtime_cache SET gate_lpr_failed = 0"))
        db.commit()

        print(f"\nĐã xoá {total} bản ghi sự kiện và {vehicles} phương tiện ma.")
        print("Đã đưa bộ đếm 'không đọc được' về 0.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

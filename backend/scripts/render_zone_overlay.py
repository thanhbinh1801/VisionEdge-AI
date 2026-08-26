"""
Render polygon zone đè lên frame thật để mắt người duyệt.

Không có bước này thì không ai biết polygon có bám đúng vật thể hay không — và
đó chính là cách bộ toạ độ cũ (vẽ cho footage cũ) lọt qua mà không ai thấy.

Chạy từ thư mục gốc dự án (VisionEdge-AI/):

    # Render zone đang nằm trong CSDL, kèm detection thật của YOLO
    .venv/Scripts/python.exe backend/scripts/render_zone_overlay.py

    # Chỉ một camera, nhiều mốc thời gian hơn, không chạy YOLO (nhanh)
    .venv/Scripts/python.exe backend/scripts/render_zone_overlay.py \
        --camera BAI-KIEM --samples 6 --no-detect

    # Xem trước toạ độ trong seed_area_demo.py thay vì toạ độ trong CSDL
    .venv/Scripts/python.exe backend/scripts/render_zone_overlay.py --source seed

Ảnh xuất ra `docs/verification/zones/<CAMERA>_<n>.png`.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

# Console Windows mặc định cp1252, không mã hoá nổi tiếng Việt trong tên zone.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from backend.app.api.v1.events import resolve_camera_video, is_frame_usable
from backend.app.services.vision_pipeline import AIVisionPipeline

DEFAULT_CAMERAS = ["BAI-KIEM", "XUONG-AN-NINH", "GATE-01"]
OUTPUT_DIR = os.path.join(ROOT, "docs", "verification", "zones")

# BGR, khớp với bảng màu severity của UI.
COLOR_OK = (88, 209, 48)
COLOR_VIOLATION = (58, 69, 255)
COLOR_TEXT = (255, 255, 255)


def hex_to_bgr(value: str, fallback=(200, 200, 200)):
    if not value:
        return fallback
    value = value.lstrip("#")
    if len(value) != 6:
        return fallback
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


def load_zones_from_db(camera_id: str):
    from backend.database.engine import SessionLocal
    from backend.database.repository import ZoneRepository

    db = SessionLocal()
    try:
        return [
            {
                "id": z.id,
                "name": z.name,
                "vertices": z.vertices or [],
                "allowed_classes": z.allowed_classes or [],
                "forbidden_classes": z.forbidden_classes or [],
                "color": z.color,
                "severity": 3,
            }
            for z in ZoneRepository(db).get_by_camera(camera_id)
        ]
    finally:
        db.close()


def load_zones_from_seed(camera_id: str):
    """Đọc trực tiếp từ seed_area_demo.py để xem trước trước khi seed vào CSDL."""
    from backend.scripts.seed_area_demo import ZONES, GATE_ZONES

    return [
        {
            "id": z.id,
            "name": z.name,
            "vertices": z.vertices or [],
            "allowed_classes": z.allowed_classes or [],
            "forbidden_classes": z.forbidden_classes or [],
            "color": z.color,
            "severity": 3,
        }
        for z in list(ZONES) + list(GATE_ZONES)
        if z.camera_id == camera_id
    ]


def vertices_to_pixels(vertices, width: int, height: int):
    """Toạ độ zone là phần trăm 0-100 (quy ước xuyên suốt dự án)."""
    pts = []
    for v in vertices:
        if isinstance(v, dict):
            x, y = float(v.get("x", 0)), float(v.get("y", 0))
        else:
            x, y = float(v[0]), float(v[1])
        pts.append([x / 100.0 * width, y / 100.0 * height])
    return np.array(pts, dtype=np.int32)


def draw_zones(frame, zones):
    overlay = frame.copy()
    height, width = frame.shape[:2]

    for zone in zones:
        pts = vertices_to_pixels(zone["vertices"], width, height)
        if len(pts) < 3:
            continue
        color = hex_to_bgr(zone.get("color"))
        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

    cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, dst=frame)

    # Nhãn vẽ sau khi trộn để chữ không bị mờ.
    for zone in zones:
        pts = vertices_to_pixels(zone["vertices"], width, height)
        if len(pts) < 3:
            continue
        cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
        label = f"{zone['id']} {zone['name']}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (cx - tw // 2 - 4, cy - th - 6), (cx + tw // 2 + 4, cy + 4), (0, 0, 0), -1)
        cv2.putText(frame, label, (cx - tw // 2, cy - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, hex_to_bgr(zone.get("color")), 1, cv2.LINE_AA)
    return frame


def draw_detections(frame, detections):
    """
    Vẽ bbox kèm **tâm bbox** — đó mới là điểm mà đánh giá vi phạm thực sự dùng
    (`evaluate_bbox_center_in_zone`). Với xe lớn ở gần camera, tâm bbox nằm trên
    nóc xe chứ không nằm dưới bánh, nên nhìn tâm mới biết zone có bắt được không.
    """
    height, width = frame.shape[:2]
    for det in detections:
        left, top, box_w, box_h = det["bbox"]
        x1, y1 = int(left / 100 * width), int(top / 100 * height)
        x2, y2 = int((left + box_w) / 100 * width), int((top + box_h) / 100 * height)
        color = COLOR_VIOLATION if det.get("zone_violation") else COLOR_OK

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 14, 2)

        label = f"{det['object_class']} {det['confidence']:.2f}"
        if det.get("zone_name"):
            label += f" @{det['zone_name']}"
        cv2.putText(frame, label, (x1, max(14, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    return frame


def draw_caption(frame, lines):
    y = 24
    for line in lines:
        (tw, th), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (8, y - th - 5), (12 + tw, y + 5), (0, 0, 0), -1)
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
        y += th + 12
    return frame


def sample_frames(video_path: str, count: int):
    """
    Lấy `count` frame trải đều bằng cách đọc tuần tự.

    Không seek: footage gốc là HEVC, seek tới frame không phải keyframe cho ảnh
    xám nát (xem ghi chú trong events.py).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    step = max(1, total // (count + 1))
    wanted = {step * (i + 1) for i in range(count)}

    frames, index = [], 0
    while len(frames) < count:
        ok, frame = cap.read()
        if not ok:
            break
        if index in wanted and is_frame_usable(frame):
            frames.append((index, frame.copy()))
        index += 1
    cap.release()
    return frames


def render_camera(camera_id: str, zones, pipeline, samples: int):
    video_path, _ = resolve_camera_video(camera_id)
    if not os.path.exists(video_path):
        print(f"[!] {camera_id}: không tìm thấy video {video_path}")
        return []
    if not zones:
        print(f"[!] {camera_id}: chưa có zone nào để render")

    written = []
    for order, (frame_index, frame) in enumerate(sample_frames(video_path, samples), start=1):
        detections = pipeline.process_frame(frame, zones) if pipeline else []
        draw_zones(frame, zones)
        draw_detections(frame, detections)

        violations = sum(1 for d in detections if d.get("zone_violation"))
        draw_caption(frame, [
            f"{camera_id}  frame #{frame_index}  zone={len(zones)}",
            f"detection={len(detections)}  vi pham={violations}",
        ])

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, f"{camera_id}_{order}.png")
        cv2.imwrite(out_path, frame)
        written.append(out_path)
        print(f"    frame #{frame_index}: {len(detections)} detection, {violations} vi phạm "
              f"-> {os.path.relpath(out_path, ROOT)}")
    return written


def main():
    parser = argparse.ArgumentParser(description="Render polygon zone đè lên frame thật.")
    parser.add_argument("--camera", action="append", dest="cameras",
                        help="Mã camera; lặp lại được. Mặc định: cả ba.")
    parser.add_argument("--samples", type=int, default=3, help="Số frame mỗi camera (mặc định 3).")
    parser.add_argument("--source", choices=["db", "seed"], default="db",
                        help="Lấy zone từ CSDL (mặc định) hay từ seed_area_demo.py.")
    parser.add_argument("--no-detect", action="store_true", help="Bỏ qua YOLO, chỉ vẽ polygon.")
    args = parser.parse_args()

    cameras = args.cameras or DEFAULT_CAMERAS
    loader = load_zones_from_db if args.source == "db" else load_zones_from_seed
    pipeline = None if args.no_detect else AIVisionPipeline()

    summary = {}
    for camera_id in cameras:
        zones = loader(camera_id)
        print(f"[{camera_id}] {len(zones)} zone từ {args.source}: "
              f"{', '.join(z['id'] for z in zones) or '(trống)'}")
        summary[camera_id] = render_camera(camera_id, zones, pipeline, args.samples)

    print(f"\nẢnh xác minh nằm trong {os.path.relpath(OUTPUT_DIR, ROOT)}/ — hãy mở ra xem "
          f"polygon có bám đúng làn/bãi không trước khi coi là xong.")
    print(json.dumps({k: len(v) for k, v in summary.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()

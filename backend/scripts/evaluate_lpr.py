"""Đo chất lượng LPR trên clip cổng bằng bộ biển số đã gán nhãn tay.

Vì sao cần: trước khi có script này, mỗi lần chỉnh ngưỡng hay đổi cách khoanh vùng biển
đều chỉ được đánh giá bằng cách mở UI xem có chữ hiện ra không. Không có số thì không
biết một thay đổi làm tốt lên hay tệ đi, và thực tế đã có nhiều vòng tinh chỉnh tham số
trên một footage vốn không hề chứa tấm biển nào đọc được.

Chỉ số quan trọng nhất là **recall theo lượt xe**, không phải theo frame: một lượt xe
dừng ở cổng nằm trong khung hình hàng trăm frame, chỉ cần đọc đúng một frame là lượt đó
đã được ghi nhận (các frame sau bị cooldown chặn). Recall theo frame nhìn thì thấp hơn
nhiều nhưng không phản ánh cái người trực cổng thực sự nhận được.

Chạy:
    python backend/scripts/evaluate_lpr.py
    python backend/scripts/evaluate_lpr.py --sample-fps 2 --engine easyocr
"""

import argparse
import io
import json
import os
import sys
import time
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_GROUNDTRUTH = os.path.join(
    PROJECT_ROOT, "backend", "tests", "fixtures", "gate_lpr_groundtruth.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", default=DEFAULT_GROUNDTRUTH)
    parser.add_argument("--sample-fps", type=float, default=1.0,
                        help="Số frame lấy mẫu mỗi giây video (mặc định 1)")
    parser.add_argument(
        "--engine", choices=("auto", "easyocr"), default="auto",
        help="'auto' dùng recognizer chuyên biển; 'easyocr' ép chạy nhánh dự phòng. "
             "Lưu ý khi đọc kết quả: nhánh EasyOCR chỉ biết quét dải cản va bên trong "
             "một bbox xe, nên ở chế độ quét toàn khung nó trả 0 lượt — đó là giới hạn "
             "của nhánh đó, không phải điểm số của EasyOCR trên tấm biển đã khoanh sẵn.",
    )
    parser.add_argument("--verbose", action="store_true", help="In từng lượt đọc")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    import cv2
    from backend.app.services.lpr_engine import lpr_engine

    with open(args.groundtruth, encoding="utf-8") as handle:
        groundtruth = json.load(handle)

    video_path = os.path.join(PROJECT_ROOT, groundtruth["video"])
    if not os.path.exists(video_path):
        print(f"Không tìm thấy video: {video_path}")
        return 1

    if args.engine == "easyocr":
        # Tắt đường đọc chính để đo riêng nhánh dự phòng, dùng khi so sánh hai engine.
        lpr_engine.plate_recognizer._unavailable = True

    passages = groundtruth["passages"]
    capture = cv2.VideoCapture(video_path)
    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    stride = max(1, int(round(fps / max(args.sample_fps, 0.01))))

    correct_frames = defaultdict(int)
    wrong_reads: list[tuple[float, str, str | None]] = []
    durations: list[float] = []
    frame_index = 0
    frames_read = 0

    print(f"Video   : {video_path}")
    print(f"Engine  : {'recognizer chuyên biển' if args.engine == 'auto' else 'EasyOCR (dự phòng)'}")
    print(f"Lấy mẫu : mỗi {stride} frame (~{fps / stride:.1f} lần/giây)\n")

    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frame_index += 1
        if frame_index % stride:
            continue
        frames_read += 1

        seconds = frame_index / fps
        started = time.time()
        reading = lpr_engine.read_plate(frame, None)
        durations.append((time.time() - started) * 1000.0)

        if not reading.plate_text:
            continue

        expected = next(
            (p["plate"] for p in passages
             if p["start_seconds"] <= seconds <= p["end_seconds"]),
            None,
        )
        if reading.plate_text == expected:
            correct_frames[expected] += 1
            if args.verbose:
                print(f"  OK  t={seconds:5.1f}s {reading.plate_text} "
                      f"conf={reading.confidence:.3f} ({reading.source})")
        else:
            wrong_reads.append((seconds, reading.plate_text, expected))
            if args.verbose:
                print(f"  SAI t={seconds:5.1f}s {reading.plate_text} "
                      f"(đúng ra: {expected}) conf={reading.confidence:.3f}")

    capture.release()

    recognized = sum(1 for p in passages if correct_frames[p["plate"]] > 0)
    print("Lượt xe:")
    for passage in passages:
        hits = correct_frames[passage["plate"]]
        layout = "2 dòng" if passage.get("plate_layout") == "two_line" else "1 dòng"
        status = "ĐỌC ĐƯỢC " if hits else "KHÔNG ĐỌC"
        print(f"  {status} {passage['plate']}  ({layout}, {hits} frame đúng)")

    total_reads = sum(correct_frames.values()) + len(wrong_reads)
    print(f"\nRecall theo lượt xe : {recognized}/{len(passages)}")
    print(f"Đọc sai             : {len(wrong_reads)}"
          + (f" / {total_reads} lượt đọc" if total_reads else ""))
    for seconds, got, expected in wrong_reads[:10]:
        print(f"    t={seconds:5.1f}s đọc '{got}', đúng ra '{expected}'")
    if durations:
        durations.sort()
        print(f"Thời gian mỗi frame : trung vị {durations[len(durations) // 2]:.0f}ms, "
              f"tối đa {durations[-1]:.0f}ms ({frames_read} frame)")

    # Recall dưới 100% không phải lỗi của script — trả 0 để dùng được trong CI, thông
    # tin đánh giá nằm ở phần in ra.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Chuẩn hoá video demo cho SentriAI Mini.

Nguồn quay từ đầu ghi là HEVC trong container MPEG-PS/ASF, độ phân giải 2592-2688px
và dài 10-19 phút. Có ba vấn đề:

  1. Trình duyệt không phát được MPEG-PS/ASF, nên thẻ <video> trên UI trống trơn.
  2. Seek tới frame bất kỳ trên HEVC hay trả về ảnh xám nát vì thiếu frame tham chiếu.
  3. Dung lượng và độ phân giải quá lớn so với nhu cầu demo.

Script cắt một cửa sổ 60 giây nhiều chuyển động nhất rồi mã hoá lại sang H.264
720p với keyframe mỗi giây, xử lý cả ba vấn đề cùng lúc.

Chạy từ gốc dự án:
    .venv/Scripts/python.exe backend/scripts/prepare_demo_videos.py
    .venv/Scripts/python.exe backend/scripts/prepare_demo_videos.py --scan-only
"""

import argparse
import os
import subprocess
import sys

import numpy as np

try:
    import imageio_ffmpeg
except ImportError:
    sys.exit("Thiếu imageio-ffmpeg. Cài bằng: .venv/Scripts/pip.exe install imageio-ffmpeg")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(PROJECT_ROOT, "data", "video")

CLIP_SECONDS = 60
# Số giây giải mã bỏ đi trước điểm cắt để decoder dựng lại đủ frame tham chiếu.
PREROLL_SECONDS = 8
SCAN_FPS = 2
SCAN_WIDTH, SCAN_HEIGHT = 160, 90
OUTPUT_HEIGHT = 720

# (camera_id, file nguồn, khoảng thời gian giới hạn khi dò tính bằng giây)
JOBS = [
    ("BAI-KIEM", "KiemHoa/KiemHoa-Hik (1).mp4", None),
    # Người xuất hiện trong bãi ở khoảng phút 1 đến phút 7.
    ("XUONG-AN-NINH", "KiemHoa/KiemHoa-LM06.ASF", (60, 420)),
    ("GATE-01", "Gate/Gate-In.mp4", None),
]


def scan_motion(path):
    """Giải mã ở độ phân giải thấp và trả về mức chuyển động theo từng mẫu."""
    cmd = [
        FFMPEG, "-hide_banner", "-loglevel", "error",
        "-i", path,
        "-vf", f"fps={SCAN_FPS},scale={SCAN_WIDTH}:{SCAN_HEIGHT},format=gray",
        "-f", "rawvideo", "-",
    ]
    frame_bytes = SCAN_WIDTH * SCAN_HEIGHT
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    scores = []
    previous = None
    while True:
        buf = proc.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        frame = np.frombuffer(buf, dtype=np.uint8).astype(np.int16)
        if previous is not None:
            scores.append(float(np.abs(frame - previous).mean()))
        previous = frame
    proc.stdout.close()
    proc.wait()
    return scores


def best_window(scores, limit_range=None):
    """Tìm cửa sổ CLIP_SECONDS giây có tổng chuyển động lớn nhất."""
    window = CLIP_SECONDS * SCAN_FPS
    if len(scores) <= window:
        return 0.0, float(sum(scores))

    lo, hi = 0, len(scores) - window
    if limit_range:
        lo = max(lo, int(limit_range[0] * SCAN_FPS))
        hi = min(hi, int(limit_range[1] * SCAN_FPS) - window)
        if hi <= lo:
            lo, hi = 0, len(scores) - window

    cumulative = np.concatenate([[0.0], np.cumsum(scores)])
    sums = cumulative[lo + window: hi + window + 1] - cumulative[lo: hi + 1]
    best = int(np.argmax(sums)) + lo
    return best / SCAN_FPS, float(sums.max())


def transcode(src, dst, start_seconds):
    """
    Cắt và mã hoá lại sang H.264 720p, keyframe mỗi giây.

    Seek hai tầng: -ss trước -i nhảy nhanh tới trước điểm cần lấy PREROLL giây,
    rồi -ss sau -i bỏ đúng phần preroll đó. Chỉ dùng một mình -ss trước -i thì
    vài giây đầu vẫn thiếu frame tham chiếu và phần hỏng bị mã hoá thẳng vào
    đầu ra; bỏ preroll đi thì decoder đã kịp dựng lại tham chiếu.
    """
    preroll = min(PREROLL_SECONDS, start_seconds)
    cmd = [
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start_seconds - preroll:.2f}",
        "-i", src,
        "-ss", f"{preroll:.2f}",
        "-t", str(CLIP_SECONDS),
        "-vf", f"scale=-2:{OUTPUT_HEIGHT}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        # Keyframe đều mỗi giây để seek luôn rơi vào frame giải mã được độc lập.
        "-g", "25", "-keyint_min", "25", "-sc_threshold", "0",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        dst,
    ]
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-only", action="store_true",
                        help="Chỉ dò đoạn nhiều chuyển động, không mã hoá lại")
    args = parser.parse_args()

    for camera_id, relative_src, limit_range in JOBS:
        src = os.path.join(VIDEO_DIR, relative_src)
        if not os.path.exists(src):
            print(f"[BỎ QUA] {camera_id}: không tìm thấy {relative_src}")
            continue

        print(f"[{camera_id}] đang dò chuyển động trong {relative_src} ...", flush=True)
        scores = scan_motion(src)
        if not scores:
            print(f"[LỖI] {camera_id}: không giải mã được frame nào")
            continue

        start, score = best_window(scores, limit_range)
        duration = len(scores) / SCAN_FPS
        print(f"    dài {duration/60:.1f} phút, chọn đoạn "
              f"{int(start)//60:02d}:{int(start)%60:02d} "
              f"-> {int(start+CLIP_SECONDS)//60:02d}:{int(start+CLIP_SECONDS)%60:02d} "
              f"(điểm {score:.0f})", flush=True)

        if args.scan_only:
            continue

        dst = os.path.join(VIDEO_DIR, f"{camera_id}.mp4")
        print(f"    đang mã hoá -> {os.path.basename(dst)}", flush=True)
        transcode(src, dst, start)
        size_mb = os.path.getsize(dst) / (1024 * 1024)
        print(f"    xong: {size_mb:.1f} MB", flush=True)


if __name__ == "__main__":
    main()

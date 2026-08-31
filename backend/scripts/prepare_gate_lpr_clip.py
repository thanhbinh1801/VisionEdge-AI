"""Cắt clip demo cho camera cổng GATE-01 từ footage camera biển số.

Vì sao cần script này: clip GATE-01 trước đây lấy từ camera toàn cảnh `Cvao L1,2`
(`Gate/Gate-In.mp4`), nơi xe container chỉ lộ hông và đuôi rơ-moóc — không frame nào
có mặt biển số hướng ống kính, nên LPR không thể đọc được gì dù engine chạy đúng.
Cảng có camera ANPR riêng: `Cvao-Bien-L2` trong `Gate/Gate-In3.mp4`, đặt thấp ngang
tầm cản trước, mỗi lượt xe đều lộ trọn tấm biển.

Footage nguồn dài 15.6 phút nhưng chỉ có 5 lượt xe, cách nhau 2-4 phút. Cắt một cửa
sổ liên tục 60 giây sẽ chỉ bắt được đúng một lượt, nên script ghép các đoạn quanh
từng lượt lại thành một clip dày sự kiện.

Độ phân giải xuất ra là 1080p chứ không phải 720p như các clip camera bãi. Đo trên 12
frame có biển: 2560px và 1920px cùng cho 8/12 lượt đọc đúng, 1280px rơi xuống 6/12 —
biển ở 720p chỉ còn ~125x25px, dưới ngưỡng đọc được của OCR.

Chạy:
    python backend/scripts/prepare_gate_lpr_clip.py
    python backend/scripts/prepare_gate_lpr_clip.py --dry-run
"""

import argparse
import io
import os
import subprocess
import sys

# Console Windows là cp1252: thiếu dòng này thì script chết ở câu print tiếng Việt đầu
# tiên, nguy hiểm nhất là chết sau khi đã ghi đè video nguồn của demo.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE_VIDEO = os.path.join(PROJECT_ROOT, "data", "video", "Gate", "Gate-In3.mp4")
OUTPUT_VIDEO = os.path.join(PROJECT_ROOT, "data", "video", "GATE-01.mp4")

# Năm lượt xe đo được trên Gate-In3.mp4, kèm biển số đọc được bằng mắt ở frame gốc.
# Cửa sổ bắt đầu trước lúc biển hiện rõ vài giây để có pha xe tiến vào, và kết thúc
# sau đó vài giây để pipeline kịp chạy vài lượt OCR trên cùng một tấm biển.
PASSAGES = [
    (32.0, 14.0, "16H-032.03"),
    (330.0, 14.0, "15C-054.62"),
    (482.0, 14.0, "35H-093.47"),
    (650.0, 14.0, "15H-190.62"),
    (888.0, 14.0, "15H-322.81"),
]

# Seek hai tầng: nhảy thô tới trước điểm cắt PREROLL giây rồi -ss tinh sau -i. Đặt -ss
# một tầng trước -i thì decoder chưa dựng đủ frame tham chiếu và phần nát bị mã hoá
# thẳng vào đầu ra — nguồn là HEVC nên lỗi này chắc chắn xảy ra.
PREROLL_SECONDS = 8.0


def ffmpeg_exe() -> str:
    """ffmpeg lấy từ package imageio-ffmpeg trong venv, không cài ở mức hệ điều hành."""
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def cut_segment(ffmpeg: str, start: float, duration: float, output_path: str) -> None:
    rough = max(0.0, start - PREROLL_SECONDS)
    fine = start - rough
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error",
            "-ss", f"{rough:.3f}", "-i", SOURCE_VIDEO,
            "-ss", f"{fine:.3f}", "-t", f"{duration:.3f}",
            "-vf", "scale=1920:1080",
            "-c:v", "libx264", "-preset", "medium", "-crf", "22",
            # Keyframe mỗi giây: SequentialFrameSource đọc tiến tới nhưng người xem trên
            # UI vẫn tua, và HEVC/H.264 thiếu keyframe dày thì tua ra frame nát.
            "-g", "25", "-keyint_min", "25", "-sc_threshold", "0",
            "-pix_fmt", "yuv420p", "-an",
            output_path,
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in kế hoạch cắt, không ghi file")
    args = parser.parse_args()

    if not os.path.exists(SOURCE_VIDEO):
        print(f"Không tìm thấy footage nguồn: {SOURCE_VIDEO}")
        print("Đây là video gốc của cảng, không nằm trong repo. Khôi phục vào data/video/Gate/.")
        return 1

    total = sum(duration for _start, duration, _plate in PASSAGES)
    print(f"Nguồn : {SOURCE_VIDEO}")
    print(f"Đích  : {OUTPUT_VIDEO}")
    print(f"Ghép {len(PASSAGES)} lượt xe, tổng {total:.0f} giây, 1920x1080 H.264:")
    for start, duration, plate in PASSAGES:
        print(f"  {start:6.1f}s +{duration:4.1f}s  {plate}")
    if args.dry_run:
        return 0

    ffmpeg = ffmpeg_exe()
    work_dir = os.path.join(PROJECT_ROOT, "data", "video", ".gate_segments")
    os.makedirs(work_dir, exist_ok=True)
    segments = []
    try:
        for index, (start, duration, plate) in enumerate(PASSAGES):
            segment_path = os.path.join(work_dir, f"seg{index:02d}.mp4")
            print(f"Cắt lượt {index + 1}/{len(PASSAGES)} ({plate})...", flush=True)
            cut_segment(ffmpeg, start, duration, segment_path)
            segments.append(segment_path)

        list_path = os.path.join(work_dir, "segments.txt")
        with open(list_path, "w", encoding="utf-8") as handle:
            for segment_path in segments:
                handle.write(f"file '{segment_path.replace(os.sep, '/')}'\n")

        print("Ghép các đoạn...", flush=True)
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", list_path, "-c", "copy", OUTPUT_VIDEO],
            check=True,
        )
    finally:
        for segment_path in segments:
            if os.path.exists(segment_path):
                os.remove(segment_path)
        list_file = os.path.join(work_dir, "segments.txt")
        if os.path.exists(list_file):
            os.remove(list_file)
        if os.path.isdir(work_dir) and not os.listdir(work_dir):
            os.rmdir(work_dir)

    size_mb = os.path.getsize(OUTPUT_VIDEO) / 1e6
    print(f"Xong: {OUTPUT_VIDEO} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

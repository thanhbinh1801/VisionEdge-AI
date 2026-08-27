#!/usr/bin/env python3
"""Đo baseline độ trễ/thông lượng của stream lane cho CR-006.

Chạy trước và sau khi tách inference khỏi vòng decode để có số liệu so sánh.
Không cần backend server đang chạy: script gọi thẳng vào pipeline.

    python backend/scripts/measure_stream_latency.py
    python backend/scripts/measure_stream_latency.py --camera GATE-01 --seconds 12
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.frame_extractor import resolve_video_path  # noqa: E402
from backend.app.services.video_stream import get_camera_pipeline  # noqa: E402
from backend.app.services.vision_pipeline import AIVisionPipeline  # noqa: E402


def measure_decode_only(video_path: str, seconds: float) -> dict:
    """Trần trên của video lane: tốc độ giải mã thuần, không suy luận."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được nguồn video: {video_path}")
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0

    frames = 0
    started = time.perf_counter()
    while time.perf_counter() - started < seconds:
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        frames += 1
    elapsed = time.perf_counter() - started
    cap.release()

    return {
        "source_fps": round(source_fps, 2),
        "decode_only_fps": round(frames / elapsed, 2) if elapsed else 0.0,
        "frames_decoded": frames,
    }


def measure_inference(vision_pipeline: AIVisionPipeline, video_path: str, samples: int) -> dict:
    """Chi phí suy luận trên mỗi frame, ở đúng imgsz đang cấu hình."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError(f"Không đọc được frame đầu tiên: {video_path}")

    vision_pipeline.process_frame(frame, [])  # nạp model, không tính vào số đo

    durations_ms = []
    for _ in range(samples):
        started = time.perf_counter()
        vision_pipeline.process_frame(frame, [])
        durations_ms.append((time.perf_counter() - started) * 1000.0)

    mean_ms = statistics.mean(durations_ms)
    return {
        "frame_shape": f"{frame.shape[1]}x{frame.shape[0]}",
        "inference_mean_ms": round(mean_ms, 1),
        "inference_p95_ms": round(max(durations_ms), 1) if len(durations_ms) < 20
        else round(statistics.quantiles(durations_ms, n=20)[18], 1),
        "inference_fps": round(1000.0 / mean_ms, 2) if mean_ms else 0.0,
        "samples": samples,
    }


def measure_pipeline_publish(camera_id: str, vision_pipeline: AIVisionPipeline, seconds: float) -> dict:
    """Nhịp thực tế mà CameraFramePipeline publish snapshot ra cho các lane."""
    pipeline = get_camera_pipeline(camera_id, vision_pipeline)
    first = pipeline.wait_for_snapshot(None, timeout=120.0)
    if first is None:
        raise RuntimeError(f"Pipeline không trả snapshot đầu tiên cho {camera_id}")

    last_frame_id = first.frame_id
    first_source_ts = first.source_timestamp_seconds
    gaps_ms = []
    detection_ages_ms = []
    published = 0

    started = time.perf_counter()
    previous_at = started
    while time.perf_counter() - started < seconds:
        snapshot = pipeline.wait_for_snapshot(last_frame_id, timeout=5.0)
        if snapshot is None or snapshot.frame_id == last_frame_id:
            continue
        now = time.perf_counter()
        gaps_ms.append((now - previous_at) * 1000.0)
        previous_at = now
        last_frame_id = snapshot.frame_id
        published += 1
        # Sau P1 trường này tồn tại; trước P1 thì detection luôn cùng frame nên tuổi bằng 0.
        detection_ages_ms.append(float(getattr(snapshot, "detection_age_ms", 0.0)))

    elapsed = time.perf_counter() - started
    final = pipeline.get_latest_snapshot()
    source_advanced = (final.source_timestamp_seconds - first_source_ts) if final else 0.0

    return {
        "publish_fps": round(published / elapsed, 2) if elapsed else 0.0,
        "publish_gap_mean_ms": round(statistics.mean(gaps_ms), 1) if gaps_ms else 0.0,
        "publish_gap_max_ms": round(max(gaps_ms), 1) if gaps_ms else 0.0,
        "detection_age_mean_ms": round(statistics.mean(detection_ages_ms), 1) if detection_ages_ms else 0.0,
        "detection_age_max_ms": round(max(detection_ages_ms), 1) if detection_ages_ms else 0.0,
        # < 1.0 nghĩa là pipeline chạy chậm hơn thời gian thực và độ lệch giãn ra liên tục.
        "realtime_ratio": round(source_advanced / elapsed, 3) if elapsed else 0.0,
        "frames_published": published,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", default="BAI-KIEM")
    parser.add_argument("--seconds", type=float, default=10.0, help="Thời lượng mỗi phép đo")
    parser.add_argument("--samples", type=int, default=8, help="Số lần lặp đo suy luận")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    video_path = resolve_video_path(args.camera)
    vision_pipeline = AIVisionPipeline()

    report = {
        "measured_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "camera_id": args.camera,
        "video_path": str(video_path),
        "model_weights": vision_pipeline.model_name_or_path,
        "decode": measure_decode_only(video_path, args.seconds),
        "inference": measure_inference(vision_pipeline, video_path, args.samples),
        "pipeline": measure_pipeline_publish(args.camera, vision_pipeline, args.seconds),
    }

    publish_fps = report["pipeline"]["publish_fps"]
    # Mốc so sánh là nhịp phát hình mong muốn, tức FPS của nguồn, chứ không phải
    # decode_only_fps: phép đo decode chạy không giữ nhịp nên cho ra con số vài trăm FPS
    # mà video lane không bao giờ cần đạt tới.
    target_fps = min(
        report["decode"]["source_fps"] or 0.0,
        report["decode"]["decode_only_fps"],
    )
    report["verdict"] = {
        # Video lane bị AI kéo lùi khi publish không theo kịp nhịp nguồn.
        "video_lane_capped_by_inference": publish_fps < target_fps * 0.5,
        "meets_global_ac1_fps_5": publish_fps >= 5.0,
        "drifts_behind_realtime": report["pipeline"]["realtime_ratio"] < 0.95,
        "target_fps": round(target_fps, 2),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nĐã ghi: {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

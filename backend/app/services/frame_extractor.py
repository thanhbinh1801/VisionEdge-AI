from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ExtractedFrame:
    jpeg_bytes: bytes
    source_name: str
    fps: float
    total_frames: int
    requested_frame_index: int
    actual_frame_index: int
    actual_timestamp_seconds: float


def resolve_video_path(camera_id: Optional[str] = None) -> str:
    env_video_path = os.getenv("VIDEO_PATH") or settings.VIDEO_PATH
    if env_video_path:
        candidate = Path(env_video_path).expanduser()
        resolved = candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate)
        resolved = resolved.resolve()
        if os.path.exists(resolved):
            return str(resolved)
    raise RuntimeError(f"VIDEO_PATH does not point to an existing file: {env_video_path}")


def extract_jpeg_frame(
    video_path: str,
    *,
    timestamp_seconds: float | None = None,
    frame_index: int | None = None,
) -> ExtractedFrame:
    if timestamp_seconds is not None and frame_index is not None:
        raise ValueError("Provide timestamp_seconds or frame_index, not both")
    if timestamp_seconds is not None and timestamp_seconds < 0:
        raise ValueError("timestamp_seconds must be greater than or equal to zero")
    if frame_index is not None and frame_index < 0:
        raise ValueError("frame_index must be greater than or equal to zero")

    try:
        import cv2
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError("OpenCV (cv2) is required to extract video frames.") from exc

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if frame_index is not None:
            target_frame = frame_index
        elif timestamp_seconds is not None and fps > 0:
            target_frame = int(timestamp_seconds * fps)
        else:
            # Current Zone Editor does not send a selector. Frame zero remains a
            # stable, backward-compatible preview without a hidden time seek.
            target_frame = 0
        if total_frames > 0:
            target_frame = max(0, min(target_frame, total_frames - 1))

        # Decode-forward from the source's initial keyframe. Directly seeking to
        # an HEVC dependent frame can yield corrupt or black preview frames.
        frame = None
        actual_frame_index = -1
        for decoded_index in range(target_frame + 1):
            ret, decoded_frame = cap.read()
            if not ret or decoded_frame is None:
                raise RuntimeError(
                    f"Unable to decode frame {decoded_index} from {video_path}"
                )
            frame = decoded_frame
            actual_frame_index = decoded_index

        ok, jpeg_buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise RuntimeError("Failed to encode video frame as JPEG")
        actual_timestamp = actual_frame_index / fps if fps > 0 else 0.0
        return ExtractedFrame(
            jpeg_bytes=jpeg_buf.tobytes(),
            source_name=Path(video_path).name,
            fps=float(fps),
            total_frames=total_frames,
            requested_frame_index=target_frame,
            actual_frame_index=actual_frame_index,
            actual_timestamp_seconds=actual_timestamp,
        )
    finally:
        cap.release()


def extract_jpeg_frame_bytes(video_path: str, seek_seconds: float = 1.0) -> bytes:
    """Backward-compatible byte-only wrapper for existing callers."""
    return extract_jpeg_frame(
        video_path, timestamp_seconds=seek_seconds
    ).jpeg_bytes

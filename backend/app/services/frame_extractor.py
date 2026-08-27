from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from backend.app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov")


class VideoSourceUnavailableError(RuntimeError):
    """Không tìm thấy file video nào dùng được cho camera.

    Kế thừa RuntimeError để các caller cũ (đang bắt RuntimeError) không đổi hành vi,
    nhưng lớp API có thể bắt riêng và trả 503 thay vì để FastAPI trả 500.
    """

    def __init__(self, camera_id: Optional[str], attempted: list[str]):
        self.camera_id = camera_id
        self.attempted = attempted
        super().__init__(
            f"Không tìm thấy nguồn video cho camera '{camera_id or 'unknown'}'. "
            f"VIDEO_PATH does not point to an existing file. "
            f"Đã thử: {', '.join(attempted) if attempted else '(không có ứng viên nào)'}"
        )


@dataclass(frozen=True)
class ExtractedFrame:
    jpeg_bytes: bytes
    source_name: str
    fps: float
    total_frames: int
    requested_frame_index: int
    actual_frame_index: int
    actual_timestamp_seconds: float


def _absolutize(raw_path: str) -> Path:
    """Neo đường dẫn tương đối vào gốc repo thay vì CWD (dev chạy từ backend/)."""
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def _coerce_camera_id(camera_id: Any) -> Optional[str]:
    """Ép camera_id về str hoặc None.

    Khi endpoint FastAPI được gọi trực tiếp như hàm Python thường (trong test),
    tham số mặc định là đối tượng `Query(...)` chứ không phải str. Lấy `.default`
    của nó thay vì để `camera_id.replace(...)` ném AttributeError.
    """
    if camera_id is not None and not isinstance(camera_id, str):
        camera_id = getattr(camera_id, "default", None)
        if not isinstance(camera_id, str):
            camera_id = None
    return camera_id


def _camera_env_video_path(camera_id: Optional[str]) -> Optional[str]:
    """Đọc override theo camera: VIDEO_<CAMERA_ID>_PATH (env hoặc settings)."""
    camera_id = _coerce_camera_id(camera_id)
    if not camera_id:
        return None
    attr = "VIDEO_" + camera_id.replace("-", "_").upper() + "_PATH"
    return os.getenv(attr) or getattr(settings, attr, "") or None


def _video_search_dirs() -> list[Path]:
    """Thư mục chứa video mẫu, ưu tiên VIDEOS_DIR rồi tới layout mặc định của repo."""
    dirs: list[Path] = []
    videos_dir = os.getenv("VIDEOS_DIR") or getattr(settings, "VIDEOS_DIR", "")
    if videos_dir:
        dirs.append(_absolutize(videos_dir))
    dirs.append(PROJECT_ROOT / "data" / "video")
    dirs.append(PROJECT_ROOT / "data" / "videos")
    dirs.append(PROJECT_ROOT / "backend" / "data" / "videos")

    unique: list[Path] = []
    for path in dirs:
        if path not in unique:
            unique.append(path)
    return unique


def _camera_file_stems(camera_id: str) -> list[str]:
    normalized = camera_id.strip()
    stems = [
        normalized,
        normalized.upper(),
        normalized.lower(),
        normalized.replace("-", "_"),
        normalized.replace("-", "_").upper(),
        normalized.replace("_", "-"),
        normalized.replace("_", "-").upper(),
    ]
    unique: list[str] = []
    for stem in stems:
        if stem and stem not in unique:
            unique.append(stem)
    return unique


def _scan_for_camera_video(camera_id: Optional[str], attempted: list[str]) -> Optional[str]:
    """Tìm file video theo tên camera trong các thư mục video mẫu của repo."""
    if not camera_id:
        return None
    for directory in _video_search_dirs():
        if not directory.is_dir():
            continue
        for stem in _camera_file_stems(camera_id):
            for ext in VIDEO_EXTENSIONS:
                candidate = directory / f"{stem}{ext}"
                attempted.append(str(candidate))
                if candidate.is_file():
                    return str(candidate)
    return None


def _scan_for_any_sample_video(attempted: list[str]) -> Optional[str]:
    """Fallback cuối: lấy video mẫu bất kỳ, sắp xếp theo tên để kết quả ổn định."""
    for directory in _video_search_dirs():
        if not directory.is_dir():
            continue
        attempted.append(f"{directory}/*{{{','.join(VIDEO_EXTENSIONS)}}}")
        candidates = sorted(
            entry
            for entry in directory.iterdir()
            if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS
        )
        if candidates:
            return str(candidates[0].resolve())
    return None


def resolve_video_path(camera_id: Optional[str] = None) -> str:
    """Xác định file video nguồn cho camera.

    Thứ tự ưu tiên:
    1. Override theo camera: `VIDEO_<CAMERA_ID>_PATH`.
    2. `VIDEO_PATH` dùng chung.
    3. Quét file trùng tên camera trong các thư mục video mẫu của repo.
    4. Video mẫu bất kỳ trong các thư mục đó.

    Hết cả 4 bước mới ném `VideoSourceUnavailableError` để caller trả 503 thay vì 500.
    """
    camera_id = _coerce_camera_id(camera_id)
    attempted: list[str] = []

    for raw_path in (_camera_env_video_path(camera_id), os.getenv("VIDEO_PATH") or settings.VIDEO_PATH):
        if not raw_path:
            continue
        resolved = _absolutize(raw_path)
        attempted.append(str(resolved))
        if resolved.is_file():
            return str(resolved)

    matched = _scan_for_camera_video(camera_id, attempted)
    if matched:
        return matched

    fallback = _scan_for_any_sample_video(attempted)
    if fallback:
        return fallback

    raise VideoSourceUnavailableError(camera_id, attempted)


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

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# Suy luận lại YOLO cho mỗi frame của clip là không dùng được: đo trên BAI-KIEM.mp4
# (25 fps, clip 10s = 250 frame) cho 0.219s/frame, tức +49.6s mỗi clip so với 4.05s
# khi chỉ sao chép frame. Giãn còn 5 frame một lần (5 Hz) đưa chi phí về +9.9s và
# giữ nguyên hộp giữa hai lần suy luận; với xe container/xe nâng di chuyển chậm
# trong bãi thì mắt thường gần như không phân biệt được.
DEFAULT_DETECT_STRIDE = 5

# Màu BGR cho OpenCV.
_COLOR_VIOLATION = (0, 0, 255)
_COLOR_NORMAL = (0, 200, 0)

# Trạng thái vòng đời của một file clip chứng cứ. Bản ghi sự kiện có
# `video_clip_url` ngay lúc phát hiện vi phạm, nhưng ở chế độ nền file chỉ ghi
# xong sau ~14s; client phải phân biệt được "đang render" với "không có".
CLIP_STATUS_READY = "ready"
CLIP_STATUS_PROCESSING = "processing"
CLIP_STATUS_MISSING = "missing"


class EventManager:
    """
    Event Processor, Cooldown 15s Deduplication Window (ADR-003) & 10s Ring Buffer Video Slicer.

    Truyền `vision_pipeline` để clip chứng cứ được vẽ bbox bám theo đối tượng
    (REQ-008 acceptance criteria 2). Không truyền thì clip vẫn cắt như cũ, không
    bbox và không tốn suy luận — đây là mặc định để giữ nguyên hành vi hiện có.
    """

    def __init__(
        self,
        cooldown_seconds: int = 15,
        clips_dir: str = "./data/clips",
        vision_pipeline: Any | None = None,
        detect_stride: int = DEFAULT_DETECT_STRIDE,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.clips_dir = clips_dir
        self.vision_pipeline = vision_pipeline
        self.detect_stride = max(1, int(detect_stride))
        self._cooldown_cache: dict[str, float] = {}  # event_key -> last_triggered_timestamp
        self._pending_clips: dict[str, threading.Thread] = {}
        self._pending_lock = threading.Lock()
        os.makedirs(self.clips_dir, exist_ok=True)

    def generate_event_key(self, camera_id: str, zone_id: str | None, object_class: str) -> str:
        return f"{camera_id}:{zone_id or 'NO_ZONE'}:{object_class}"

    def is_duplicate(self, camera_id: str, zone_id: str | None, object_class: str) -> bool:
        """
        Checks if event is within cooldown 15s sliding window cache.
        Returns True if event is DUPLICATE (should be suppressed).
        """
        key = self.generate_event_key(camera_id, zone_id, object_class)
        now = time.time()
        
        if key in self._cooldown_cache:
            elapsed = now - self._cooldown_cache[key]
            if elapsed < self.cooldown_seconds:
                logger.debug(f"Event {key} suppressed by Cooldown Cache ({elapsed:.1f}s < {self.cooldown_seconds}s)")
                return True
                
        self._cooldown_cache[key] = now
        return False

    def slice_10s_ring_buffer_clip(
        self,
        camera_id: str,
        timestamp: float | None = None,
        *,
        source_video_path: str | None = None,
        source_timestamp_seconds: float | None = None,
        duration_seconds: float = 10.0,
        background: bool = False,
    ) -> str:
        """
        Extracts 10s MP4 evidence video clip around event timestamp and returns relative URL.

        When a source video is available, the clip is centered on
        source_timestamp_seconds and clamped to the source bounds. Near the start
        or end of the source, the clip is shorter only when the source itself
        cannot provide duration_seconds of frames.

        `background=True` trả URL ngay và ghi file trong thread nền. Dùng khi vẽ
        bbox, vì suy luận theo frame làm thời gian sinh clip vượt xa chu kỳ poll
        của client. Caller phải chấp nhận file chưa tồn tại ngay sau khi gọi —
        dùng `wait_for_pending_clips()` khi cần chắc chắn đã ghi xong.
        """
        ts = int(timestamp or time.time())
        filename = f"clip_{camera_id}_{ts}.mp4"
        filepath = os.path.join(self.clips_dir, filename)

        if not os.path.exists(filepath):
            if not source_video_path:
                from app.services.frame_extractor import resolve_video_path

                source_video_path = resolve_video_path(camera_id)
            kwargs = {
                "source_video_path": source_video_path,
                "destination_path": filepath,
                "event_timestamp_seconds": source_timestamp_seconds or 0.0,
                "duration_seconds": duration_seconds,
            }
            if background:
                self._spawn_clip_writer(filepath, kwargs)
            else:
                self._write_mp4_clip(**kwargs)

        logger.info(f"Sliced 10s evidence video clip: {filepath}")
        return f"/media/clips/{filename}"

    def _spawn_clip_writer(self, filepath: str, kwargs: dict) -> None:
        """Ghi clip trong thread nền, mỗi file chỉ một thread."""
        with self._pending_lock:
            existing = self._pending_clips.get(filepath)
            if existing is not None and existing.is_alive():
                return

            def run() -> None:
                try:
                    self._write_mp4_clip(**kwargs)
                except Exception:
                    # Nuốt ở đây thì clip hỏng im lặng, nên ghi log đầy đủ. Không
                    # ném tiếp vì thread nền không có ai bắt.
                    logger.exception("Không sinh được clip chứng cứ: %s", filepath)
                finally:
                    with self._pending_lock:
                        self._pending_clips.pop(filepath, None)

            thread = threading.Thread(target=run, name=f"clip-writer-{os.path.basename(filepath)}", daemon=True)
            self._pending_clips[filepath] = thread
            thread.start()

    def wait_for_pending_clips(self, timeout: float = 120.0) -> bool:
        """Chờ mọi clip nền ghi xong. Trả False nếu hết thời gian mà còn thread sống."""
        deadline = time.monotonic() + timeout
        while True:
            with self._pending_lock:
                threads = [t for t in self._pending_clips.values() if t.is_alive()]
            if not threads:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            threads[0].join(timeout=min(remaining, 0.5))

    def resolve_clip_path(self, video_clip_url: str | None) -> str | None:
        """
        Đổi `/media/clips/<tên file>` thành đường dẫn thật trong `clips_dir`.

        Chỉ lấy phần tên file: URL đi vào đây có thể đến từ bản ghi CSDL cũ hoặc
        từ tham số client, nên không được để `../` trỏ ra ngoài thư mục clip.
        """
        if not video_clip_url:
            return None
        filename = os.path.basename(str(video_clip_url).split("?", 1)[0])
        if not filename:
            return None
        return os.path.join(self.clips_dir, filename)

    def get_clip_status(self, video_clip_url: str | None) -> str:
        """
        Trạng thái file clip chứng cứ ứng với `video_clip_url`.

        - `processing`: thread nền đang ghi, client phải chờ và thử lại.
        - `ready`: file đã đóng và có nội dung, tải về được.
        - `missing`: không có URL, hoặc file không tồn tại và cũng không ai đang ghi.

        `VideoWriter` tạo file ngay khi mở nên riêng `os.path.exists` không đủ để
        kết luận đã xong; phải loại các file còn thread nền đang giữ.

        Giới hạn đã biết: sổ theo dõi thread nằm trong bộ nhớ tiến trình, nên clip
        ghi dở lúc backend tắt đột ngột sẽ báo `ready` sau khi khởi động lại.
        """
        filepath = self.resolve_clip_path(video_clip_url)
        if filepath is None:
            return CLIP_STATUS_MISSING

        with self._pending_lock:
            thread = self._pending_clips.get(filepath)
        if thread is not None and thread.is_alive():
            return CLIP_STATUS_PROCESSING

        try:
            if os.path.getsize(filepath) > 0:
                return CLIP_STATUS_READY
        except OSError:
            pass
        return CLIP_STATUS_MISSING

    def _write_mp4_clip(
        self,
        *,
        source_video_path: str,
        destination_path: str,
        event_timestamp_seconds: float,
        duration_seconds: float,
    ) -> None:
        try:
            import cv2
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("OpenCV (cv2) is required to create evidence clips.") from exc

        cap = cv2.VideoCapture(source_video_path)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"Unable to open video source for evidence clip: {source_video_path}")

        writer = None
        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
                raise RuntimeError(f"Video source has invalid metadata: {source_video_path}")

            total_duration = frame_count / fps
            clip_duration = min(max(duration_seconds, 0.1), total_duration)
            start_seconds = event_timestamp_seconds - (clip_duration / 2.0)
            start_seconds = max(0.0, min(start_seconds, max(0.0, total_duration - clip_duration)))
            start_frame = max(0, min(int(start_seconds * fps), frame_count - 1))
            frames_to_write = max(1, min(round(clip_duration * fps), frame_count - start_frame))

            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(destination_path, fourcc, fps, (width, height))
            if not writer.isOpened():
                raise RuntimeError(f"Unable to open MP4 writer for evidence clip: {destination_path}")

            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            written = 0
            detections: list[dict] = []
            while written < frames_to_write:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                if self.vision_pipeline is not None:
                    # Chỉ suy luận mỗi `detect_stride` frame; giữa hai lần thì giữ
                    # nguyên hộp cũ. Xem DEFAULT_DETECT_STRIDE để biết số đo.
                    if written % self.detect_stride == 0:
                        detections = self._detect_for_clip(frame)
                    self._draw_detections(cv2, frame, detections)
                writer.write(frame)
                written += 1

            if written == 0:
                raise RuntimeError(f"Unable to decode frames for evidence clip: {source_video_path}")
        finally:
            cap.release()
            if writer is not None:
                writer.release()

    def _detect_for_clip(self, frame) -> list[dict]:
        """
        Chạy suy luận cho một frame của clip.

        Lỗi suy luận không được làm hỏng cả clip: thà trả clip không có hộp còn
        hơn ném lỗi và mất luôn bằng chứng.
        """
        try:
            return self.vision_pipeline.process_frame(frame) or []
        except Exception:
            logger.exception("Suy luận thất bại khi vẽ bbox cho clip, bỏ qua frame này")
            return []

    @staticmethod
    def _draw_detections(cv2, frame, detections: list[dict]) -> None:
        """
        Vẽ bbox và nhãn tiếng Việt lên frame.

        `bbox` từ vision pipeline là phần trăm [left, top, width, height] theo
        khung hình (xem quy ước trong vision_pipeline.process_frame), nên phải
        quy đổi sang pixel trước khi vẽ.
        """
        if not detections:
            return
        height, width = frame.shape[:2]
        for det in detections:
            bbox = det.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            x = int((float(bbox[0]) / 100.0) * width)
            y = int((float(bbox[1]) / 100.0) * height)
            w = int((float(bbox[2]) / 100.0) * width)
            h = int((float(bbox[3]) / 100.0) * height)
            if w <= 0 or h <= 0:
                continue

            color = _COLOR_VIOLATION if det.get("zone_violation") else _COLOR_NORMAL
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

            label = str(det.get("vietnamese_name") or det.get("object_class") or "")
            confidence = det.get("confidence")
            if confidence is not None:
                label = f"{label} {float(confidence):.2f}".strip()
            if label:
                cv2.putText(
                    frame,
                    label,
                    (x, max(14, y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

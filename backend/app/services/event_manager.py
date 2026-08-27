import logging
import os
import time

logger = logging.getLogger(__name__)

class EventManager:
    """
    Event Processor, Cooldown 15s Deduplication Window (ADR-003) & 10s Ring Buffer Video Slicer.
    """

    def __init__(self, cooldown_seconds: int = 15, clips_dir: str = "./data/clips"):
        self.cooldown_seconds = cooldown_seconds
        self.clips_dir = clips_dir
        self._cooldown_cache: dict[str, float] = {}  # event_key -> last_triggered_timestamp
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
    ) -> str:
        """
        Extracts 10s MP4 evidence video clip around event timestamp and returns relative URL.

        When a source video is available, the clip is centered on
        source_timestamp_seconds and clamped to the source bounds. Near the start
        or end of the source, the clip is shorter only when the source itself
        cannot provide duration_seconds of frames.
        """
        ts = int(timestamp or time.time())
        filename = f"clip_{camera_id}_{ts}.mp4"
        filepath = os.path.join(self.clips_dir, filename)
        
        if not os.path.exists(filepath):
            if not source_video_path:
                from backend.app.services.frame_extractor import resolve_video_path

                source_video_path = resolve_video_path(camera_id)
            self._write_mp4_clip(
                source_video_path=source_video_path,
                destination_path=filepath,
                event_timestamp_seconds=source_timestamp_seconds or 0.0,
                duration_seconds=duration_seconds,
            )
                
        logger.info(f"Sliced 10s evidence video clip: {filepath}")
        return f"/media/clips/{filename}"

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
            while written < frames_to_write:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                writer.write(frame)
                written += 1

            if written == 0:
                raise RuntimeError(f"Unable to decode frames for evidence clip: {source_video_path}")
        finally:
            cap.release()
            if writer is not None:
                writer.release()

        # Post-process clip with FFmpeg to H.264 (yuv420p + faststart) for Telegram & Browser player compatibility
        if os.path.exists(destination_path):
            try:
                import subprocess
                import imageio_ffmpeg
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                h264_tmp_path = destination_path + ".h264.mp4"
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-i", destination_path,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    h264_tmp_path,
                ]
                res = subprocess.run(cmd, capture_output=True, timeout=15)
                if res.returncode == 0 and os.path.exists(h264_tmp_path) and os.path.getsize(h264_tmp_path) > 0:
                    os.replace(h264_tmp_path, destination_path)
                elif os.path.exists(h264_tmp_path):
                    os.remove(h264_tmp_path)
            except Exception as exc:
                logger.warning(f"FFmpeg H.264 transcoding skipped for {destination_path}: {exc}")

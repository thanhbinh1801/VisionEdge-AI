import logging
import os
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.services.frame_extractor import resolve_video_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessedFrameSnapshot:
    """One immutable identity shared by pixels and their detection metadata."""

    frame_id: int
    captured_at: str
    frame: Any
    detections: tuple[dict[str, Any], ...]
    pipeline_latency_ms: float
    stream_status: str = "online"


class CameraFramePipeline:
    """Stateful per-camera decode -> inference -> zone-evaluation pipeline."""

    def __init__(
        self,
        camera_id: str,
        video_path: str,
        vision_pipeline: Any,
        target_fps: float | None = None,
        inference_threshold: float = 0.35,
    ):
        self.camera_id = camera_id
        self.video_path = video_path
        self.vision_pipeline = vision_pipeline
        self.target_fps = target_fps
        self.inference_threshold = inference_threshold
        self._condition = threading.Condition()
        self._zones: list[dict[str, Any]] = []
        self._zone_version = 0
        self._snapshot: ProcessedFrameSnapshot | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._error: Exception | None = None

    def update_zones(self, zones: list[dict[str, Any]], zone_version: int | None = None) -> None:
        with self._condition:
            self._zones = [dict(zone) for zone in zones]
            if zone_version is not None:
                self._zone_version = zone_version

    def start(self) -> None:
        with self._condition:
            if self._running:
                return
            self._running = True
            self._error = None
            self._thread = threading.Thread(
                target=self._run,
                name=f"camera-pipeline-{self.camera_id}",
                daemon=True,
            )
            self._thread.start()

    def get_latest_snapshot(self, timeout: float = 2.0) -> ProcessedFrameSnapshot | None:
        return self.wait_for_snapshot(after_frame_id=None, timeout=timeout)

    def wait_for_snapshot(
        self, after_frame_id: int | None, timeout: float = 2.0
    ) -> ProcessedFrameSnapshot | None:
        self.start()
        deadline = time.monotonic() + timeout
        with self._condition:
            while (
                self._error is None
                and self._running
                and (
                    self._snapshot is None
                    or (after_frame_id is not None and self._snapshot.frame_id <= after_frame_id)
                )
            ):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            if self._error is not None:
                raise RuntimeError(f"Camera pipeline failed: {self.camera_id}") from self._error
            return self._snapshot

    def stop(self) -> None:
        with self._condition:
            self._running = False
            self._condition.notify_all()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        cap = None
        try:
            import cv2

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Unable to open video source: {self.video_path}")
            source_fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
            delay = 1.0 / max(self.target_fps or source_fps, 1.0)
            frame_id = 0
            while self._running and cap.isOpened():
                started_at = time.monotonic()
                ok, frame = cap.read()
                if not ok or frame is None:
                    # This is the only permitted seek: restart a completed demo file.
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        raise RuntimeError(f"Unable to decode video source: {self.video_path}")

                with self._condition:
                    zones = [dict(zone) for zone in self._zones]
                detections = self.vision_pipeline.process_frame(
                    frame, zones, conf_threshold=self.inference_threshold
                )
                frame_id += 1
                snapshot = ProcessedFrameSnapshot(
                    frame_id=frame_id,
                    captured_at=datetime.now(timezone.utc).isoformat(),
                    frame=frame,
                    detections=tuple(dict(item) for item in detections),
                    pipeline_latency_ms=(time.monotonic() - started_at) * 1000.0,
                )
                with self._condition:
                    self._snapshot = snapshot
                    self._condition.notify_all()
                time.sleep(max(0.0, delay - (time.monotonic() - started_at)))
        except Exception as exc:
            logger.exception("Camera pipeline stopped for %s", self.camera_id)
            with self._condition:
                self._error = exc
                self._condition.notify_all()
        finally:
            if cap is not None:
                cap.release()
            with self._condition:
                self._running = False
                self._condition.notify_all()


_camera_pipeline_lock = threading.Lock()
_camera_pipelines: dict[tuple[str, str], CameraFramePipeline] = {}


def get_camera_pipeline(
    camera_id: str, vision_pipeline: Any, video_path: str | None = None
) -> CameraFramePipeline:
    resolved_path = os.path.abspath(video_path or resolve_video_path(camera_id))
    key = (camera_id, resolved_path)
    with _camera_pipeline_lock:
        pipeline = _camera_pipelines.get(key)
        if pipeline is None:
            pipeline = CameraFramePipeline(camera_id, resolved_path, vision_pipeline)
            _camera_pipelines[key] = pipeline
        return pipeline


class LatestFrameProvider:
    """Continuously decode a source and expose its latest complete frame."""

    def __init__(self, video_path: str, target_fps: float | None = None):
        self.video_path = video_path
        self.target_fps = target_fps
        self._condition = threading.Condition()
        self._frame: Any | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._error: Exception | None = None

    def start(self) -> None:
        with self._condition:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._decode_loop,
                name=f"video-frame-provider-{os.path.basename(self.video_path)}",
                daemon=True,
            )
            self._thread.start()

    def get_latest_frame(self, timeout: float = 2.0) -> Any | None:
        self.start()
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._frame is None and self._error is None and self._running:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            if self._error is not None:
                raise RuntimeError(f"Unable to decode video source: {self.video_path}") from self._error
            return self._frame.copy() if hasattr(self._frame, "copy") else self._frame

    def stop(self) -> None:
        with self._condition:
            self._running = False
            self._condition.notify_all()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)

    def _decode_loop(self) -> None:
        cap = None
        try:
            import cv2

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Unable to open video source: {self.video_path}")

            source_fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
            decode_fps = self.target_fps or source_fps
            delay = 1.0 / max(decode_fps, 1.0)

            while self._running and cap.isOpened():
                started_at = time.monotonic()
                ret, frame = cap.read()
                if not ret or frame is None:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        raise RuntimeError(f"Unable to decode video source: {self.video_path}")

                with self._condition:
                    self._frame = frame
                    self._condition.notify_all()

                time.sleep(max(0.0, delay - (time.monotonic() - started_at)))
        except Exception as exc:
            logger.exception("Frame provider stopped for %s", self.video_path)
            with self._condition:
                self._error = exc
                self._condition.notify_all()
        finally:
            if cap is not None:
                cap.release()
            with self._condition:
                self._running = False
                self._condition.notify_all()


_provider_lock = threading.Lock()
_frame_providers: dict[str, LatestFrameProvider] = {}


def get_latest_frame_provider(video_path: str) -> LatestFrameProvider:
    """Return the single sequential decoder owned by a resolved video source."""
    normalized_path = os.path.abspath(video_path)
    with _provider_lock:
        provider = _frame_providers.get(normalized_path)
        if provider is None:
            provider = LatestFrameProvider(normalized_path)
            _frame_providers[normalized_path] = provider
        return provider

class VideoStreamService:
    """
    Ingestion Stream Loop Service (OpenCV VideoCapture RTSP / MP4 file stream reader).
    Supports infinite looping for 2 Area Zone Monitoring streams (BAI_KIEM 10s & XUONG_AN_NINH 4m32s).
    """

    def __init__(self, camera_id: str, video_path: str | None = None, target_fps: float = 15.0):
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.video_path = self._resolve_video_path(camera_id, video_path)
        self.is_running = False

    def _resolve_video_path(self, camera_id: str, custom_path: str | None) -> str:
        if custom_path and os.path.exists(custom_path):
            return custom_path
        return resolve_video_path(camera_id)

    def get_frame_generator(self) -> Generator[Any | None, None, None]:
        """
        Yields frames at target_fps with automatic loop seek(0) on end-of-file.
        """
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV (cv2) not available. VideoStreamService operating in fallback mode.")
            while self.is_running:
                yield None
                time.sleep(1.0 / self.target_fps)
            return

        if not os.path.exists(self.video_path):
            raise RuntimeError(f"Video file not found at {self.video_path}")

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"Unable to open video source: {self.video_path}")

        delay = 1.0 / self.target_fps
        self.is_running = True
        logger.info(f"Started VideoStreamService for camera {self.camera_id} from {self.video_path} @ {self.target_fps} FPS")

        try:
            while self.is_running and cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    # Loop demo files only after EOF. Sequential decoding keeps the
                    # HEVC reference-picture buffer intact between emitted frames.
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        logger.warning("Unable to decode video after EOF reset: %s", self.video_path)
                        break

                yield frame
                time.sleep(delay)
        finally:
            self.is_running = False
            cap.release()
            logger.info(f"Stopped VideoStreamService for camera {self.camera_id}")

    def stop(self):
        self.is_running = False

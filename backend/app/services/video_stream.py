import os
import time
import logging
from typing import Generator, Optional, Any

logger = logging.getLogger(__name__)

class VideoStreamService:
    """
    Ingestion Stream Loop Service (OpenCV VideoCapture RTSP / MP4 file stream reader).
    Supports infinite looping for 2 Area Zone Monitoring streams (BAI_KIEM 10s & XUONG_AN_NINH 4m32s).
    """

    def __init__(self, camera_id: str, video_path: str = None, target_fps: float = 15.0):
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.video_path = self._resolve_video_path(camera_id, video_path)
        self.is_running = False

    def _resolve_video_path(self, camera_id: str, custom_path: Optional[str]) -> str:
        if custom_path and os.path.exists(custom_path):
            return custom_path

        possible_paths = [
            f"backend/data/videos/{camera_id}.mp4",
            f"backend/data/videos/{camera_id.replace('-', '_')}.mp4",
            f"backend/data/videos/{camera_id.replace('_', '-')}.mp4",
            f"data/videos/{camera_id}.mp4",
            f"data/videos/{camera_id.replace('-', '_')}.mp4",
        ]

        if camera_id == "BAI-KIEM" or camera_id == "BAI_KIEM":
            possible_paths.insert(0, "backend/data/videos/BAI_KIEM.mp4")
        elif camera_id == "XUONG-AN-NINH" or camera_id == "XUONG_AN_NINH":
            possible_paths.insert(0, "backend/data/videos/XUONG_AN_NINH.mp4")

        for p in possible_paths:
            if os.path.exists(p):
                return p

        return custom_path or f"backend/data/videos/{camera_id}.mp4"

    def get_frame_generator(self) -> Generator[Optional[Any], None, None]:
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
            logger.warning(f"Video file not found at {self.video_path}. Creating fallback stream.")
            while self.is_running:
                yield None
                time.sleep(1.0 / self.target_fps)
            return

        cap = cv2.VideoCapture(self.video_path)
        delay = 1.0 / self.target_fps

        self.is_running = True
        logger.info(f"Started VideoStreamService for camera {self.camera_id} from {self.video_path} @ {self.target_fps} FPS")

        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # Infinite Loop Seek(0) for demo videos
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            yield frame
            time.sleep(delay)

        cap.release()
        logger.info(f"Stopped VideoStreamService for camera {self.camera_id}")

    def stop(self):
        self.is_running = False

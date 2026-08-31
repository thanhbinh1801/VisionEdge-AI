"""Đồng thuận nhiều frame trước khi công nhận một biển số (TASK-007/BUG-003).

Vì sao cần: recognizer đọc đúng ở phần lớn frame nhưng vẫn sai ở một vài frame lẻ, và
**sai với confidence cao**. Đo trên clip cổng, chiếc `15H-032.03` — biển vuông hai dòng
bị đồng hồ camera in đè lên dòng trên — sinh ra bốn biến thể ma:

    15H-032.03  đọc đúng   23 lần   confidence 0.983 - 1.000
    55H-032.03  sai         1 lần   confidence 0.715
    16H-032.03  sai         1 lần   confidence 0.951
    11H-032.23  sai         1 lần   confidence 0.739
    11H-032.03  sai         1 lần   confidence 0.978

Mỗi biến thể đó được ghi vào bảng events như một chiếc xe chưa từng thấy, tức một lượt
qua cổng không có thật.

Vì sao không siết ngưỡng confidence thay thế: hai lần sai đạt 0.951 và 0.978, nằm lọt
giữa dải của các lần đọc đúng. Không có ngưỡng nào tách được chúng mà không đồng thời
giết cả biển thật. Thứ phân biệt hai nhóm không phải độ tự tin, mà là **số lần lặp
lại**: biển thật xuất hiện hàng chục lần, biển ma đúng một lần.

Đây cũng là cách ANPR công nghiệp làm: đọc liên tục rồi lấy kết quả đồng thuận, thay vì
tin vào một khung hình đơn lẻ.
"""

import logging
import threading
import time
from collections import deque

logger = logging.getLogger(__name__)

# Dọn các biển đã lâu không xuất hiện, để bảng đếm không phình theo thời gian chạy.
_PRUNE_EVERY_SECONDS = 300.0


class PlateVoteTracker:
    """Đếm số lần một biển số được đọc ra trong một cửa sổ thời gian trượt."""

    def __init__(self, required_reads: int = 3, window_seconds: float = 20.0):
        self.required_reads = required_reads
        self.window_seconds = window_seconds
        self._reads: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()
        self._last_prune = time.monotonic()

    def record(
        self,
        camera_id: str,
        plate_text: str,
        *,
        required_reads: int | None = None,
        window_seconds: float | None = None,
    ) -> bool:
        """Ghi nhận một lượt đọc. Trả True khi biển này đã đủ số lần đồng thuận.

        Ngưỡng truyền vào được ưu tiên hơn giá trị khởi tạo, để chỗ gọi lấy cấu hình
        đang hiệu lực thay vì giá trị đóng băng lúc import module.
        """
        needed = self.required_reads if required_reads is None else required_reads
        window = self.window_seconds if window_seconds is None else window_seconds

        # Ngưỡng <= 1 nghĩa là tắt cơ chế: một lượt đọc là đủ.
        if needed <= 1:
            return True

        now = time.monotonic()
        key = (camera_id, plate_text)
        with self._lock:
            timestamps = self._reads.setdefault(key, deque())
            timestamps.append(now)
            while timestamps and now - timestamps[0] > window:
                timestamps.popleft()
            count = len(timestamps)
            self._prune_locked(now, window)

        if count < needed:
            logger.debug(
                "Biển %s mới đọc được %d/%d lần trong %.0fs, chờ thêm bằng chứng",
                plate_text, count, needed, window,
            )
            return False
        return True

    def _prune_locked(self, now: float, window: float) -> None:
        """Xoá các biển không còn lượt đọc nào trong cửa sổ. Gọi khi đang giữ lock."""
        if now - self._last_prune < _PRUNE_EVERY_SECONDS:
            return
        self._last_prune = now
        stale = [
            key for key, stamps in self._reads.items()
            if not stamps or now - stamps[-1] > window
        ]
        for key in stale:
            del self._reads[key]

    def reset(self) -> None:
        """Xoá toàn bộ phiếu đã đếm. Dùng trong test để các bài không ảnh hưởng nhau."""
        with self._lock:
            self._reads.clear()


plate_vote_tracker = PlateVoteTracker()

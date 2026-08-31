"""Định vị tấm biển số trong khung hình camera cổng.

Thay cho cách cũ trong `lpr_engine.find_plate_candidates()`: lọc cạnh Canny rồi giữ
contour có tỉ lệ 4.3:1 và nền sáng. Cách đó dò *hình chữ nhật sáng*, mà một khung hình
cổng có hàng chục thứ như vậy — mảng cản va, thành thùng, vạch sơn, tấm phản quang —
nên phần lớn ứng viên trả về là rác, và tấm biển thật lại thường trượt vì viền của nó
đứt nét ở cự ly xa.

Ở đây dò *màu*: biển số xe kinh doanh vận tải Việt Nam nền vàng nghệ, chữ đen. Đo trên
clip cổng, mask HSV (15-40, 80-255, 80-255) kèm ràng buộc tỉ lệ và độ lấp đầy khoanh
đúng tấm biển ở 12/13 frame có biển, so với 5/13 của cách cũ.

Vẫn có nhánh biển trắng cho xe cá nhân, nhưng đặt sau nhánh vàng: nền trắng trùng màu
với vô số bề mặt kim loại sơn sáng ở cổng, nên nó chỉ chạy khi nhánh vàng không tìm
được gì.
"""

import logging
from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple

logger = logging.getLogger(__name__)

# Biển vàng: nền vàng nghệ bão hoà cao. Ngưỡng dưới của S và V để 85 chứ không cao hơn
# vì biển trong bóng cột cổng tụt xuống quanh 95-110.
YELLOW_HSV_LOWER = (15, 80, 80)
YELLOW_HSV_UPPER = (40, 255, 255)

# Biển trắng: bão hoà thấp, sáng cao.
WHITE_HSV_LOWER = (0, 0, 165)
WHITE_HSV_UPPER = (180, 45, 255)

# Tỉ lệ khung biển Việt Nam: biển dài 1 dòng ~470x110mm (4.3:1), biển vuông 2 dòng
# ~280x200mm (1.4:1). Nới hai đầu cho biến dạng phối cảnh khi xe đi chéo.
PLATE_ASPECT_RANGE = (1.05, 5.5)

# Tấm biển nhỏ hơn ngần này thì recognizer không còn nét chữ để đọc. Đo trên clip cổng
# 1080p: biển đọc được nhỏ nhất là 124x37px, biển ở cự ly dừng bốt khoảng 260x85px.
MIN_PLATE_WIDTH_PX = 38
MIN_PLATE_HEIGHT_PX = 16

# Vùng màu chiếm hơn 1/4 chiều khung hình là mảng sơn hoặc thành xe, không phải biển.
MAX_PLATE_WIDTH_RATIO = 0.25
MAX_PLATE_HEIGHT_RATIO = 0.25

# Tấm biển là hình chữ nhật đặc: contour của nó lấp gần trọn bounding box. Vạch kẻ
# đường vàng-đen hình mũi tên có cùng màu và cùng tỉ lệ nhưng chỉ lấp ~0.4-0.5, nên
# ngưỡng này là thứ tách biển khỏi vạch sơn — bỏ nó ra là mọi frame đều đầy ứng viên.
MIN_FILL_RATIO = 0.60

# Nới mép khi cắt: contour bám sát viền sơn và cắt cụt ký tự ngoài cùng.
CROP_PADDING_PX = 6


@dataclass(frozen=True)
class PlateRegion:
    """Một vùng nghi là biển số: ảnh đã cắt kèm toạ độ tuyệt đối trong khung hình."""

    image: Any
    rect: Tuple[int, int, int, int]
    color: str
    score: float


def _regions_for_mask(image_matrix, mask, color: str) -> List[PlateRegion]:
    import cv2

    height, width = mask.shape[:2]
    regions: List[PlateRegion] = []
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < MIN_PLATE_WIDTH_PX or h < MIN_PLATE_HEIGHT_PX:
            continue
        if w > width * MAX_PLATE_WIDTH_RATIO or h > height * MAX_PLATE_HEIGHT_RATIO:
            continue
        if not PLATE_ASPECT_RANGE[0] <= w / float(h) <= PLATE_ASPECT_RANGE[1]:
            continue
        fill_ratio = cv2.contourArea(contour) / float(w * h)
        if fill_ratio < MIN_FILL_RATIO:
            continue

        x0 = max(0, x - CROP_PADDING_PX)
        y0 = max(0, y - CROP_PADDING_PX)
        x1 = min(width, x + w + CROP_PADDING_PX)
        y1 = min(height, y + h + CROP_PADDING_PX)
        crop = image_matrix[y0:y1, x0:x1]
        if getattr(crop, "size", 0) == 0:
            continue
        # Biển to hơn thì đọc chắc hơn, và độ lấp đầy cao là dấu hiệu tấm biển thật.
        regions.append(PlateRegion(crop, (x0, y0, x1 - x0, y1 - y0), color, fill_ratio * w))
    return regions


def find_plate_regions(image_matrix, max_regions: int = 3) -> List[PlateRegion]:
    """Các vùng nghi là biển số trong ảnh, xếp theo điểm khả dĩ giảm dần."""
    import cv2
    import numpy as np

    if image_matrix is None or getattr(image_matrix, "size", 0) == 0:
        return []
    if getattr(image_matrix, "ndim", 2) != 3:
        return []

    hsv = cv2.cvtColor(image_matrix, cv2.COLOR_BGR2HSV)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))

    yellow = cv2.inRange(hsv, np.array(YELLOW_HSV_LOWER), np.array(YELLOW_HSV_UPPER))
    yellow = cv2.morphologyEx(yellow, cv2.MORPH_CLOSE, close_kernel)
    regions = _regions_for_mask(image_matrix, yellow, "yellow")

    if not regions:
        white = cv2.inRange(hsv, np.array(WHITE_HSV_LOWER), np.array(WHITE_HSV_UPPER))
        white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, close_kernel)
        regions = _regions_for_mask(image_matrix, white, "white")

    regions.sort(key=lambda region: region.score, reverse=True)
    return regions[:max_regions]


def crop_bbox(frame_matrix, bbox: Sequence[float] | None):
    """Cắt BBox phần trăm [x, y, w, h] (0..100) khỏi khung hình."""
    if frame_matrix is None or bbox is None or len(bbox) != 4:
        return None

    height, width = frame_matrix.shape[:2]
    left_pct, top_pct, width_pct, height_pct = [float(v) for v in bbox]
    if width_pct <= 0 or height_pct <= 0:
        return None

    left = max(0, min(int(round(left_pct / 100.0 * width)), width - 1))
    top = max(0, min(int(round(top_pct / 100.0 * height)), height - 1))
    right = max(left + 1, min(int(round((left_pct + width_pct) / 100.0 * width)), width))
    bottom = max(top + 1, min(int(round((top_pct + height_pct) / 100.0 * height)), height))

    crop = frame_matrix[top:bottom, left:right]
    if getattr(crop, "size", 0) == 0:
        return None
    return crop

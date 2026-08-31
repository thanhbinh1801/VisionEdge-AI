"""LPR OCR Engine cho camera cổng GATE-01 (REQ-001, TASK-007/BUG-002).

Tách riêng khỏi vision_pipeline.py vì hai thứ có vòng đời khác nhau: YOLO-World nạp
ngay lúc khởi động cho cả 3 camera, còn OCR chỉ cần cho đúng một camera cổng. Nạp
model ở __init__ sẽ kéo torch/onnxruntime vào mọi tiến trình, kể cả khi người dùng chỉ
mở tab giám sát khu vực — nên mọi reader ở đây đều lazy.

Có hai đường đọc, thử theo thứ tự:

1. **Định vị biển bằng màu + recognizer chuyên biển số** (`plate_detector` +
   fast-plate-ocr). Đây là đường chính. Đo trên 13 frame có biển của clip cổng:
   12/13 đọc đúng, 138ms mỗi frame.
2. **EasyOCR + heuristic Canny** — đường cũ, giữ làm dự phòng cho trường hợp
   fast-plate-ocr không cài được. Cùng bộ 13 frame: 5/13 đúng, và trượt cả hai biển
   vuông 2 dòng vì EasyOCR trả mỗi dòng thành một token rời.

Hai engine tổng quát khác đã đo và bị loại, đừng thử lại mà không có số mới:
RapidOCR (PP-OCRv4 trên ONNX) toàn khung 9/13 và 1293ms; RapidOCR trên vùng biển đã
khoanh cũng 9/13 và 1710ms. Cả hai trượt sạch biển 2 dòng. PaddleOCR bản gốc không cài
được: paddlepaddle chưa có wheel cho Python 3.14.
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, List, Sequence, Tuple

from backend.app.core.config import settings
from backend.app.services.plate_detector import crop_bbox, find_plate_regions

logger = logging.getLogger(__name__)

# Ngưỡng tin cậy tối thiểu để chấp nhận một chuỗi biển số đọc được.
# Giá trị thật lúc chạy lấy từ OCR_CONFIDENCE_THRESHOLD trong .env.
DEFAULT_PLATE_CONFIDENCE_THRESHOLD = 0.50

# Vùng quét cản va: biển số gắn ở cản trước/cản sau, tức phần dưới của BBox xe.
# Đo trên footage GATE-01 thì camera nhìn xe ở góc nghiêng, BBox bao trọn cả đầu kéo
# lẫn rơ-moóc, nên **không** được ném cả dải này vào OCR — đáy BBox chủ yếu là mặt
# đường vạch vàng-đen và bánh xe, sinh token rác lấn át biển số. Dải này chỉ là không
# gian tìm kiếm; find_plate_candidates() mới là thứ chọn ra hình chữ nhật biển số.
PLATE_ROI_TOP_RATIO = 0.45
# Margin cũ 8% cắt mất biển của xe nằm sát mép BBox (biển thường ở rìa cản va).
PLATE_ROI_SIDE_MARGIN_RATIO = 0.02

# Biển số nằm lệch hẳn về một góc dưới của đuôi/đầu xe. Hai góc này là phương án dự
# phòng khi lọc cạnh không khoanh được hình chữ nhật nào (biển quá mờ để có viền rõ):
# vùng nhỏ hơn dải cản va nên được phóng to mạnh hơn, OCR còn cơ hội bóc ra mảnh ký tự.
BUMPER_CORNER_WIDTH_RATIO = 0.45

# EasyOCR đọc rất kém dưới ~100px chiều ngang. Biển sau container trong footage GATE-01
# chỉ rộng khoảng 25-40px, nên mọi ứng viên đều phải được phóng lên tối thiểu 200px.
MIN_ROI_WIDTH_PX = 200
# ROI hẹp thì ép thêm hệ số tối thiểu: 25px * 3 = 75px vẫn dưới 200px nên MIN_ROI_WIDTH_PX
# thường là ràng buộc quyết định, hệ số này chỉ chặn trường hợp ROI ~70-120px bị phóng quá ít.
MIN_UPSCALE_FACTOR = 3.0
SMALL_ROI_WIDTH_PX = 120
# Trần phóng to: nội suy quá 8x chỉ nhân bản nhiễu nén video chứ không thêm thông tin,
# đổi lại ảnh to gấp 64 lần làm EasyOCR chậm hẳn.
MAX_UPSCALE_FACTOR = 8.0

# Tỉ lệ khung biển số Việt Nam. Biển dài 1 dòng ~470x110mm (4.3:1), biển vuông 2 dòng
# ~280x200mm (1.4:1). Nới hai đầu để chịu được biến dạng phối cảnh khi xe đi chéo.
LONG_PLATE_ASPECT_RANGE = (2.5, 5.5)
SQUARE_PLATE_ASPECT_RANGE = (1.2, 1.8)

# Ứng viên nhỏ hơn ngần này thì kể cả phóng to cũng không còn nét chữ để đọc.
MIN_PLATE_WIDTH_PX = 16
MIN_PLATE_HEIGHT_PX = 7
# Hình chữ nhật chiếm gần trọn dải cản va là thành/thùng xe, không phải biển số.
MAX_PLATE_WIDTH_RATIO = 0.60
MAX_PLATE_HEIGHT_RATIO = 0.85

# Biển số Việt Nam nền trắng/vàng, chữ đen. Vùng tối hơn ngưỡng này là lốp, gầm xe,
# bóng đổ — loại sớm để không tốn một lượt gọi EasyOCR.
MIN_PLATE_MEAN_BRIGHTNESS = 85

# Trần số lần gọi OCR cho mỗi xe mỗi frame. Endpoint /live-detections bị frontend poll
# liên tục, mỗi lượt readtext trên CPU tốn hàng chục ms; không chặn thì một khung hình
# nhiều xe sẽ kéo cả stream tụt.
MAX_OCR_ATTEMPTS = 4

# Số ký tự OCR đọc đúng liên tiếp tối thiểu để được phép khớp một biển trong roster.
# Dưới ngưỡng này thì bằng chứng quá mỏng, trả None và tính là "không đọc được" — thà
# bỏ trống còn hơn gán một biển số không có căn cứ vào bảng events.
#
# Đo trên data/video/GATE-01.mp4: ở mức 2, mảnh rác '1604654' (EasyOCR đọc nhầm chữ
# chìm trên thùng xe) khớp '16H-002.15' chỉ nhờ hai ký tự '16' và sinh một lượt xe ma.
# Mức 3 loại sạch nhiễu đo được mà vẫn giữ được ca thật '16H' và ca '164-00215'.
MIN_ROSTER_EVIDENCE_CHARS = 3

# Ký tự chỉ bị nhầm theo một chiều đáng tin: ở vị trí bắt buộc là chữ số, các chữ cái
# này gần như luôn là lỗi đọc. Chiều ngược lại (số -> chữ ở vị trí seri) KHÔNG được
# ánh xạ: đoán '0' thành 'D' hay 'O' là bịa dữ liệu, thà trả về None còn hơn ghi sai
# một biển số vào bảng events.
_DIGIT_LOOKALIKES = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
}

# Biển số Việt Nam: 2 chữ số mã tỉnh + 1-2 chữ cái seri + 4-5 chữ số.
_PLATE_STRUCTURE_RE = re.compile(r"^([0-9A-Z]{2})([A-Z]{1,2})([0-9A-Z]{4,5})$")

# Model fast-plate-ocr mặc định. 'cct-s-v2-global-model' (~10MB) đọc đúng 5/5 biển đo
# được trên clip cổng với char_prob > 0.999 và ~45ms mỗi tấm biển trên CPU. Bản 'xs'
# nhỏ hơn nhưng chưa đo trên footage này.
DEFAULT_PLATE_MODEL = "cct-s-v2-global-model"

# Sàn confidence riêng cho recognizer chuyên biển. Thang điểm của nó khác hẳn EasyOCR:
# đọc đúng thì char_prob gần như luôn > 0.99, còn khi đoán bừa trên một mảnh không phải
# biển thì tụt xuống dưới 0.5. Nhờ khoảng cách đó, ngưỡng ở đây đặt cao được mà không
# mất lượt đọc thật — và cao là cần thiết vì vùng màu vàng có thể là vạch sơn.
MIN_PLATE_MODEL_CONFIDENCE = 0.60


def _coerce_digits(chunk: str) -> str:
    return "".join(_DIGIT_LOOKALIKES.get(char, char) for char in chunk)


def compact_plate(raw_text: str | None) -> str:
    """Bỏ mọi ký tự phân cách, đưa về chữ hoa: '16H-002.15' -> '16H00215'."""
    return re.sub(r"[^0-9A-Z]", "", (raw_text or "").upper())


def normalize_plate_text(raw_text: str | None) -> str | None:
    """Chuẩn hoá chuỗi OCR thô về định dạng biển số Việt Nam, hoặc None nếu không phải.

    29A12345  -> 29A-123.45
    15C 67890 -> 15C-678.90
    29A1234   -> 29A-1234
    """
    compact = compact_plate(raw_text)
    if not 7 <= len(compact) <= 9:
        return None

    match = _PLATE_STRUCTURE_RE.match(compact)
    if not match:
        return None

    province = _coerce_digits(match.group(1))
    series = match.group(2)
    serial = _coerce_digits(match.group(3))
    if not province.isdigit() or not serial.isdigit():
        return None

    if len(serial) == 5:
        return f"{province}{series}-{serial[:3]}.{serial[3:]}"
    return f"{province}{series}-{serial}"


def match_roster_plate(
    fragments: Sequence[Tuple[str, float]],
    roster: Sequence[str],
    min_evidence_chars: int = MIN_ROSTER_EVIDENCE_CHARS,
) -> Tuple[str, float] | None:
    """Ghép các mảnh ký tự OCR đọc được vào một biển số đã biết của footage.

    Đây là hoàn thiện một lượt đọc dở dang bằng danh sách phương tiện đã đăng ký, không
    phải sinh biển số: hàm chỉ trả kết quả khi OCR thực sự đọc được ít nhất
    `min_evidence_chars` ký tự liên tiếp nằm trong biển đó. Không có mảnh nào -> None.

    Confidence trả về bị chiết khấu theo tỉ lệ ký tự thực sự có bằng chứng, để một biển
    khớp từ 3/8 ký tự không bao giờ trông chắc chắn ngang một lượt đọc trọn vẹn.
    """
    normalized_roster = [(plate, compact_plate(plate)) for plate in roster or []]
    normalized_roster = [item for item in normalized_roster if item[1]]
    if not normalized_roster:
        return None

    scored: List[Tuple[int, str, float]] = []
    for plate, compact in normalized_roster:
        matched_chars = 0
        matched_confidence = 0.0
        for raw_text, confidence in fragments:
            piece = compact_plate(raw_text)
            if len(piece) < min_evidence_chars:
                continue
            # Đo bằng chuỗi con chung dài nhất chứ không đòi mảnh nằm trọn trong biển:
            # ở 50px, EasyOCR trả '164-00215' cho biển 16H-002.15 — một ký tự đọc sai
            # không được phép xoá sạch bằng chứng của 5 ký tự đọc đúng liền nhau.
            # Vẫn là chuỗi *liên tiếp*: đúng ký tự nhưng sai thứ tự thì không tính.
            run = max(
                _longest_common_substring(piece, compact),
                _longest_common_substring(_coerce_digits(piece), compact),
            )
            # Lấy mảnh mạnh nhất thay vì cộng dồn: cùng một tấm biển thường được EasyOCR
            # trả về nhiều lần ở các vùng chồng nhau, cộng dồn sẽ thổi phồng bằng chứng.
            if run > matched_chars:
                matched_chars = run
                matched_confidence = float(confidence)

        if matched_chars < min_evidence_chars:
            continue
        coverage = min(1.0, matched_chars / len(compact))
        scored.append((matched_chars, plate, matched_confidence * coverage))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    # Bằng chứng khớp đều hai biển thì không có cơ sở chọn cái nào; đoán bừa ở đây là
    # ghi sai một lượt xe vào lịch sử cổng.
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        logger.debug("Mảnh OCR khớp nhiều biển trong roster như nhau, bỏ qua: %s", fragments)
        return None

    _evidence, plate, confidence = scored[0]
    return plate, round(confidence, 3)


def _box_sort_key(box: Any) -> Tuple[float, float]:
    """Sắp token theo thứ tự đọc (trên xuống, trái sang) để ghép biển số 2 dòng."""
    try:
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        return (min(ys), min(xs))
    except (TypeError, ValueError, IndexError):
        return (0.0, 0.0)


@dataclass(frozen=True)
class PlateReading:
    """Kết quả một lượt đọc biển số, kèm nguồn gốc để phân biệt đọc thật và khớp roster."""

    plate_text: str | None
    confidence: float
    # "plate_ocr": recognizer chuyên biển đọc từ vùng biển đã khoanh. "ocr": EasyOCR đọc
    # trọn vẹn đúng định dạng. "roster_match": ghép mảnh vào biển đã biết. "unreadable":
    # có gọi OCR nhưng không ra biển. "unavailable": không engine nào dùng được.
    source: str
    fragments: Tuple[Tuple[str, float], ...] = field(default=())

    @property
    def recognized(self) -> bool:
        return self.plate_text is not None


class PlateRecognizer:
    """fast-plate-ocr: recognizer chuyên biển số, nạp lazy, chạy trên CPU qua ONNX.

    Khác OCR tổng quát ở chỗ nó nhận nguyên tấm biển đã cắt và trả thẳng chuỗi ký tự —
    kể cả biển vuông 2 dòng, thứ mà EasyOCR và RapidOCR đều trả thành hai token rời rồi
    ghép sai thứ tự. Model 'cct-s-v2-global-model' còn trả về vùng quốc gia; đo trên
    clip cổng, cả 5 biển đều được gán region='Vietnam' với xác suất > 0.999.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or DEFAULT_PLATE_MODEL
        self._model = None
        self._lock = threading.Lock()
        self._unavailable = False

    def get_model(self):
        """Nạp model ở lần đọc đầu tiên. Trả None nếu không cài được — thiếu recognizer
        làm mất đường đọc chính chứ không được làm sập luồng phát hiện của cổng."""
        if self._model is not None or self._unavailable:
            return self._model

        with self._lock:
            if self._model is not None or self._unavailable:
                return self._model
            try:
                from fast_plate_ocr import LicensePlateRecognizer

                logger.info("Lazy-loading fast-plate-ocr (model=%s)", self.model_name)
                self._model = LicensePlateRecognizer(self.model_name)
            except Exception as exc:
                self._unavailable = True
                logger.warning(
                    "Không nạp được fast-plate-ocr, LPR lùi về EasyOCR: %s", exc
                )
            return self._model

    def is_available(self) -> bool:
        return self.get_model() is not None

    def read(self, plate_image) -> Tuple[str, float] | None:
        """Đọc một tấm biển đã cắt. Trả (chuỗi thô, confidence) hoặc None."""
        model = self.get_model()
        if model is None or plate_image is None or getattr(plate_image, "size", 0) == 0:
            return None

        import cv2
        import numpy as np

        # Model nhận RGB; ảnh từ OpenCV là BGR. Đưa nhầm thứ tự kênh vẫn chạy nhưng
        # đọc sai ký tự, và không có lỗi nào được ném ra để nhận biết.
        rgb = cv2.cvtColor(plate_image, cv2.COLOR_BGR2RGB)
        try:
            # Thiếu return_confidence thì char_probs về rỗng và mọi lượt đọc đều mang
            # confidence 0.0 — tức là bị sàn tin cậy chặn sạch dù đọc đúng ký tự.
            predictions = model.run(rgb, return_confidence=True)
        except Exception as exc:
            logger.warning("Lỗi khi chạy recognizer biển số: %s", exc)
            return None

        if not isinstance(predictions, list):
            predictions = [predictions]
        for prediction in predictions:
            text = getattr(prediction, "plate", None)
            if not text:
                continue
            char_probs = getattr(prediction, "char_probs", None)
            # Confidence của cả tấm biển là ký tự yếu nhất, không phải trung bình: một
            # ký tự đọc bấp bênh làm sai cả biển số, mà trung bình thì 9 ký tự chắc
            # chắn dư sức che lấp nó.
            if char_probs is not None and len(char_probs) > 0:
                confidence = float(np.min(np.asarray(char_probs)))
            else:
                confidence = float(getattr(prediction, "confidence", 0.0) or 0.0)
            return str(text), confidence
        return None


class LPREngine:
    """EasyOCR reader lazy-load + tìm vùng biển số / tiền xử lý cho camera cổng."""

    def __init__(
        self,
        languages: Sequence[str] = ("en",),
        confidence_threshold: float | None = None,
        plate_roster: Sequence[str] | None = None,
        min_accepted_confidence: float | None = None,
    ):
        self.languages = list(languages)
        self.confidence_threshold = (
            DEFAULT_PLATE_CONFIDENCE_THRESHOLD
            if confidence_threshold is None
            else float(confidence_threshold)
        )
        self.min_accepted_confidence = (
            self.confidence_threshold
            if min_accepted_confidence is None
            else float(min_accepted_confidence)
        )
        self.plate_roster = [p for p in (plate_roster or []) if p]
        self._reader = None
        self._reader_lock = threading.Lock()
        self._reader_unavailable = False
        self.plate_recognizer = PlateRecognizer()

    def get_reader(self):
        """Dựng EasyOCR Reader ở lần đọc biển số đầu tiên, tái dùng cho các lần sau.

        Trả None nếu easyocr chưa cài hoặc không khởi tạo được — thiếu OCR làm mất
        tính năng LPR chứ không được làm sập luồng phát hiện đối tượng của cổng.
        """
        if self._reader is not None or self._reader_unavailable:
            return self._reader

        with self._reader_lock:
            if self._reader is not None or self._reader_unavailable:
                return self._reader
            try:
                import easyocr

                logger.info("Lazy-loading EasyOCR Reader cho LPR (languages=%s)", self.languages)
                self._reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
            except Exception as exc:
                self._reader_unavailable = True
                logger.warning("Không khởi tạo được EasyOCR Reader, LPR bị vô hiệu: %s", exc)
            return self._reader

    def is_available(self) -> bool:
        """Có ít nhất một engine đọc được không. Gọi lần đầu sẽ kéo theo việc nạp model."""
        return self.plate_recognizer.is_available() or self.get_reader() is not None

    def ocr_status(self) -> str:
        """'ready' | 'unavailable' — để API báo tường minh thay vì im lặng trả rỗng."""
        return "ready" if self.is_available() else "unavailable"

    @staticmethod
    def crop_plate_roi(frame_matrix, bbox: Sequence[float] | None):
        """Cắt dải cản va (phần dưới BBox xe) từ BBox phần trăm [x, y, w, h] (0..100).

        Đây là *không gian tìm kiếm*, không phải vùng biển số: xem PLATE_ROI_TOP_RATIO.
        """
        if frame_matrix is None or bbox is None or len(bbox) != 4:
            return None

        height, width = frame_matrix.shape[:2]
        left_pct, top_pct, width_pct, height_pct = [float(v) for v in bbox]
        if width_pct <= 0 or height_pct <= 0:
            return None

        box_left = (left_pct / 100.0) * width
        box_top = (top_pct / 100.0) * height
        box_width = (width_pct / 100.0) * width
        box_height = (height_pct / 100.0) * height

        roi_left = int(round(box_left + box_width * PLATE_ROI_SIDE_MARGIN_RATIO))
        roi_right = int(round(box_left + box_width * (1.0 - PLATE_ROI_SIDE_MARGIN_RATIO)))
        roi_top = int(round(box_top + box_height * PLATE_ROI_TOP_RATIO))
        roi_bottom = int(round(box_top + box_height))

        roi_left = max(0, min(roi_left, width - 1))
        roi_top = max(0, min(roi_top, height - 1))
        roi_right = max(roi_left + 1, min(roi_right, width))
        roi_bottom = max(roi_top + 1, min(roi_bottom, height))

        roi = frame_matrix[roi_top:roi_bottom, roi_left:roi_right]
        if getattr(roi, "size", 0) == 0:
            return None
        return roi

    @staticmethod
    def bumper_corner_regions(bumper_roi) -> List[Any]:
        """Hai góc dưới của dải cản va, nơi biển số thực tế được bắt vít."""
        if bumper_roi is None or getattr(bumper_roi, "size", 0) == 0:
            return []

        roi_height, roi_width = bumper_roi.shape[:2]
        corner_width = max(1, int(round(roi_width * BUMPER_CORNER_WIDTH_RATIO)))
        if corner_width >= roi_width:
            return []

        left = bumper_roi[:, :corner_width]
        right = bumper_roi[:, roi_width - corner_width:]
        return [region for region in (right, left) if getattr(region, "size", 0) > 0]

    @staticmethod
    def find_plate_candidates(region_matrix, max_candidates: int = 3) -> List[Any]:
        """Khoanh các hình chữ nhật có tỉ lệ và độ sáng của một tấm biển số.

        Lọc cạnh Canny + tìm đường bao, giữ contour có tỉ lệ rộng/cao rơi vào khung
        biển dài hoặc biển vuông, nền đủ sáng. Trả về danh sách patch đã sắp theo điểm
        khả dĩ giảm dần (ứng viên tốt nhất đứng đầu).
        """
        import cv2
        import numpy as np

        if region_matrix is None or getattr(region_matrix, "size", 0) == 0:
            return []

        region_height, region_width = region_matrix.shape[:2]
        gray = region_matrix
        if getattr(region_matrix, "ndim", 2) == 3:
            gray = cv2.cvtColor(region_matrix, cv2.COLOR_BGR2GRAY)

        # bilateralFilter làm phẳng vân bê tông/vạch sơn mà vẫn giữ cạnh tấm biển.
        smoothed = cv2.bilateralFilter(gray, 5, 40, 40)
        edges = cv2.Canny(smoothed, 40, 140)
        # Viền biển số ở 30px thường đứt nét; khép lại để contour thành hình chữ nhật kín.
        edges = cv2.morphologyEx(
            edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        )

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        scored: List[Tuple[float, Tuple[int, int, int, int]]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < MIN_PLATE_WIDTH_PX or h < MIN_PLATE_HEIGHT_PX:
                continue
            if w > region_width * MAX_PLATE_WIDTH_RATIO or h > region_height * MAX_PLATE_HEIGHT_RATIO:
                continue

            aspect_ratio = w / float(h)
            is_long = LONG_PLATE_ASPECT_RANGE[0] <= aspect_ratio <= LONG_PLATE_ASPECT_RANGE[1]
            is_square = SQUARE_PLATE_ASPECT_RANGE[0] <= aspect_ratio <= SQUARE_PLATE_ASPECT_RANGE[1]
            if not (is_long or is_square):
                continue

            patch = gray[y:y + h, x:x + w]
            brightness = float(np.mean(patch))
            if brightness < MIN_PLATE_MEAN_BRIGHTNESS:
                continue

            # Điểm khả dĩ: gần tỉ lệ chuẩn, nền sáng, kích thước lớn thì đọc dễ hơn.
            ideal_ratio = 4.3 if is_long else 1.4
            ratio_penalty = abs(aspect_ratio - ideal_ratio) / ideal_ratio
            score = (brightness / 255.0) + (w / float(region_width)) - ratio_penalty
            scored.append((score, (x, y, w, h)))

        scored.sort(key=lambda item: item[0], reverse=True)

        candidates: List[Any] = []
        accepted: List[Tuple[int, int, int, int]] = []
        for _score, rect in scored:
            if any(_rects_overlap(rect, taken) for taken in accepted):
                continue
            accepted.append(rect)
            x, y, w, h = rect
            # Nới vài pixel: contour thường bám sát viền và cắt cụt ký tự ngoài cùng.
            pad_x = max(2, int(round(w * 0.06)))
            pad_y = max(2, int(round(h * 0.12)))
            x0 = max(0, x - pad_x)
            y0 = max(0, y - pad_y)
            x1 = min(region_width, x + w + pad_x)
            y1 = min(region_height, y + h + pad_y)
            candidates.append(region_matrix[y0:y1, x0:x1])
            if len(candidates) >= max_candidates:
                break

        return candidates

    @staticmethod
    def preprocess_plate_roi(roi_matrix):
        """Phóng to (siêu phân giải nội suy) -> CLAHE -> unsharp masking.

        Không nhị phân hoá nữa: adaptive threshold trên ảnh cổng ngoài trời biến vạch
        sơn và vân bê tông thành nhiễu muối tiêu đặc kín, xoá luôn nét chữ biển số.
        EasyOCR vốn có bước nhị phân riêng và đọc ảnh xám tốt hơn ảnh đã bị ép trắng đen.
        """
        import cv2

        gray = roi_matrix
        if getattr(roi_matrix, "ndim", 2) == 3:
            gray = cv2.cvtColor(roi_matrix, cv2.COLOR_BGR2GRAY)

        roi_height, roi_width = gray.shape[:2]
        if roi_width > 0 and roi_height > 0:
            scale = MIN_ROI_WIDTH_PX / float(roi_width)
            if roi_width < SMALL_ROI_WIDTH_PX:
                scale = max(scale, MIN_UPSCALE_FACTOR)
            scale = max(1.0, min(scale, MAX_UPSCALE_FACTOR))
            if scale > 1.01:
                gray = cv2.resize(
                    gray,
                    (
                        max(1, int(round(roi_width * scale))),
                        max(1, int(round(roi_height * scale))),
                    ),
                    interpolation=cv2.INTER_CUBIC,
                )

        # Ảnh cổng ngoài trời có nắng/bóng đổ loang trên cùng một tấm biển, nên phải
        # cân bằng sáng theo cục bộ; equalizeHist toàn cục làm mất nửa biển trong bóng.
        contrasted = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

        # Unsharp masking: nội suy CUBIC trả lại ảnh to nhưng nhoè, viền chữ số bị nén
        # video làm mờ vẫn không đọc được. Trừ đi bản làm mờ để dựng lại độ nét của viền.
        blurred = cv2.GaussianBlur(contrasted, (0, 0), 3)
        return cv2.addWeighted(contrasted, 1.6, blurred, -0.6, 0)

    @staticmethod
    def crop_trigger_box(frame_matrix, trigger_box: Sequence[float] | None):
        """Cắt LPR Trigger Box [x, y, w, h] phần trăm (0..100) khỏi khung hình."""
        if frame_matrix is None or trigger_box is None or len(trigger_box) != 4:
            return None

        height, width = frame_matrix.shape[:2]
        left_pct, top_pct, width_pct, height_pct = [float(v) for v in trigger_box]
        if width_pct <= 0 or height_pct <= 0:
            return None

        left = max(0, min(int(round(left_pct / 100.0 * width)), width - 1))
        top = max(0, min(int(round(top_pct / 100.0 * height)), height - 1))
        right = max(left + 1, min(int(round((left_pct + width_pct) / 100.0 * width)), width))
        bottom = max(top + 1, min(int(round((top_pct + height_pct) / 100.0 * height)), height))

        roi = frame_matrix[top:bottom, left:right]
        if getattr(roi, "size", 0) == 0:
            return None
        return roi

    def read_plate_by_detector(
        self,
        frame_matrix,
        bbox: Sequence[float] | None = None,
    ) -> PlateReading | None:
        """Đường đọc chính: khoanh tấm biển bằng màu rồi đưa cho recognizer chuyên biển.

        `bbox` chỉ để thu hẹp không gian tìm kiếm về một chiếc xe. Bỏ trống thì quét
        vùng cấu hình ở `GATE_PLATE_SCAN_REGION` — cần thiết ở camera cổng, vì khi xe áp
        sát bốt nó chiếm gần trọn khung và YOLO ngừng nhận ra đó là xe, đúng lúc tấm
        biển rõ nhất. Vùng đó cắt bỏ phần mặt đường vốn không bao giờ có biển, nhờ vậy
        giảm hơn nửa số lần gọi OCR trên các mảng màu vàng của vạch sơn và bốt.

        Trả None nghĩa là "đường đọc này không có gì để nói, thử cách khác đi" — xảy ra
        khi recognizer không cài được, hoặc khi không khoanh được vùng biển nào. Khác hẳn
        với PlateReading 'unreadable', vốn có nghĩa là đã nhìn thấy một tấm biển mà không
        đọc nổi nó.
        """
        if not self.plate_recognizer.is_available():
            return None

        if bbox is not None:
            search_area = crop_bbox(frame_matrix, bbox)
        else:
            scan_region = settings.gate_plate_scan_region()
            search_area = (
                crop_bbox(frame_matrix, scan_region) if scan_region else frame_matrix
            )
        if search_area is None or getattr(search_area, "size", 0) == 0:
            return PlateReading(None, 0.0, "unreadable")

        regions = find_plate_regions(search_area)
        if not regions:
            # Không khoanh được tấm biển nào. Có thể là khung hình không có xe, cũng có
            # thể là biển bẩn hoặc màu lạ nằm ngoài dải HSV — nên nhường lượt cho nhánh
            # EasyOCR quét cản va thay vì kết luận "không đọc được".
            return None

        fragments: List[Tuple[str, float]] = []
        best: Tuple[str, float] | None = None
        for region in regions:
            result = self.plate_recognizer.read(region.image)
            if result is None:
                continue
            raw_text, confidence = result
            fragments.append((raw_text, confidence))
            if confidence < MIN_PLATE_MODEL_CONFIDENCE:
                logger.debug(
                    "Bỏ '%s' từ vùng %s: confidence %.3f < sàn model %.2f",
                    raw_text, region.rect, confidence, MIN_PLATE_MODEL_CONFIDENCE,
                )
                continue
            plate_text = normalize_plate_text(raw_text)
            if plate_text and (best is None or confidence > best[1]):
                best = (plate_text, confidence)

        if best is not None:
            return self._accept(best[0], best[1], "plate_ocr", fragments)
        return PlateReading(
            None,
            round(max((c for _t, c in fragments), default=0.0), 3),
            "unreadable",
            tuple(fragments),
        )

    def read_plate(
        self,
        frame_matrix,
        bbox: Sequence[float] | None,
        trigger_box: Sequence[float] | None = None,
    ) -> PlateReading:
        """Đọc biển số của một xe.

        Thử recognizer chuyên biển trước; chỉ khi nó không cài được mới lùi về EasyOCR.

        Ở nhánh EasyOCR: có `trigger_box` thì chỉ chạy đúng một lượt OCR trong ô cố định
        đó, không có thì quét cản va (khoanh ứng viên -> OCR -> khớp roster).
        """
        by_detector = self.read_plate_by_detector(frame_matrix, bbox)
        if by_detector is not None:
            # Recognizer chuyên biển chạy được thì nó là câu trả lời cuối cùng, kể cả khi
            # không đọc ra biển nào. Chạy tiếp EasyOCR ở đây sẽ kéo torch vào tiến trình
            # và tốn thêm ~300ms mỗi frame, mà đo trên clip cổng nó không cứu thêm được
            # lượt xe nào — nó chỉ thêm cơ hội sinh chuỗi rác.
            return by_detector

        reader = self.get_reader()
        if reader is None:
            return PlateReading(None, 0.0, "unavailable")

        if trigger_box is not None:
            triggered = self.crop_trigger_box(frame_matrix, trigger_box)
            if triggered is None:
                return PlateReading(None, 0.0, "unreadable")
            return self._read_from_regions(reader, [triggered])

        bumper = self.crop_plate_roi(frame_matrix, bbox)
        if bumper is None:
            return PlateReading(None, 0.0, "unreadable")

        try:
            regions = self._ocr_regions(bumper)
        except Exception as exc:
            logger.warning("Lỗi khi khoanh vùng biển số: %s", exc)
            regions = [bumper]
        return self._read_from_regions(reader, regions)

    def _accept(self, plate_text: str, confidence: float, source: str, fragments) -> PlateReading:
        """Cổng ra duy nhất cho một kết quả nhận thành công.

        Sàn cứng áp cho MỌI nguồn, kể cả khớp roster: một biển số dưới ngưỡng lên tới UI
        và vào bảng events thì người trực cổng không có cách nào phân biệt nó với một
        lượt đọc thật. Đã xảy ra: hai lượt xe ma ghi ở confidence 0.094.
        """
        if confidence < self.min_accepted_confidence:
            logger.debug(
                "Bỏ biển số '%s' (%s): confidence %.3f < sàn %.2f",
                plate_text,
                source,
                confidence,
                self.min_accepted_confidence,
            )
            return PlateReading(None, round(confidence, 3), "unreadable", tuple(fragments))
        return PlateReading(plate_text, round(confidence, 3), source, tuple(fragments))

    def _read_from_regions(self, reader, regions: List[Any]) -> PlateReading:
        candidates: List[Tuple[str, float]] = []
        fragments: List[Tuple[str, float]] = []
        for region in regions[:MAX_OCR_ATTEMPTS]:
            try:
                raw_results = reader.readtext(self.preprocess_plate_roi(region))
            except Exception as exc:
                logger.warning("Lỗi khi chạy OCR biển số: %s", exc)
                continue
            region_candidates, region_fragments = self._plate_candidates(raw_results)
            candidates.extend(region_candidates)
            fragments.extend(region_fragments)
            if region_candidates:
                # Đã có chuỗi khớp định dạng biển số thì không cần quét nốt các vùng
                # dự phòng — chúng chỉ tồn tại cho trường hợp không khoanh được gì.
                break

        if candidates:
            plate_text, confidence = max(candidates, key=lambda item: item[1])
            if confidence >= self.confidence_threshold:
                return self._accept(plate_text, confidence, "ocr", fragments)
            logger.debug(
                "Bỏ biển số '%s': confidence %.3f < ngưỡng %.2f",
                plate_text,
                confidence,
                self.confidence_threshold,
            )

        # OCR không ghép đủ 7-9 ký tự đúng định dạng. Nếu vẫn bóc được mảnh ký tự thì thử
        # hoàn thiện bằng danh sách phương tiện đã biết của camera này.
        matched = match_roster_plate(fragments, self.plate_roster)
        if matched is not None:
            plate_text, confidence = matched
            logger.info(
                "Khớp roster GATE: mảnh OCR %s -> %s (confidence %.3f)",
                [text for text, _conf in fragments],
                plate_text,
                confidence,
            )
            return self._accept(plate_text, confidence, "roster_match", fragments)

        best_confidence = max((conf for _text, conf in candidates), default=0.0)
        return PlateReading(None, round(best_confidence, 3), "unreadable", tuple(fragments))

    def _ocr_regions(self, bumper_roi) -> List[Any]:
        """Ứng viên biển số trước, hai góc cản va sau, cả dải cản va là chốt chặn cuối."""
        regions = list(self.find_plate_candidates(bumper_roi))
        regions.extend(self.bumper_corner_regions(bumper_roi))
        regions.append(bumper_roi)
        return regions

    def extract_license_plate(
        self, frame_matrix, bbox: Sequence[float] | None
    ) -> Tuple[str | None, float]:
        """Bóc tách chuỗi biển số từ BBox xe.

        Giữ nguyên chữ ký tuple (plate_text, confidence) cho các chỗ gọi chỉ cần kết quả;
        dùng read_plate() khi cần biết cả nguồn gốc và các mảnh ký tự đọc được.
        """
        reading = self.read_plate(frame_matrix, bbox)
        return reading.plate_text, reading.confidence

    @staticmethod
    def _plate_candidates(raw_results: Any) -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
        """Trả về (biển số hợp lệ, các mảnh ký tự thô) từ kết quả readtext của EasyOCR."""
        ordered = sorted(list(raw_results or []), key=lambda item: _box_sort_key(item[0]))
        texts: List[str] = []
        confidences: List[float] = []
        candidates: List[Tuple[str, float]] = []
        fragments: List[Tuple[str, float]] = []

        for _box, text, confidence in ordered:
            text = str(text)
            confidence = float(confidence)
            texts.append(text)
            confidences.append(confidence)
            if compact_plate(text):
                fragments.append((text, confidence))
            plate = normalize_plate_text(text)
            if plate:
                candidates.append((plate, confidence))

        # Biển vuông 2 dòng, hoặc biển bị EasyOCR tách làm 2 mảnh, chỉ hợp lệ khi ghép lại.
        if len(texts) > 1:
            joined = normalize_plate_text("".join(texts))
            if joined:
                candidates.append((joined, sum(confidences) / len(confidences)))

        return candidates, fragments


def _longest_common_substring(left: str, right: str) -> int:
    """Độ dài chuỗi con *liên tiếp* dài nhất có mặt ở cả hai chuỗi."""
    if not left or not right:
        return 0

    previous_row = [0] * (len(right) + 1)
    best = 0
    for i in range(1, len(left) + 1):
        current_row = [0] * (len(right) + 1)
        for j in range(1, len(right) + 1):
            if left[i - 1] == right[j - 1]:
                current_row[j] = previous_row[j - 1] + 1
                if current_row[j] > best:
                    best = current_row[j]
        previous_row = current_row
    return best


def _rects_overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


lpr_engine = LPREngine(
    confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD,
    plate_roster=settings.gate_plate_roster(),
    min_accepted_confidence=settings.MIN_ACCEPTED_PLATE_CONFIDENCE,
)

import logging
import os
import threading
from typing import Any, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)

# Standard 8 object classes as defined in CR-001
CANONICAL_8_OBJECT_CLASSES = [
    "container",
    "truck",
    "forklift",
    "crane",
    "car",
    "motorbike",
    "bicycle",
    "person"
]

OBJECT_VIETNAMESE_NAMES = {
    # "Container" chứ không phải "Xe container": lớp này bao cả xe chở container lẫn
    # thùng container xếp tĩnh trong bãi, vì taxonomy 8 lớp không tách hai thứ đó ra.
    "container": "Container",
    "truck": "Xe tải",
    "forklift": "Xe nâng",
    "crane": "Xe cẩu",
    "car": "Xe con",
    "motorbike": "Xe máy",
    "bicycle": "Xe đạp",
    "person": "Người"
}

# Ánh xạ nhãn COCO sang 8 lớp chuẩn. Chỉ dùng cho nhánh dự phòng yolov8n (COCO 80 lớp
# không có container/forklift/crane); YOLO-World vốn đã trả thẳng tên lớp chuẩn.
#
# "train" -> "container" là xấp xỉ có chủ ý: mô hình COCO thường gán nhãn train cho xe
# đầu kéo chở container vì hình khối hộp dài giống nhau. Trước đây bảng này còn có
# "bench" -> "forklift", một suy diễn vô căn cứ khiến ghế băng và mọi vật thể ngang tầm
# bị báo thành xe nâng — đã bỏ. Không thêm ánh xạ mới nếu không có căn cứ hình học.
COCO_TO_CANONICAL = {
    "train": "container",
    "truck": "truck",
    "bus": "truck",
    "car": "car",
    "motorcycle": "motorbike",
    "bicycle": "bicycle",
    "person": "person",
}

# Prompt đưa vào YOLO-World, tách khỏi tên lớp chuẩn vì hai thứ phục vụ hai mục đích
# khác nhau: tên lớp là khoá dữ liệu ổn định (CSDL, API, UI đều bám vào), còn prompt là
# chuỗi ngôn ngữ nạp cho CLIP và phải chỉnh theo cảnh thật.
#
# Trước đây `set_classes()` nhận thẳng 8 tên lớp trần, và kết quả đo trên footage cảng
# (backend/scripts/render_zone_overlay.py) là: **0 detection trên toàn bộ bãi Bãi Kiểm**
# — cả một bãi đầy container lẫn một chiếc reach stacker giữa khung hình đều bị bỏ qua.
#
# Các prompt dưới đây được chọn bằng đo đạc, không phải phỏng đoán:
#   - "cargo container box" bắt được container; "shipping container" thì không.
#   - reach stacker chỉ chịu khớp với "yellow heavy machinery vehicle" (khớp cả khi xe
#     màu xanh — CLIP bám hình dáng máy công trình nhiều hơn bám từ "yellow").
#   - "semi trailer truck" nhận xe đầu kéo ở cổng với 0.89, so với 0.40 của "truck".
#   - Prompt dạng câu dài ("a tall gantry crane at a port") làm nổ false positive:
#     57 box trên một khung hình. Giữ prompt ở mức cụm danh từ ngắn.
#
# Hai prompt đã thử và bị loại, đừng thêm lại:
#   - "truck trailer": 33 box @0.97 trên một khung hình Xưởng An Ninh.
#   - "flatbed trailer": cứu được chiếc xe ở Làn IN 1 (0.27 -> 0.40) nhưng lại nuốt
#     luôn reach stacker với 0.74, biến xe nâng thành xe tải. Đánh đổi không đáng.
CANONICAL_CLASS_PROMPTS = {
    "container": ["cargo container box"],
    "truck": ["semi trailer truck", "truck"],
    "forklift": ["forklift", "reach stacker", "yellow heavy machinery vehicle"],
    "crane": ["crane", "gantry crane"],
    "car": ["car"],
    "motorbike": ["motorcycle"],
    "bicycle": ["bicycle"],
    "person": ["person"],
}

# Rich Open-Vocabulary Prompts for Port & Industrial Yard Equipment (CR-001)
RICH_CLASS_PROMPTS = [
    "shipping container", "freight container", "container",
    "container truck", "heavy cargo truck", "semi truck", "truck",
    "blue reach stacker", "container reach stacker", "reach stacker", "container handler", "heavy forklift", "forklift",
    "mobile crane truck", "container crane", "port crane", "gantry crane", "crane",
    "car", "automobile", "pickup truck",
    "motorbike", "motorcycle", "scooter",
    "bicycle", "bike",
    "person", "worker", "pedestrian",
    "light pole", "lamp post", "utility pole", "pole", "column"
]

PROMPT_TO_CANONICAL = {
    "shipping container": "container",
    "freight container": "container",
    "container truck": "truck",
    "heavy cargo truck": "truck",
    "semi truck": "truck",
    "blue reach stacker": "forklift",
    "container reach stacker": "forklift",
    "reach stacker": "forklift",
    "container handler": "forklift",
    "heavy forklift": "forklift",
    "mobile crane truck": "forklift",
    "container crane": "crane",
    "port crane": "crane",
    "gantry crane": "crane",
    "crane": "crane",
    "automobile": "car",
    "pickup truck": "car",
    "motorcycle": "motorbike",
    "scooter": "motorbike",
    "bike": "bicycle",
    "worker": "person",
    "pedestrian": "person",
    "light pole": "IGNORE",
    "lamp post": "IGNORE",
    "utility pole": "IGNORE",
    "pole": "IGNORE",
    "column": "IGNORE"
}

POLE_LIKE_BACKGROUND_CLASSES = {
    "light pole",
    "lamp post",
    "utility pole",
    "pole",
    "column",
    "post",
    "mast",
}

CRANE_RAW_CLASSES = {
    "container crane",
    "port crane",
    "gantry crane",
    "crane",
}

class AIVisionPipeline:
    """
    Ultralytics YOLO-World v2 Engine & Ray-Casting Point-in-Polygon Evaluator.
    Loads weight models from backend/app/ai/weights/.
    Supports 8 Object Classes (CR-001) & Open-Vocabulary Custom Object Detection.
    """

    # Ngưỡng mặc định khi gọi trực tiếp mà không truyền cấu hình.
    # Giá trị thật lúc chạy lấy từ DETECTION_CONFIDENCE_THRESHOLD trong .env.
    DEFAULT_CONFIDENCE_THRESHOLD = 0.30

    # Ultralytics mặc định iou=0.7, quá lỏng với cảnh này: một xe đầu kéo ở cổng cho ra
    # hai box lồng nhau (0.89 bao cả đầu kéo, 0.58 bao riêng rơ-moóc, IoU ~0.76) và cả
    # hai cùng lọt lên UI. Kèm agnostic_nms để gộp cả box trùng khác nhãn — với nhiều
    # prompt cho cùng một lớp, chuyện hai prompt cùng bắt một vật là bình thường.
    DEFAULT_IOU_THRESHOLD = 0.5

    def __init__(
        self,
        model_name_or_path: str = None,
        confidence_threshold: float = None,
    ):
        # Bỏ trống thì lấy DETECTION_MODEL_WEIGHTS trong .env, nhờ vậy đổi model chỉ
        # cần sửa một dòng cấu hình thay vì sửa cả ba chỗ khởi tạo pipeline.
        if model_name_or_path is None:
            from backend.app.core.config import settings
            model_name_or_path = settings.DETECTION_MODEL_WEIGHTS
        self.model_name_or_path = model_name_or_path
        self.confidence_threshold = (
            self.DEFAULT_CONFIDENCE_THRESHOLD
            if confidence_threshold is None
            else float(confidence_threshold)
        )
        self.model = None
        self.model_type = "yolo-world"
        self.classes = list(CANONICAL_8_OBJECT_CLASSES)
        # `prompts` là thứ nạp vào model; `prompt_to_class` đưa nhãn model trả về ngược
        # lại tên lớp chuẩn. Xem CANONICAL_CLASS_PROMPTS để biết vì sao phải tách đôi.
        self.prompts = []
        self.prompt_to_class = {}
        self._rebuild_prompts()
        self._initialize_model()

    def _rebuild_prompts(self):
        """Dựng lại danh sách prompt phẳng và bảng tra ngược từ self.classes."""
        self.prompts = []
        self.prompt_to_class = {}
        for cls_name in self.classes:
            # Lớp tuỳ chỉnh do người dùng thêm chưa có prompt riêng, dùng chính tên nó.
            for prompt in CANONICAL_CLASS_PROMPTS.get(cls_name, [cls_name]):
                if prompt not in self.prompt_to_class:
                    self.prompts.append(prompt)
                self.prompt_to_class[prompt.lower()] = cls_name

    def _weights_dir(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(current_dir))
        return os.path.join(backend_dir, "app", "ai", "weights")

    def _resolve_model_path(self, model_name: str = None) -> str:
        """
        Trả về đường dẫn tuyệt đối tới file weights.

        Nếu file chưa có sẵn, tải asset từ Ultralytics về thư mục
        backend/app/ai/weights/. Truyền đường dẫn đầy đủ cho trình tải để weights
        không bị ghi vào thư mục làm việc hiện tại (vốn thay đổi theo cách khởi chạy).
        """
        model_name = model_name or self.model_name_or_path

        # Đường dẫn tuyệt đối do người dùng chỉ định thì tôn trọng nguyên vẹn.
        if os.path.isabs(model_name):
            return model_name

        local_path = os.path.join(self._weights_dir(), os.path.basename(model_name))
        if os.path.exists(local_path):
            return local_path

        os.makedirs(self._weights_dir(), exist_ok=True)
        try:
            from ultralytics.utils.downloads import attempt_download_asset
            logger.info(f"Weights chưa có sẵn, đang tải: {model_name}")
            attempt_download_asset(local_path)
        except Exception as e:
            logger.warning(f"Không tải được weights '{model_name}': {e}")

        return local_path

    def _initialize_model(self):
        model_source = self._resolve_model_path()
        logger.info(f"Attempting to load model weights from: {model_source}")

        # 1. Try loading YOLOWorld
        if "world" in os.path.basename(model_source).lower():
            try:
                from ultralytics import YOLOWorld
                self.model = YOLOWorld(model_source)
                self.model.set_classes(self.prompts)
                self.model_type = "yolo-world"
                logger.info(f"Loaded YOLO-World v2 model with rich prompts from: {model_source}")
                return
            except Exception as e:
                logger.warning(f"YOLO-World load error: {e}")

        # 2. Weights YOLO thường (checkpoint finetune như sentri-yolo11s.pt, hoặc
        # yolov8n.pt). Nạp thẳng file đã yêu cầu — trước đây nhánh này bỏ qua
        # model_source và luôn nạp yolov8n.pt, nên mọi checkpoint tự huấn luyện đều
        # bị nuốt im lặng và hệ thống chạy bằng model COCO mặc định.
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_source)
            self.model_type = "yolo"
            logger.info(f"Loaded YOLO model from: {model_source}")
            return
        except Exception as e:
            logger.warning(f"YOLO model load error ({model_source}): {e}")

        # 3. Lưới an toàn cuối: yolov8n.pt để hệ thống còn chạy được khi weights chính
        # hỏng hoặc thiếu. Lớp phát hiện sẽ nghèo hơn, log lại để không âm thầm.
        try:
            from ultralytics import YOLO
            yolov8n_path = self._resolve_model_path("yolov8n.pt")
            self.model = YOLO(yolov8n_path)
            self.model_type = "yolov8"
            logger.warning(
                f"Lùi về weights dự phòng {yolov8n_path} vì không nạp được {model_source}."
            )
            return
        except Exception as e:
            logger.warning(f"YOLOv8 model load fallback error: {e}")

        self.model = None

    def update_custom_classes(self, new_classes: List[str]):
        combined_classes = list(self.classes)
        for cls_name in new_classes:
            if cls_name not in combined_classes:
                combined_classes.append(cls_name)
        self.classes = combined_classes
        self._rebuild_prompts()
        if self.model and self.model_type == "yolo-world":
            try:
                self.model.set_classes(self.prompts)
            except Exception as e:
                logger.error(f"Error setting custom classes: {e}")

    @staticmethod
    def normalize_point(point: Union[Dict[str, float], Tuple[float, float], List[float]]) -> Tuple[float, float]:
        if isinstance(point, dict):
            return (float(point.get("x", 0)), float(point.get("y", 0)))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            return (float(point[0]), float(point[1]))
        return (0.0, 0.0)

    def point_in_polygon(
        self,
        point: Union[Dict[str, float], Tuple[float, float], List[float]],
        polygon_points: List[Any]
    ) -> bool:
        if not polygon_points or len(polygon_points) < 3:
            return False

        px, py = self.normalize_point(point)
        raw_poly = [self.normalize_point(p) for p in polygon_points]

        max_coord = max(max(abs(pt[0]), abs(pt[1])) for pt in raw_poly)
        is_percentage = max_coord > 1.0

        if is_percentage:
            norm_poly = [(pt[0] / 100.0, pt[1] / 100.0) for pt in raw_poly]
            norm_p = (px / 100.0 if px > 1.0 else px, py / 100.0 if py > 1.0 else py)
        else:
            norm_poly = raw_poly
            norm_p = (px, py)

        x, y = norm_p
        n = len(norm_poly)
        inside = False
        p1x, p1y = norm_poly[0]

        for i in range(n + 1):
            p2x, p2y = norm_poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xints:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def evaluate_bbox_center_in_zone(
        self,
        bbox: Tuple[float, float, float, float],
        polygon_points: List[Any]
    ) -> bool:
        b0, b1, b2, b3 = bbox
        # If b2 > b0 and b3 > b1, format is (xmin, ymin, xmax, ymax)
        if b2 > b0 and b3 > b1:
            cx = (b0 + b2) / 2.0
            cy = (b1 + b3) / 2.0
        else:
            # Format is (left, top, width, height)
            cx = b0 + b2 / 2.0
            cy = b1 + b3 / 2.0
        return self.point_in_polygon((cx, cy), polygon_points)

    @staticmethod
    def map_raw_class_to_canonical(raw_cls_name: str) -> str | None:
        # Dataset tự huấn luyện đặt tên lớp kiểu snake_case ("shipping_container",
        # "container_truck") còn các bảng ánh xạ dưới đây viết cách bằng dấu cách.
        # Chuẩn hoá một lần ở đây thay vì nhân đôi mọi khoá trong từng bảng.
        raw_cls_lower = raw_cls_name.lower().strip().replace("_", " ")
        cls_name = PROMPT_TO_CANONICAL.get(raw_cls_lower, COCO_TO_CANONICAL.get(raw_cls_lower, raw_cls_lower))
        if cls_name == "IGNORE":
            return None

        if cls_name in CANONICAL_8_OBJECT_CLASSES:
            return cls_name

        if raw_cls_lower in ("train", "box", "shipping container", "freight container"):
            return "container"
        if raw_cls_lower in (
            "reach stacker",
            "container handler",
            "blue reach stacker",
            "container reach stacker",
            "mobile crane truck",
            # "bench" đã bị gỡ khỏi đây cùng lý do đã gỡ khỏi COCO_TO_CANONICAL:
            # ghế băng không phải xe nâng, và suy diễn này làm mọi vật thể ngang tầm
            # bị báo thành forklift. Xem test_bench_is_no_longer_mapped_to_forklift.
            "loader",
        ):
            return "forklift"
        if raw_cls_lower in ("bus", "heavy truck", "cargo truck", "heavy cargo truck", "semi truck"):
            return "truck"
        return None

    @staticmethod
    def is_pole_like_crane_false_positive(raw_cls_name: str, pct_bbox: List[float]) -> bool:
        raw_cls_lower = raw_cls_name.lower().strip()
        if raw_cls_lower in POLE_LIKE_BACKGROUND_CLASSES:
            return True
        if raw_cls_lower not in CRANE_RAW_CLASSES:
            return False

        _, _, width_pct, height_pct = pct_bbox
        if width_pct <= 0 or height_pct <= 0:
            return False

        aspect_ratio = height_pct / width_pct
        is_narrow_tall_structure = width_pct <= 8.0 and height_pct >= 22.0 and aspect_ratio >= 4.0
        is_very_thin_structure = width_pct <= 4.5 and height_pct >= 12.0 and aspect_ratio >= 3.0
        return is_narrow_tall_structure or is_very_thin_structure

    def process_frame(self, frame_matrix, zones: List[Dict[str, Any]] = None, conf_threshold: float = None) -> List[Dict[str, Any]]:
        """
        Runs YOLO inference on frame matrix and evaluates Ray-Casting PIP zone violations.
        Filters out detections below specified confidence threshold.

        Bỏ trống conf_threshold thì dùng self.confidence_threshold, tức giá trị
        DETECTION_CONFIDENCE_THRESHOLD trong .env.
        """
        if conf_threshold is None:
            conf_threshold = self.confidence_threshold
        detections = []
        if self.model is not None and frame_matrix is not None:
            try:
                results = self.model.predict(
                    frame_matrix,
                    conf=conf_threshold,
                    iou=self.DEFAULT_IOU_THRESHOLD,
                    agnostic_nms=True,
                    verbose=False,
                )
                # Lớp hợp lệ gồm 8 lớp chuẩn và cả lớp mở do người dùng thêm qua
                # update_custom_classes(); nếu chỉ nhận 8 lớp thì tính năng open-vocab
                # của YOLO-World trở thành vô nghĩa vì kết quả bị vứt ngay tại đây.
                known_classes = set(CANONICAL_8_OBJECT_CLASSES) | set(self.classes)

                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        conf = float(box.conf[0])
                        if conf < conf_threshold:
                            continue

                        cls_id = int(box.cls[0])
                        names = getattr(r, "names", None) or {}
                        raw_cls_name = names.get(cls_id)
                        if not raw_cls_name:
                            logger.warning(
                                f"Không tra được tên lớp cho cls_id={cls_id}, bỏ qua detection."
                            )
                            continue

                        # YOLO-World trả về chính prompt đã nạp, nên tra bảng prompt
                        # trước; COCO_TO_CANONICAL chỉ còn dùng cho nhánh yolov8n.
                        raw_lower = raw_cls_name.lower()
                        cls_name = self.prompt_to_class.get(raw_lower)
                        if cls_name is None:
                            # Nhãn không nằm trong prompt đã nạp: đưa qua bảng ánh xạ
                            # rộng hơn (COCO, prompt mô tả cảng, nền IGNORE) trước khi bỏ.
                            cls_name = self.map_raw_class_to_canonical(raw_cls_name)
                        if cls_name is None:
                            continue  # Skip ignored background and unmapped non-canonical noise.

                        # Không đoán bừa lớp. Trước đây mọi nhãn lạ đều bị ép thành
                        # "person", nên một vật thể không rõ là gì lại xuất hiện trên UI
                        # như một người thật và sinh vi phạm severity 3 — nguồn gốc của
                        # feed sự kiện toàn "Người · Vi phạm". Không nhận ra thì bỏ qua.
                        if cls_name not in known_classes:
                            logger.debug(
                                f"Bỏ qua lớp ngoài danh mục: '{raw_cls_name}' -> '{cls_name}'."
                            )
                            continue

                        xyxy = box.xyxy[0].tolist()

                        h, w = frame_matrix.shape[:2]
                        # Normalized BBox 0.0-1.0
                        norm_bbox = (xyxy[0] / w, xyxy[1] / h, xyxy[2] / w, xyxy[3] / h)
                        # Percentage BBox 0..100%
                        pct_bbox = [
                            round((xyxy[0] / w) * 100.0, 1),
                            round((xyxy[1] / h) * 100.0, 1),
                            round(((xyxy[2] - xyxy[0]) / w) * 100.0, 1),
                            round(((xyxy[3] - xyxy[1]) / h) * 100.0, 1)
                        ]

                        # Suppress pole/column-shaped crane false positives without removing wide crane structures.
                        if cls_name == "crane" and self.is_pole_like_crane_false_positive(raw_cls_name, pct_bbox):
                            continue

                        detection = {
                            "object_class": cls_name,
                            "vietnamese_name": OBJECT_VIETNAMESE_NAMES.get(cls_name, cls_name),
                            "confidence": round(conf, 3),
                            "bbox": pct_bbox,
                            "severity": 1,
                            "zone_violation": False,
                            "zone_name": None,
                            "zone_id": None,
                        }

                        if zones:
                            for zone in zones:
                                polygon = zone.get("vertices") or zone.get("polygon_points") or []
                                forbidden = zone.get("forbidden_classes") or zone.get("prohibited_object_types") or []
                                allowed = zone.get("allowed_classes") or zone.get("allowed_object_types") or []

                                is_inside = self.evaluate_bbox_center_in_zone(norm_bbox, polygon)
                                if is_inside:
                                    if cls_name in forbidden or (allowed and cls_name not in allowed):
                                        detection["zone_violation"] = True
                                        detection["severity"] = zone.get("severity", 3)
                                        detection["zone_name"] = zone.get("name", "Vùng Cấm")
                                        detection["zone_id"] = zone.get("id")
                                        break
                                    else:
                                        detection["zone_name"] = zone.get("name", "Zone An Toàn")
                                        detection["zone_id"] = zone.get("id")

                        detections.append(detection)
            except Exception as e:
                logger.error(f"Error in YOLO inference: {e}")
        return detections


# Một AIVisionPipeline cho mỗi bộ weights, chia sẻ giữa các camera dùng chung weights.
# Khoá cache là tên weights chứ không phải camera_id: ba camera dùng chung một file .pt
# thì không có lý do nạp ba bản model vào RAM.
_pipelines_by_weights: dict[str, "AIVisionPipeline"] = {}
_pipelines_lock = threading.Lock()


def get_pipeline_for_camera(camera_id: str | None) -> "AIVisionPipeline":
    """Pipeline dùng weights đã cấu hình cho camera này (DETECTION_MODEL_WEIGHTS_BY_CAMERA).

    Camera cổng và camera bãi cần hai bộ weights khác nhau — xem ghi chú ở
    `Settings.DETECTION_MODEL_WEIGHTS_BY_CAMERA`. Nạp lazy để một camera cấu hình sai
    weights không chặn cả tiến trình khởi động.
    """
    from backend.app.core.config import settings

    weights = settings.detection_weights_for(camera_id)
    with _pipelines_lock:
        pipeline = _pipelines_by_weights.get(weights)
        if pipeline is None:
            logger.info("Dựng AIVisionPipeline cho camera %s với weights %s", camera_id, weights)
            pipeline = AIVisionPipeline(model_name_or_path=weights)
            _pipelines_by_weights[weights] = pipeline
        return pipeline

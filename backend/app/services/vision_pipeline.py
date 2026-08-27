import logging
import os
from typing import Any, ClassVar, Dict, List, Tuple, Union

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

AREA_OBJECT_CLASSES = [
    "container",
    "shipping_container",
    "truck",
    "container_truck",
    "forklift",
    "crane",
    "car",
    "motorbike",
    "bicycle",
    "person",
]

OBJECT_VIETNAMESE_NAMES = {
    "container": "Container",
    "shipping_container": "Thùng container",
    "truck": "Xe tải",
    "container_truck": "Xe tải container",
    "forklift": "Xe nâng",
    "crane": "Xe cẩu",
    "car": "Xe con",
    "motorbike": "Xe máy",
    "bicycle": "Xe đạp",
    "person": "Người"
}

# Nhãn trả về từ YOLOv11s finetune. Runtime không còn prompt/open-vocabulary.
FINETUNE_CLASS_TO_CANONICAL = {
    "shipping container": "shipping_container",
    "freight container": "shipping_container",
    "cargo container box": "shipping_container",
    "container": "shipping_container",
    "container truck": "container",
    "container_truck": "container",
    "truck": "truck",
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
    Ultralytics YOLOv11s finetuned engine & zone evaluator.
    Loads weight models from backend/app/ai/weights/.
    Supports the area-monitoring classes exported by the finetuned checkpoint.
    """

    # Ngưỡng mặc định khi gọi trực tiếp mà không truyền cấu hình.
    # Giá trị thật lúc chạy lấy từ DETECTION_CONFIDENCE_THRESHOLD trong .env.
    DEFAULT_CONFIDENCE_THRESHOLD = 0.30
    DEFAULT_INFERENCE_THRESHOLD = 0.25
    DEFAULT_APPLICATION_THRESHOLD = 0.50
    DEFAULT_PER_CLASS_APPLICATION_THRESHOLDS: ClassVar[dict[str, float]] = {
        "person": 0.45,
        "motorbike": 0.45,
        "bicycle": 0.45,
        "forklift": 0.50,
        "truck": 0.50,
        "container_truck": 0.50,
        "car": 0.50,
        "crane": 0.50,
        "container": 0.55,
        "shipping_container": 0.55,
    }
    FOOTPRINT_OVERLAP_CLASSES: ClassVar[set[str]] = {"forklift", "truck", "container_truck", "car", "crane"}
    BOTTOM_CENTER_CLASSES: ClassVar[set[str]] = {"person", "motorbike", "bicycle"}
    BBOX_OVERLAP_CLASSES: ClassVar[set[str]] = {"shipping_container"}
    DETECT_ONLY_CLASSES: ClassVar[set[str]] = {"container", "shipping_container"}
    ZONE_RULE_ALIASES: ClassVar[dict[str, set[str]]] = {
        "container_truck": {"container"},
    }
    DEFAULT_FOOTPRINT_OVERLAP_RATIO = 0.15
    DEFAULT_CONTAINER_OVERLAP_RATIO = 0.25

    # Ultralytics mặc định iou=0.7, quá lỏng với cảnh này: một xe đầu kéo ở cổng cho ra
    # hai box lồng nhau (0.89 bao cả xe, 0.58 bao riêng rơ-moóc, IoU ~0.76).
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
        self.inference_threshold = min(self.DEFAULT_INFERENCE_THRESHOLD, self.confidence_threshold)
        self.application_threshold = self.DEFAULT_APPLICATION_THRESHOLD
        self.per_class_application_thresholds = dict(self.DEFAULT_PER_CLASS_APPLICATION_THRESHOLDS)
        self.model = None
        self.model_type = "yolov11s-finetune"
        self.classes = list(CANONICAL_8_OBJECT_CLASSES)
        self._initialize_model()

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

        try:
            from ultralytics import YOLO
            self.model = YOLO(model_source)
            self.model_type = "yolov11s-finetune"
            logger.info(f"Loaded YOLOv11s finetuned model from: {model_source}")
            return
        except Exception as e:
            logger.error(f"YOLOv11s finetuned model load error ({model_source}): {e}")

        self.model = None

    def update_custom_classes(self, new_classes: List[str]):
        """Compatibility no-op: finetuned weights define runtime detection classes."""
        combined_classes = list(self.classes)
        for cls_name in new_classes:
            if cls_name not in combined_classes:
                combined_classes.append(cls_name)
        self.classes = combined_classes

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

    @classmethod
    def class_application_threshold(cls, cls_name: str) -> float:
        return cls.DEFAULT_PER_CLASS_APPLICATION_THRESHOLDS.get(
            cls_name,
            cls.DEFAULT_APPLICATION_THRESHOLD,
        )

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
    def _normalize_bbox_xyxy(
        bbox: Tuple[float, float, float, float] | List[float],
    ) -> tuple[float, float, float, float]:
        b0, b1, b2, b3 = [float(v) for v in bbox]
        if b2 >= b0 and b3 >= b1:
            x1, y1, x2, y2 = b0, b1, b2, b3
        else:
            x1, y1, x2, y2 = b0, b1, b0 + b2, b1 + b3
        max_coord = max(abs(x1), abs(y1), abs(x2), abs(y2))
        if max_coord > 1.0:
            x1, y1, x2, y2 = x1 / 100.0, y1 / 100.0, x2 / 100.0, y2 / 100.0
        x1, x2 = sorted((max(0.0, min(1.0, x1)), max(0.0, min(1.0, x2))))
        y1, y2 = sorted((max(0.0, min(1.0, y1)), max(0.0, min(1.0, y2))))
        return (x1, y1, x2, y2)

    @classmethod
    def _bbox_bottom_center(cls, bbox: Tuple[float, float, float, float] | List[float]) -> tuple[float, float]:
        x1, _y1, x2, y2 = cls._normalize_bbox_xyxy(bbox)
        return ((x1 + x2) / 2.0, y2)

    @classmethod
    def _bbox_footprint_rect(cls, bbox: Tuple[float, float, float, float] | List[float]) -> tuple[float, float, float, float]:
        x1, y1, x2, y2 = cls._normalize_bbox_xyxy(bbox)
        height = max(0.0, y2 - y1)
        return (x1, max(y1, y2 - height * 0.35), x2, y2)

    @staticmethod
    def _normalize_polygon(polygon_points: List[Any]) -> list[tuple[float, float]]:
        raw_poly = [AIVisionPipeline.normalize_point(p) for p in polygon_points or []]
        if not raw_poly:
            return []
        max_coord = max(max(abs(pt[0]), abs(pt[1])) for pt in raw_poly)
        if max_coord > 1.0:
            return [(pt[0] / 100.0, pt[1] / 100.0) for pt in raw_poly]
        return raw_poly

    @staticmethod
    def _clip_polygon_against_rect(
        polygon: list[tuple[float, float]],
        rect: tuple[float, float, float, float],
    ) -> list[tuple[float, float]]:
        x_min, y_min, x_max, y_max = rect

        def clip_edge(points, inside, intersect):
            if not points:
                return []
            output = []
            previous = points[-1]
            previous_inside = inside(previous)
            for current in points:
                current_inside = inside(current)
                if current_inside:
                    if not previous_inside:
                        output.append(intersect(previous, current))
                    output.append(current)
                elif previous_inside:
                    output.append(intersect(previous, current))
                previous = current
                previous_inside = current_inside
            return output

        def vertical_intersection(a, b, x):
            ax, ay = a
            bx, by = b
            if bx == ax:
                return (x, ay)
            t = (x - ax) / (bx - ax)
            return (x, ay + t * (by - ay))

        def horizontal_intersection(a, b, y):
            ax, ay = a
            bx, by = b
            if by == ay:
                return (ax, y)
            t = (y - ay) / (by - ay)
            return (ax + t * (bx - ax), y)

        clipped = polygon
        clipped = clip_edge(clipped, lambda p: p[0] >= x_min, lambda a, b: vertical_intersection(a, b, x_min))
        clipped = clip_edge(clipped, lambda p: p[0] <= x_max, lambda a, b: vertical_intersection(a, b, x_max))
        clipped = clip_edge(clipped, lambda p: p[1] >= y_min, lambda a, b: horizontal_intersection(a, b, y_min))
        clipped = clip_edge(clipped, lambda p: p[1] <= y_max, lambda a, b: horizontal_intersection(a, b, y_max))
        return clipped

    @staticmethod
    def _polygon_area(points: list[tuple[float, float]]) -> float:
        if len(points) < 3:
            return 0.0
        area = 0.0
        for index, (x1, y1) in enumerate(points):
            x2, y2 = points[(index + 1) % len(points)]
            area += x1 * y2 - x2 * y1
        return abs(area) / 2.0

    @classmethod
    def _rect_polygon_overlap_ratio(
        cls,
        rect: tuple[float, float, float, float],
        polygon_points: List[Any],
    ) -> float:
        x1, y1, x2, y2 = rect
        rect_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        if rect_area <= 0:
            return 0.0
        polygon = cls._normalize_polygon(polygon_points)
        clipped = cls._clip_polygon_against_rect(polygon, rect)
        return max(0.0, min(1.0, cls._polygon_area(clipped) / rect_area))

    def evaluate_bbox_class_aware_in_zone(
        self,
        bbox: Tuple[float, float, float, float] | List[float],
        polygon_points: List[Any],
        object_class: str,
    ) -> dict[str, Any]:
        if object_class in self.DETECT_ONLY_CLASSES:
            return {
                "inside": False,
                "zone_eval_method": "none",
                "zone_overlap_ratio": None,
            }
        if object_class in self.BOTTOM_CENTER_CLASSES:
            point = self._bbox_bottom_center(bbox)
            return {
                "inside": self.point_in_polygon(point, polygon_points),
                "zone_eval_method": "bottom_center",
                "zone_overlap_ratio": None,
            }
        if object_class in self.FOOTPRINT_OVERLAP_CLASSES:
            rect = self._bbox_footprint_rect(bbox)
            ratio = self._rect_polygon_overlap_ratio(rect, polygon_points)
            return {
                "inside": ratio >= self.DEFAULT_FOOTPRINT_OVERLAP_RATIO,
                "zone_eval_method": "footprint_overlap",
                "zone_overlap_ratio": round(ratio, 4),
            }
        if object_class in self.BBOX_OVERLAP_CLASSES:
            ratio = self._rect_polygon_overlap_ratio(self._normalize_bbox_xyxy(bbox), polygon_points)
            return {
                "inside": ratio >= self.DEFAULT_CONTAINER_OVERLAP_RATIO,
                "zone_eval_method": "bbox_overlap_ratio",
                "zone_overlap_ratio": round(ratio, 4),
            }
        return {
            "inside": self.evaluate_bbox_center_in_zone(bbox, polygon_points),
            "zone_eval_method": "center_point_fallback",
            "zone_overlap_ratio": None,
        }

    @classmethod
    def zone_rule_matches_class(cls, object_class: str, rule_classes: list[str] | tuple[str, ...] | set[str]) -> bool:
        class_set = set(rule_classes or [])
        return object_class in class_set or bool(cls.ZONE_RULE_ALIASES.get(object_class, set()) & class_set)

    def map_raw_class_to_canonical(self, raw_cls_name: str) -> str | None:
        raw_key = raw_cls_name.lower().strip()
        raw_cls_lower = raw_key.replace("_", " ")
        cls_name = FINETUNE_CLASS_TO_CANONICAL.get(raw_key, FINETUNE_CLASS_TO_CANONICAL.get(raw_cls_lower, raw_cls_lower))
        if cls_name == "IGNORE":
            return None

        if cls_name in AREA_OBJECT_CLASSES:
            return cls_name
        if cls_name in self.classes:
            return cls_name
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

    def process_frame(
        self,
        frame_matrix,
        zones: List[Dict[str, Any]] = None,
        conf_threshold: float = None,
        inference_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs YOLO inference on frame matrix and evaluates Ray-Casting PIP zone violations.
        Filters out detections below specified confidence threshold.

        Bỏ trống conf_threshold thì dùng self.confidence_threshold, tức giá trị
        DETECTION_CONFIDENCE_THRESHOLD trong .env.
        """
        if conf_threshold is None:
            conf_threshold = self.confidence_threshold
        if inference_threshold is None:
            inference_threshold = min(self.inference_threshold, conf_threshold)
        detections = []
        if self.model is not None and frame_matrix is not None:
            try:
                results = self.model.predict(
                    frame_matrix,
                    conf=inference_threshold,
                    iou=self.DEFAULT_IOU_THRESHOLD,
                    agnostic_nms=True,
                    verbose=False,
                )
                # Lớp hợp lệ là các label đã biết từ checkpoint finetune và taxonomy
                # vùng bãi; nhãn ngoài danh mục bị bỏ, không đoán bừa.
                known_classes = set(AREA_OBJECT_CLASSES) | set(self.classes)

                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        conf = float(box.conf[0])
                        if conf < inference_threshold:
                            continue

                        cls_id = int(box.cls[0])
                        names = getattr(r, "names", None) or {}
                        raw_cls_name = names.get(cls_id)
                        if not raw_cls_name:
                            logger.warning(
                                f"Không tra được tên lớp cho cls_id={cls_id}, bỏ qua detection."
                            )
                            continue

                        # Model finetune có thể dùng snake_case hoặc space-separated labels.
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
                            "id": None,
                            "object_class": cls_name,
                            "raw_class": raw_cls_name,
                            "canonical_class": cls_name,
                            "vietnamese_name": OBJECT_VIETNAMESE_NAMES.get(cls_name, cls_name),
                            "confidence": round(conf, 3),
                            "bbox": pct_bbox,
                            "bbox_xyxy_norm": [round(v, 4) for v in norm_bbox],
                            "zone_eval_method": "none",
                            "zone_overlap_ratio": None,
                            "severity": 1,
                            "zone_violation": False,
                            "zone_name": None,
                            "zone_id": None,
                        }

                        if zones and cls_name not in self.DETECT_ONLY_CLASSES:
                            for zone in zones:
                                polygon = zone.get("vertices") or zone.get("polygon_points") or []
                                forbidden = zone.get("forbidden_classes") or zone.get("prohibited_object_types") or []
                                allowed = zone.get("allowed_classes") or zone.get("allowed_object_types") or []

                                evaluation = self.evaluate_bbox_class_aware_in_zone(
                                    norm_bbox, polygon, cls_name
                                )
                                if evaluation["inside"]:
                                    detection["zone_eval_method"] = evaluation["zone_eval_method"]
                                    detection["zone_overlap_ratio"] = evaluation["zone_overlap_ratio"]
                                    is_forbidden = self.zone_rule_matches_class(cls_name, forbidden)
                                    is_allowed = self.zone_rule_matches_class(cls_name, allowed)
                                    if is_forbidden or (allowed and not is_allowed):
                                        if conf >= self.class_application_threshold(cls_name):
                                            detection["zone_violation"] = True
                                            detection["severity"] = zone.get("severity", 3)
                                        else:
                                            detection["severity"] = 1
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

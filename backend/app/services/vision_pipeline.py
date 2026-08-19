import os
import logging
from typing import List, Tuple, Dict, Any, Union

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
    "container": "Xe container",
    "truck": "Xe tải",
    "forklift": "Xe nâng",
    "crane": "Xe cẩu",
    "car": "Xe con",
    "motorbike": "Xe máy",
    "bicycle": "Xe đạp",
    "person": "Người"
}

# COCO class mapping to canonical 8 classes
COCO_TO_CANONICAL = {
    "train": "container",
    "truck": "truck",
    "bus": "truck",
    "car": "car",
    "motorcycle": "motorbike",
    "bicycle": "bicycle",
    "person": "person",
    "bench": "forklift"
}

class AIVisionPipeline:
    """
    Ultralytics YOLO-World v2 Engine & Ray-Casting Point-in-Polygon Evaluator.
    Loads weight models from backend/app/ai/weights/.
    Supports 8 Object Classes (CR-001) & Open-Vocabulary Custom Object Detection.
    """

    def __init__(self, model_name_or_path: str = "yolov8s-worldv2.pt"):
        self.model_name_or_path = model_name_or_path
        self.model = None
        self.model_type = "yolo-world"
        self.classes = list(CANONICAL_8_OBJECT_CLASSES)
        self._initialize_model()

    def _resolve_model_path(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(current_dir))
        project_root = os.path.dirname(backend_dir)

        possible_paths = [
            os.path.join(backend_dir, "app", "ai", "weights", self.model_name_or_path),
            os.path.join(project_root, "backend", "app", "ai", "weights", self.model_name_or_path),
            os.path.join(backend_dir, "app", "ai", "weights", "yolov8n.pt"),
            self.model_name_or_path,
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return self.model_name_or_path

    def _initialize_model(self):
        model_source = self._resolve_model_path()
        logger.info(f"Attempting to load model weights from: {model_source}")
        
        # 1. Try loading YOLOWorld
        try:
            from ultralytics import YOLOWorld
            if os.path.exists(model_source) and "world" in model_source.lower():
                self.model = YOLOWorld(model_source)
                self.model.set_classes(self.classes)
                self.model_type = "yolo-world"
                logger.info(f"Loaded YOLO-World v2 model from: {model_source}")
                return
        except Exception as e:
            logger.warning(f"YOLO-World load error: {e}")

        # 2. Fallback to standard YOLOv8 (yolov8n.pt in weights directory)
        try:
            from ultralytics import YOLO
            yolov8n_path = os.path.join(os.path.dirname(model_source), "yolov8n.pt")
            if not os.path.exists(yolov8n_path):
                yolov8n_path = model_source
            if os.path.exists(yolov8n_path):
                self.model = YOLO(yolov8n_path)
                self.model_type = "yolov8"
                logger.info(f"Loaded YOLOv8 model from: {yolov8n_path}")
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
        if self.model and self.model_type == "yolo-world":
            try:
                self.model.set_classes(self.classes)
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
        xmin, ymin, xmax, ymax = bbox
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        return self.point_in_polygon((cx, cy), polygon_points)

    def process_frame(self, frame_matrix, zones: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Runs YOLO inference on frame matrix and evaluates Ray-Casting PIP zone violations.
        """
        detections = []
        if self.model is not None and frame_matrix is not None:
            try:
                results = self.model.predict(frame_matrix, conf=0.10, verbose=False)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        raw_cls_name = r.names[cls_id] if hasattr(r, "names") and cls_id in r.names else "person"
                        cls_name = COCO_TO_CANONICAL.get(raw_cls_name.lower(), raw_cls_name.lower())
                        
                        if cls_name not in CANONICAL_8_OBJECT_CLASSES:
                            cls_name = "container" if raw_cls_name.lower() in ("train", "box") else "person"

                        conf = float(box.conf[0])
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

                        detection = {
                            "object_class": cls_name,
                            "vietnamese_name": OBJECT_VIETNAMESE_NAMES.get(cls_name, cls_name),
                            "confidence": round(conf, 3),
                            "bbox": pct_bbox,
                            "severity": 1,
                            "zone_violation": False,
                            "zone_name": None,
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
                                        break
                                    else:
                                        detection["zone_name"] = zone.get("name", "Zone An Toàn")

                        detections.append(detection)
            except Exception as e:
                logger.error(f"Error in YOLO inference: {e}")
        return detections

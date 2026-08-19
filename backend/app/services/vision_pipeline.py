import os
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class AIVisionPipeline:
    """
    Ultralytics YOLO-World v2 Engine & Ray-Casting Point-in-Polygon Evaluator.
    Supports Open-Vocabulary Object Detection with static class embedding caching.
    """

    def __init__(self, model_name_or_path: str = "yolov8s-worldv2.pt"):
        self.model_name_or_path = model_name_or_path
        self.model = None
        self.classes = ["person", "forklift", "truck", "container", "car", "motorcycle"]
        self._initialize_model()

    def _resolve_model_path(self) -> str:
        possible_paths = [
            self.model_name_or_path,
            os.path.join("backend", "app", "ai", "weights", self.model_name_or_path),
            os.path.join(os.getcwd(), self.model_name_or_path),
            os.path.join(os.getcwd(), "backend", "app", "ai", "weights", self.model_name_or_path),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return self.model_name_or_path

    def _initialize_model(self):
        try:
            from ultralytics import YOLOWorld
            model_source = self._resolve_model_path()
            logger.info(f"Loading YOLO-World v2 model from: {model_source}")
            self.model = YOLOWorld(model_source)
            # Static Class Embedding Caching for Maximum FPS & Latency < 1s
            self.model.set_classes(self.classes)
            logger.info(f"YOLO-World set static classes cached: {self.classes}")
        except Exception as e:
            logger.warning(f"YOLO-World model load fallback (using simulation mode): {e}")
            self.model = None

    def update_custom_classes(self, new_classes: List[str]):
        """
        Dynamically updates prompt classes for REQ-007 Custom Label Tool.
        """
        self.classes = new_classes
        if self.model:
            try:
                self.model.set_classes(self.classes)
                logger.info(f"Updated YOLO-World cached classes: {self.classes}")
            except Exception as e:
                logger.error(f"Error setting custom classes: {e}")

    def point_in_polygon(self, point: Tuple[float, float], polygon_points: List[Tuple[float, float]]) -> bool:
        """
        Ray-Casting Algorithm for Point-in-Polygon zone check (ADR-002).
        Calculates if point (x, y) relative (0.0-1.0) is inside polygon_points.
        """
        if not polygon_points or len(polygon_points) < 3:
            return False

        x, y = point
        n = len(polygon_points)
        inside = False
        p1x, p1y = polygon_points[0]

        for i in range(n + 1):
            p2x, p2y = polygon_points[i % n]
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
        polygon_points: List[Tuple[float, float]]
    ) -> bool:
        """
        Calculates normalized BBox center point (cx, cy) and evaluates inside polygon zone.
        BBox format: (xmin, ymin, xmax, ymax)
        """
        xmin, ymin, xmax, ymax = bbox
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        return self.point_in_polygon((cx, cy), polygon_points)

    def process_frame(self, frame_matrix, zones: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Runs YOLO-World detection on frame matrix and evaluates zone violations.
        """
        detections = []
        if self.model is not None and frame_matrix is not None:
            try:
                results = self.model.predict(frame_matrix, conf=0.25, verbose=False)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        cls_name = self.classes[cls_id] if cls_id < len(self.classes) else "unknown"
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()

                        detection = {
                            "object_class": cls_name,
                            "confidence": round(conf, 3),
                            "bbox": [round(v, 1) for v in xyxy],
                            "severity": 1,
                            "zone_violation": False,
                            "zone_name": None,
                        }

                        # Evaluate against active zones if provided
                        if zones:
                            # Normalize bbox to 0.0-1.0 relative coordinates assuming frame size
                            h, w = frame_matrix.shape[:2]
                            norm_bbox = (xyxy[0] / w, xyxy[1] / h, xyxy[2] / w, xyxy[3] / h)
                            for zone in zones:
                                polygon = zone.get("polygon_points", [])
                                forbidden = zone.get("forbidden_classes", ["person", "car"])
                                if cls_name in forbidden and self.evaluate_bbox_center_in_zone(norm_bbox, polygon):
                                    detection["zone_violation"] = True
                                    detection["severity"] = zone.get("severity", 3)
                                    detection["zone_name"] = zone.get("name", "Vùng Cấm")
                                    break

                        detections.append(detection)
            except Exception as e:
                logger.error(f"Error in YOLO-World detection: {e}")
        return detections

import logging
import sys

def setup_logger(name: str = "sentri_ai"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger()

# Các service dùng logging.getLogger(__name__), tức tên "backend.app.services.*".
# Nếu chỉ cấu hình logger "sentri_ai" thì chúng propagate lên root logger — vốn không
# có handler và mặc định ở mức WARNING — nên mọi dòng INFO biến mất, kể cả
# "Loaded YOLO model from: ..." lúc khởi động. Cấu hình logger gốc của package thay
# vì root để không kéo theo log ồn ào của torch/ultralytics.
setup_logger("backend")

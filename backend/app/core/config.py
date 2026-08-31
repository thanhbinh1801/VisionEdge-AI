import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "db" / "sentriai.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

# Locate project root
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
project_root = os.path.dirname(backend_dir)

# .env được nạp qua model_config.env_file bên dưới, không qua load_dotenv():
# load_dotenv() ghi thẳng vào os.environ nên Settings(_env_file=None) không còn cô lập
# được nữa, và test_database_config sẽ đọc phải .env của máy đang chạy.


def _path_from_sqlite_url(parsed_path: str) -> Path:
    raw_path = unquote(parsed_path)
    if len(raw_path) >= 4 and raw_path[0] == "/" and raw_path[2] == ":":
        raw_path = raw_path[1:]
    elif raw_path.startswith("/./") or raw_path.startswith("/../"):
        raw_path = raw_path[1:]
    return Path(raw_path)


def _sqlite_url_from_path(path_value: str) -> str:
    db_path = Path(path_value)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return f"sqlite:///{db_path.resolve().as_posix()}"


def _canonicalize_sqlite_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url

    parsed = urlparse(database_url)
    if parsed.netloc:
        db_path = Path(f"//{parsed.netloc}{unquote(parsed.path)}")
    else:
        db_path = _path_from_sqlite_url(parsed.path)

    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    return f"sqlite:///{db_path.resolve().as_posix()}"


def resolve_from_project_root(path: str) -> str:
    """
    Quy đổi đường dẫn tương đối theo gốc dự án thay vì theo thư mục làm việc.

    Dev server chạy bằng `cd backend && python main.py` nên CWD là backend/,
    còn pytest chạy từ gốc repo. Nếu để nguyên đường dẫn tương đối thì cùng một
    giá trị trong .env sẽ trỏ vào hai chỗ khác nhau — đó là lý do trước đây
    sinh ra hai file sentri_ai.db riêng biệt.
    """
    if not path:
        return path
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(project_root, path))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(PROJECT_ROOT / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "SentriAI Mini Backend"
    API_V1_STR: str = "/api/v1"
    PROJECT_ROOT: str = project_root

    DATABASE_URL: str = DEFAULT_DATABASE_URL
    SENTRIAI_DB_PATH: str | None = None

    CLIPS_DIR: str = "./data/clips"
    CROPS_DIR: str = "./data/crops"
    VIDEOS_DIR: str = "./data/video"
    IMAGES_DIR: str = "./data/images"

    # Ghi đè video cho từng camera; để trống thì dùng ánh xạ mặc định trong
    # backend/app/api/v1/events.py.
    VIDEO_BAI_KIEM_PATH: str = ""
    VIDEO_GATE_01_PATH: str = ""
    VIDEO_XUONG_AN_NINH_PATH: str = ""

    # Ngưỡng tin cậy tối thiểu để giữ lại một detection của YOLOv11s finetune.
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.30

    # Tên file weights (nằm trong backend/app/ai/weights/) hoặc đường dẫn tuyệt đối
    # tới file .pt dùng cho Area Zone Monitoring.
    # Mặc định dùng YOLOv11s finetune trên dataset cảng; runtime không còn nạp
    # open-vocabulary hoặc fallback sang model COCO.
    DETECTION_MODEL_WEIGHTS: str = "sentri-yolo11s.pt"

    # Ghi đè weights cho từng camera: {"camera_id": "ten-file.pt"}. Camera không khai
    # báo ở đây dùng DETECTION_MODEL_WEIGHTS.
    #
    # GATE-01 cần bộ khác vì sentri-yolo11s được finetune trên ảnh bãi container chụp
    # từ xa, còn camera cổng (Cvao-Bien-L2) đặt ngang tầm cản trước và xe chiếm gần
    # trọn khung. Đo trên clip cổng: sentri-yolo11s gán đầu kéo thành 'motorbike' và
    # rỗng ở nhiều frame, yolov8s-worldv2 trả truck/container 0.45-0.69 đều đặn.
    # Trên footage cổng cũ khoảng cách còn lớn hơn: 1 box/6 frame so với 14.
    DETECTION_MODEL_WEIGHTS_BY_CAMERA: str = '{"GATE-01": "yolov8s-worldv2.pt"}'

    EVENT_COOLDOWN_SECONDS: int = 15

    # Ngưỡng tin cậy tối thiểu để chấp nhận một chuỗi biển số do EasyOCR đọc được
    # (REQ-001). Dưới ngưỡng thì tính là "không đọc được" thay vì ghi một biển số
    # sai vào bảng events — một biển số sai còn tệ hơn một ô trống trên dashboard.
    #
    # Hạ từ 0.70 xuống 0.50: camera GATE-01 nhìn xe ở góc nghiêng nên biển số bị méo
    # phối cảnh, EasyOCR hiếm khi vượt 0.70 dù đọc đúng ký tự. Định dạng biển số Việt
    # Nam (_PLATE_STRUCTURE_RE) vẫn là hàng rào chính chặn chuỗi rác, ngưỡng này chỉ
    # là hàng rào thứ hai — nên nới được mà không kéo theo biển số bịa.
    OCR_CONFIDENCE_THRESHOLD: float = 0.50

    # Sàn tin cậy cứng cho một biển số được coi là "đọc thành công". Áp cho MỌI đường
    # ra kết quả, kể cả khớp roster — không có biển số nào dưới mức này được lên UI hay
    # vào bảng events. Trước khi có sàn này, một mảnh rác khớp roster ở 0.094 đã ghi
    # được hai lượt xe ma vào CSDL.
    MIN_ACCEPTED_PLATE_CONFIDENCE: float = 0.50

    # Sổ đăng ký biển số của các xe xuất hiện trong footage camera cổng, phân tách bằng
    # dấu phẩy. Dùng để hoàn thiện một lượt đọc dở dang: khi biển chỉ ~30px trên khung
    # hình, EasyOCR thường chỉ bóc được vài ký tự chứ không đủ 7-9 ký tự để khớp định dạng.
    #
    # Đây KHÔNG phải cơ chế sinh biển số: match_roster_plate() bắt buộc phải có ít nhất
    # 3 ký tự liên tiếp do OCR thực sự đọc được thì mới khớp, confidence bị chiết khấu
    # theo tỉ lệ ký tự có bằng chứng, và vẫn phải vượt MIN_ACCEPTED_PLATE_CONFIDENCE.
    #
    # Để TRỐNG theo mặc định. Danh sách chỉ có giá trị khi biển số thật của footage đã
    # được xác minh; điền biển đoán mò vào đây là cách nhanh nhất để sinh lượt xe ma.
    GATE_PLATE_ROSTER: str = ""

    # LPR Trigger Box: vùng chữ nhật cố định [x, y, w, h] tính theo phần trăm khung hình,
    # khoá theo zone_id của làn IN. Chỉ có tác dụng với nhánh EasyOCR dự phòng.
    #
    # Để TRỐNG theo mặc định. Ô ngắm cố định giả định xe luôn dừng đúng một chỗ; đo trên
    # clip camera biển số thì tấm biển rơi vào x 35-50% ở lượt này và x 79-87% ở lượt
    # khác, tuỳ xe dừng nông hay sâu — không ô cố định nào bao được cả hai. Đường đọc
    # chính (plate_detector khoanh theo màu) không cần ô này.
    GATE_LPR_TRIGGER_BOXES: str = "{}"

    # Vùng quét biển số [x, y, w, h] tính theo phần trăm khung hình, dùng khi đọc biển
    # mà không bám theo bbox của một chiếc xe cụ thể.
    #
    # Đây KHÔNG phải zone làn. Hai thứ bám hai vật khác nhau: zone làn bám tâm bbox xe
    # (đo được ở x 27-52, y 17-51), còn vùng này bám vị trí tấm biển (x 32-90, y 5-33) —
    # tấm biển chỉ nằm ở nửa trên khung hình, toàn bộ mặt đường phía dưới không bao giờ
    # có biển. Gộp hai thứ làm một thì hoặc mất biển, hoặc quét thừa nửa khung hình.
    #
    # Đo trên clip cổng, so số biển đọc được với số vùng nhiễu phải gọi OCR:
    #   toàn khung        51/51 biển, 133 nhiễu, 100% diện tích
    #   x 25-92, y 0-38   51/51 biển,  58 nhiễu,  25% diện tích  <- đang dùng
    #   x 25-80, y 0-38   50/51 biển,  22 nhiễu,  21% diện tích
    # Hẹp hơn nữa thì bắt đầu cắt mất pha xe rời cổng, nơi tấm biển dạt sang phải.
    #
    # Để trống thì quét cả khung hình.
    GATE_PLATE_SCAN_REGION: str = "[25.0, 0.0, 67.0, 38.0]"

    # Cửa sổ chống trùng cho sự kiện LPR_PASSAGE: một lượt xe qua cổng nằm trong khung
    # hình nhiều giây liền, mỗi frame lại đọc ra cùng một biển số. Không có cooldown thì
    # một chiếc xe sinh hàng chục event giống hệt nhau.
    LPR_COOLDOWN_SECONDS: int = 12

    # Số lần một chuỗi biển số phải được đọc ra trong LPR_CONFIRMATION_WINDOW_SECONDS
    # thì mới được công nhận là một lượt xe. Đặt 1 để tắt.
    #
    # Recognizer đọc sai ở vài frame lẻ và sai với confidence cao — đo được các chuỗi ma
    # ở 0.951, 0.978 và 0.920, nằm lọt giữa dải của những lần đọc đúng. Siết ngưỡng
    # confidence không tách được chúng; thứ tách được là số lần lặp lại.
    #
    # Vì sao là 2 chứ không cao hơn. Đếm số phiếu mỗi chuỗi ở đúng nhịp chạy thật
    # (~1.4 lần/giây) trên trọn clip cổng:
    #     15H-190.62  19    15H-322.81  19    35H-093.47  14
    #     15C-054.62  13    15H-032.03   3  <- biển hai dòng bị đồng hồ camera đè
    #     mọi chuỗi ma quan sát được: đúng 1 phiếu
    # Chiếc 15H-032.03 chỉ đọc thành công ở ~3% số frame, nên nó là trần thực tế: mức 4
    # đã làm mất hẳn xe đó, mức 3 vừa khít không còn biên dự phòng. Mức 2 loại sạch mọi
    # chuỗi ma đã gặp mà vẫn giữ gấp đôi biên an toàn cho ca yếu nhất.
    #
    # Đánh đổi còn lại: một chuỗi ma lặp đúng hai lần liên tiếp sẽ lọt. Chưa quan sát
    # thấy ca nào như vậy; nếu gặp thì cách sửa đúng là gom các chuỗi lệch nhau một ký
    # tự về cùng một nhóm rồi lấy chuỗi nhiều phiếu nhất, chứ không phải nâng mức này.
    LPR_MIN_CONFIRMATIONS: int = 2

    # Cửa sổ trượt để đếm số lần đọc ở trên. Phải đủ dài để một chiếc xe dừng ở bốt kịp
    # được đọc đủ số lần: vòng nhận dạng chạy mỗi ~0.7 giây, xe nằm trong khung nhiều
    # giây, nên 20 giây là dư dả. Quá ngắn thì biển thật cũng không kịp gom đủ phiếu.
    LPR_CONFIRMATION_WINDOW_SECONDS: float = 20.0

    VIDEO_PATH: str = ""
    DEMO_MODE: bool = False
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    # Google Gemini cho nhánh LLM Text-to-SQL của trợ lý (ADR-004).
    # Để trống thì qa_agent chạy thẳng Rule Engine, không gọi mạng.
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    @field_validator(
        "CLIPS_DIR", "CROPS_DIR", "VIDEOS_DIR", "IMAGES_DIR",
        "VIDEO_BAI_KIEM_PATH", "VIDEO_GATE_01_PATH", "VIDEO_XUONG_AN_NINH_PATH",
    )
    @classmethod
    def _absolutize(cls, value: str) -> str:
        return resolve_from_project_root(value)

    @field_validator("DATABASE_URL")
    @classmethod
    def _absolutize_sqlite_url(cls, value: str) -> str:
        """Neo file SQLite vào gốc dự án để CWD không quyết định dùng DB nào."""
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        raw_path = value[len(prefix):]
        if raw_path.startswith(":memory:") or not raw_path:
            return value
        return prefix + resolve_from_project_root(raw_path).replace("\\", "/")

    @field_validator("DETECTION_CONFIDENCE_THRESHOLD", "OCR_CONFIDENCE_THRESHOLD")
    @classmethod
    def _check_confidence(cls, value: float, info) -> float:
        if not 0.0 < value < 1.0:
            raise ValueError(
                f"{info.field_name} phải nằm trong khoảng (0, 1), nhận được {value}"
            )
        return value

    @field_validator("LPR_COOLDOWN_SECONDS")
    @classmethod
    def _check_lpr_cooldown(cls, value: int) -> int:
        if not 10 <= value <= 15:
            raise ValueError(
                f"LPR_COOLDOWN_SECONDS phải nằm trong khoảng 10-15 giây, nhận được {value}"
            )
        return value

    @model_validator(mode="after")
    def normalize_paths(self) -> "Settings":
        if self.SENTRIAI_DB_PATH and self.DATABASE_URL == DEFAULT_DATABASE_URL:
            self.DATABASE_URL = _sqlite_url_from_path(self.SENTRIAI_DB_PATH)
        else:
            self.DATABASE_URL = _canonicalize_sqlite_url(self.DATABASE_URL)

        clips_path = Path(self.CLIPS_DIR)
        if not clips_path.is_absolute():
            resolved_clips = (PROJECT_ROOT / clips_path).resolve()
            if not resolved_clips.exists() and (PROJECT_ROOT / "backend" / clips_path).exists():
                resolved_clips = (PROJECT_ROOT / "backend" / clips_path).resolve()
            self.CLIPS_DIR = str(resolved_clips)

        crops_path = Path(self.CROPS_DIR)
        if not crops_path.is_absolute():
            resolved_crops = (PROJECT_ROOT / crops_path).resolve()
            if not resolved_crops.exists() and (PROJECT_ROOT / "backend" / crops_path).exists():
                resolved_crops = (PROJECT_ROOT / "backend" / crops_path).resolve()
            self.CROPS_DIR = str(resolved_crops)

        return self

    def gate_plate_roster(self) -> list[str]:
        """Tách GATE_PLATE_ROSTER thành danh sách biển số, bỏ khoảng trắng và mục rỗng."""
        return [plate.strip() for plate in self.GATE_PLATE_ROSTER.split(",") if plate.strip()]

    def gate_lpr_trigger_boxes(self) -> dict[str, list[float]]:
        """Bảng zone_id -> [x, y, w, h] phần trăm. JSON hỏng thì tắt trigger box, không sập."""
        try:
            raw = json.loads(self.GATE_LPR_TRIGGER_BOXES or "{}")
        except (ValueError, TypeError):
            return {}
        if not isinstance(raw, dict):
            return {}

        boxes: dict[str, list[float]] = {}
        for zone_id, box in raw.items():
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            try:
                values = [float(v) for v in box]
            except (TypeError, ValueError):
                continue
            if values[2] > 0 and values[3] > 0:
                boxes[str(zone_id)] = values
        return boxes

    def gate_plate_scan_region(self) -> list[float] | None:
        """Vùng quét biển [x, y, w, h] phần trăm, hoặc None nếu quét cả khung hình."""
        try:
            raw = json.loads(self.GATE_PLATE_SCAN_REGION or "null")
        except (ValueError, TypeError):
            return None
        if not isinstance(raw, (list, tuple)) or len(raw) != 4:
            return None
        try:
            values = [float(v) for v in raw]
        except (TypeError, ValueError):
            return None
        if values[2] <= 0 or values[3] <= 0:
            return None
        return values

    def detection_weights_for(self, camera_id: str | None) -> str:
        """Weights YOLO của một camera. JSON hỏng thì lùi về weights chung, không sập."""
        if not camera_id:
            return self.DETECTION_MODEL_WEIGHTS
        try:
            raw = json.loads(self.DETECTION_MODEL_WEIGHTS_BY_CAMERA or "{}")
        except (ValueError, TypeError):
            return self.DETECTION_MODEL_WEIGHTS
        if not isinstance(raw, dict):
            return self.DETECTION_MODEL_WEIGHTS
        weights = raw.get(str(camera_id))
        return str(weights) if weights else self.DETECTION_MODEL_WEIGHTS

    def video_path_override(self, camera_id: str) -> Optional[str]:
        """Trả về video ghi đè cho camera nếu .env có khai báo và file tồn tại."""
        attr = "VIDEO_" + camera_id.replace("-", "_").upper() + "_PATH"
        path = getattr(self, attr, "")
        if path and os.path.exists(path):
            return path
        return None


settings = Settings()

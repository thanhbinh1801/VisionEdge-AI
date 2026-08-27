import os
import sys
from pathlib import Path

# Gốc repo, neo theo vị trí file này thay vì CWD: pytest có thể chạy từ repo root
# hoặc từ backend/, nên mọi đường dẫn tài nguyên phải tuyệt đối.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# init_db() bỏ qua schema trong im lặng nếu đường dẫn không tồn tại, nên đường dẫn
# tương đối "docs/contracts/db/schema.sql" sẽ tạo ra database rỗng mà không báo lỗi.
SCHEMA_SQL_PATH = PROJECT_ROOT / "docs" / "contracts" / "db" / "schema.sql"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

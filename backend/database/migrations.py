import sqlite3
from datetime import datetime


CR004_VERSION = "1.2.0-cr004-object-labeling"

CR005_VERSION = "1.3.0-cr005-object-class-key-normalization"

# 8 khoá lớp chuẩn — giá trị hợp lệ duy nhất của `events.object_class`.
_CANONICAL_CLASS_KEYS = (
    "container",
    "truck",
    "forklift",
    "crane",
    "car",
    "motorbike",
    "bicycle",
    "person",
)

# Tên hiển thị (và các biến thể người dùng/pipeline từng ghi nhầm) → khoá lớp.
# Xếp theo thứ tự giảm dần độ dài khi so khớp chuỗi con, để "xe container" không
# bị "xe con" nuốt mất.
_DISPLAY_NAME_TO_KEY = {
    "container": "container",
    "xe container": "container",
    "thung container": "container",
    "xe tai": "truck",
    "xe nang": "forklift",
    "xe cau": "crane",
    "xe con": "car",
    "xe hoi": "car",
    "o to": "car",
    "xe may": "motorbike",
    "xe gan may": "motorbike",
    "xe dap": "bicycle",
    "nguoi": "person",
}


def _fold(value: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường, để so khớp không phụ thuộc cách gõ."""
    import unicodedata

    lowered = str(value).strip().lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize_object_class(raw: str | None) -> str | None:
    """
    Quy một giá trị `object_class` bất kỳ về khoá lớp tiếng Anh.

    Trả về `None` khi không nhận ra — caller phải giữ nguyên giá trị cũ thay vì
    đoán bừa, vì ghi sai khoá còn tệ hơn để nguyên dữ liệu bẩn.

    Xử lý được cả các giá trị đã bị pipeline cũ ghi kèm định danh phương tiện,
    ví dụ "Xe nâng FL-01" hay "Xe container 15R-158.45".
    """
    if raw is None:
        return None

    folded = _fold(raw)
    if not folded:
        return None
    if folded in _CANONICAL_CLASS_KEYS:
        return folded
    if folded in _DISPLAY_NAME_TO_KEY:
        return _DISPLAY_NAME_TO_KEY[folded]

    # Giá trị bẩn dạng "<tên lớp> <mã phương tiện>": so khớp chuỗi con, ưu tiên
    # tên dài nhất để "xe container ..." không rơi nhầm vào "xe con".
    for name in sorted(_DISPLAY_NAME_TO_KEY, key=len, reverse=True):
        if name in folded:
            return _DISPLAY_NAME_TO_KEY[name]
    for key in sorted(_CANONICAL_CLASS_KEYS, key=len, reverse=True):
        if key in folded:
            return key
    return None


def apply_cr005_migration(raw_conn) -> None:
    """
    CR-005: `events.object_class` lưu khoá lớp tiếng Anh, không lưu tên hiển thị.

    Pipeline cũ ghi thẳng `vietnamese_name` vào cột này, nên mọi bộ lọc dạng
    `WHERE object_class = 'forklift'` đều trả 0 dòng dù dữ liệu có sẵn. Migration
    quy các bản ghi cũ về khoá chuẩn; giá trị không nhận ra được giữ nguyên.
    """
    cursor = raw_conn.cursor()
    try:
        rows = cursor.execute(
            "SELECT DISTINCT object_class FROM events WHERE object_class IS NOT NULL"
        ).fetchall()
    except sqlite3.OperationalError:
        # Bảng events chưa tồn tại (DB mới tinh) — không có gì để chuẩn hoá.
        cursor.close()
        return

    for (current,) in rows:
        if current in _CANONICAL_CLASS_KEYS:
            continue
        normalized = normalize_object_class(current)
        if normalized is None or normalized == current:
            continue
        cursor.execute(
            "UPDATE events SET object_class = ? WHERE object_class = ?",
            (normalized, current),
        )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_object_class ON events(object_class)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type_timestamp ON events(event_type, timestamp DESC)")
    cursor.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
        (CR005_VERSION, "CR-005 normalize events.object_class to canonical keys", datetime.utcnow().isoformat()),
    )
    raw_conn.commit()
    cursor.close()


def apply_cr004_migration(raw_conn) -> None:
    cursor = raw_conn.cursor()
    _add_missing_columns(cursor, "custom_labels", {
        "label_key": "VARCHAR(128)",
        "label_type": "VARCHAR(16) NOT NULL DEFAULT 'custom'",
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "deleted_at": "DATETIME",
    })
    _add_missing_columns(cursor, "dataset_sources", {
        "storage_path": "VARCHAR(512)",
        "public_url": "VARCHAR(512)",
        "original_filename": "VARCHAR(255)",
        "mime_type": "VARCHAR(128)",
        "file_size_bytes": "INTEGER",
        "sha256": "VARCHAR(64)",
        "fps": "FLOAT",
        "width": "INTEGER",
        "height": "INTEGER",
        "import_status": "VARCHAR(32) NOT NULL DEFAULT 'ready'",
        "import_error": "TEXT",
        "updated_at": "DATETIME",
    })
    _add_missing_columns(cursor, "bbox_samples", {
        "frame_timestamp_seconds": "FLOAT",
        "coordinate_space": "VARCHAR(32) NOT NULL DEFAULT 'percent_0_100'",
        "updated_at": "DATETIME",
    })
    cursor.execute("UPDATE custom_labels SET label_key = lower(trim(label_name)) WHERE label_key IS NULL OR trim(label_key) = ''")
    cursor.execute("UPDATE dataset_sources SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)")
    cursor.execute("UPDATE bbox_samples SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)")
    cursor.execute("UPDATE bbox_samples SET coordinate_space = 'percent_0_100' WHERE coordinate_space IS NULL")
    _seed_system_labels(cursor)
    _create_indexes(cursor)
    cursor.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
        (CR004_VERSION, "CR-004 real object labeling storage migration", datetime.utcnow().isoformat()),
    )
    raw_conn.commit()
    cursor.close()


def _add_missing_columns(cursor: sqlite3.Cursor, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, ddl in columns.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def _seed_system_labels(cursor: sqlite3.Cursor) -> None:
    rows = [
        ("lbl_system_container", "container", "Container", "system", "vehicle_shape"),
        ("lbl_system_truck", "truck", "Xe tải", "system", "vehicle_shape"),
        ("lbl_system_forklift", "forklift", "Xe nâng", "system", "vehicle_shape"),
        ("lbl_system_crane", "crane", "Xe cẩu", "system", "vehicle_shape"),
        ("lbl_system_car", "car", "Xe con", "system", "vehicle_shape"),
        ("lbl_system_motorbike", "motorbike", "Xe máy", "system", "vehicle_shape"),
        ("lbl_system_bicycle", "bicycle", "Xe đạp", "system", "vehicle_shape"),
        ("lbl_system_person", "person", "Người", "system", "person"),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO custom_labels
            (id, label_key, label_name, label_type, category, sample_count, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        rows,
    )


def _create_indexes(cursor: sqlite3.Cursor) -> None:
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_object_labels_label_key ON custom_labels(label_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_object_labels_active_type_key ON custom_labels(is_active, label_type, label_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dataset_sources_created_at ON dataset_sources(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dataset_sources_sha256 ON dataset_sources(sha256)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bbox_samples_source_frame ON bbox_samples(source_id, frame_index, created_at DESC)")

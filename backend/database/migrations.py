import sqlite3
from datetime import datetime


CR004_VERSION = "1.2.0-cr004-object-labeling"


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

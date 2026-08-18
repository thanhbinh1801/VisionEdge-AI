from typing import List, Optional
from backend.db.connection import get_db_connection
from backend.db.models import EventModel, VehicleModel, ZoneModel, CameraModel, CustomLabelModel

def get_all_events(limit: int = 50, camera_id: Optional[str] = None, severity: Optional[int] = None) -> List[dict]:
    conn = get_db_connection()
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    if camera_id:
        query += " AND camera_id = ?"
        params.append(camera_id)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_event(event: EventModel) -> str:
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO events (id, camera_id, zone_id, event_type, severity, license_plate, ocr_confidence, object_class, snapshot_path, clip_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.id, event.camera_id, event.zone_id, event.event_type,
            event.severity, event.license_plate, event.ocr_confidence,
            event.object_class, event.snapshot_path, event.clip_path
        )
    )
    conn.commit()
    conn.close()
    return event.id

def correct_event_plate(event_id: str, corrected_plate: str) -> bool:
    conn = get_db_connection()
    cursor = conn.execute(
        """
        UPDATE events
        SET corrected_plate = ?, is_corrected = 1
        WHERE id = ?
        """,
        (corrected_plate, event_id)
    )
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_vehicle(license_plate: str) -> Optional[dict]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM vehicles WHERE license_plate = ?", (license_plate,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_zones_by_camera(camera_id: str) -> List[dict]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM zones WHERE camera_id = ?", (camera_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

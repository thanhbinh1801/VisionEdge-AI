from fastapi import APIRouter
from typing import List
from datetime import datetime
from app.models.schemas.event import EventResponse

router = APIRouter()

@router.get("", response_model=List[EventResponse])
def get_events(limit: int = 20):
    """
    Query recent event logs.
    """
    return [
        EventResponse(
            id="evt-001",
            timestamp=datetime.utcnow(),
            camera_id="GATE-01",
            camera_name="Cổng Vào GATE-01",
            zone_id=None,
            zone_name=None,
            event_type="LPR",
            severity=1,
            plate_number="29A-888.88",
            object_class="Truck",
            confidence=0.985,
            crop_url="/media/crops/crop_001.jpg",
            video_clip_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            status="NEW"
        ),
        EventResponse(
            id="evt-002",
            timestamp=datetime.utcnow(),
            camera_id="BAI-KIEM",
            camera_name="Bãi Kiểm BAI-KIEM",
            zone_id="zone-01",
            zone_name="Vùng Cấm Bãi Kiểm",
            event_type="ZONE_INTRUSION",
            severity=3,
            plate_number=None,
            object_class="Person",
            confidence=0.942,
            crop_url="/media/crops/crop_002.jpg",
            video_clip_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            status="NEW"
        )
    ]

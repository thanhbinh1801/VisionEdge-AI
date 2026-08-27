import os

import pytest

from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.tests.conftest import SCHEMA_SQL_PATH
from backend.database.models import Camera, Zone
from backend.database.repository import CameraRepository, CustomLabelRepository, DatasetError, DatasetRepository, ZoneRepository


TEST_DB_URL = "sqlite:///./test_dataset_zone_sync.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path=str(SCHEMA_SQL_PATH), target_engine=engine)
    yield engine
    engine.dispose()
    if os.path.exists("test_dataset_zone_sync.db"):
        os.remove("test_dataset_zone_sync.db")


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def _zone(db_session):
    CameraRepository(db_session).create(Camera(id="CAM-ZSYNC", name="Sync Cam", location="Yard", stream_url="url"))
    return ZoneRepository(db_session).create(Zone(
        id="zone-sync-1",
        camera_id="CAM-ZSYNC",
        name="Sync Zone",
        vertices=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
        allowed_classes=["car"],
        forbidden_classes=["truck"],
    ))


def test_create_restore_and_sync_append_custom_label_keys(db_session):
    zone = _zone(db_session)
    label_repo = CustomLabelRepository(db_session)
    dataset_repo = DatasetRepository(db_session)
    label = label_repo.create_custom("Ao phan quang", "person")
    sync = dataset_repo.sync_custom_labels_to_zones()
    db_session.commit()
    db_session.refresh(zone)

    assert label.label_key == "ao phan quang"
    assert "ao phan quang" in zone.forbidden_classes
    assert sync["default_rule"] == "forbidden"
    assert "zone-sync-1" in sync["affected_zones"]

    with pytest.raises(DatasetError) as exc:
        label_repo.soft_delete_custom(label.id)
    assert exc.value.code == "LABEL_IN_USE_BY_ZONE"


def test_rename_custom_label_updates_zone_rules(db_session):
    zone = _zone(db_session)
    label_repo = CustomLabelRepository(db_session)
    dataset_repo = DatasetRepository(db_session)
    label = label_repo.create_custom("Vung cam rieng", "vehicle_shape")
    dataset_repo.sync_custom_labels_to_zones()
    db_session.commit()

    label, old_key = label_repo.update_custom(label.id, label_name="Khu hang nang")
    dataset_repo.rename_label_in_zones(old_key, label.label_key)
    dataset_repo.sync_custom_labels_to_zones()
    db_session.commit()
    db_session.refresh(zone)

    assert "vung cam rieng" not in zone.forbidden_classes
    assert "khu hang nang" in zone.forbidden_classes


def test_duplicate_label_names_are_case_insensitive(db_session):
    repo = CustomLabelRepository(db_session)
    repo.create_custom("Xe Keo Hang", "vehicle_shape")
    db_session.commit()

    with pytest.raises(DatasetError) as exc:
        repo.create_custom("  xe keo hang  ", "vehicle_shape")
    assert exc.value.code == "DUPLICATE_LABEL_NAME"

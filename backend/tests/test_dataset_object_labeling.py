import os

import pytest

from backend.database.engine import SessionLocal, get_sqlite_engine, init_db
from backend.tests.conftest import SCHEMA_SQL_PATH
from backend.database.models import Camera, DatasetSource, Zone
from backend.database.repository import CameraRepository, CustomLabelRepository, DatasetError, DatasetRepository, ZoneRepository


TEST_DB_URL = "sqlite:///./test_dataset_object_labeling.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = get_sqlite_engine(TEST_DB_URL)
    init_db(schema_sql_path=str(SCHEMA_SQL_PATH), target_engine=engine)
    yield engine
    engine.dispose()
    if os.path.exists("test_dataset_object_labeling.db"):
        os.remove("test_dataset_object_labeling.db")


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def _source(repo: DatasetRepository, source_id: str = "src_img_01"):
    return repo.create_source(DatasetSource(
        id=source_id,
        name="frame.jpg",
        kind="img",
        url=f"/media/dataset/{source_id}/source.jpg",
        storage_path=f"backend/data/dataset/{source_id}/source.jpg",
        public_url=f"/media/dataset/{source_id}/source.jpg",
        original_filename="frame.jpg",
        mime_type="image/jpeg",
        file_size_bytes=10,
        sha256="a" * 64,
        total_frames=1,
        width=100,
        height=100,
        import_status="ready",
    ))


def test_system_labels_are_seeded_and_locked(db_session):
    repo = CustomLabelRepository(db_session)
    labels = repo.get_all()
    db_session.commit()

    system_ids = {label.id for label in labels if label.label_type == "system"}
    assert len(system_ids) == 8

    with pytest.raises(DatasetError) as exc:
        repo.update_custom("lbl_system_forklift", label_name="Forklift 2")
    assert exc.value.code == "SYSTEM_LABEL_LOCKED"


def test_batch_samples_are_atomic_and_recompute_counts(db_session):
    label_repo = CustomLabelRepository(db_session)
    dataset_repo = DatasetRepository(db_session)
    label_repo.seed_system_labels()
    label = label_repo.create_custom("Ao phan quang", "person")
    source = _source(dataset_repo)
    source_id = source.id
    label_id = label.id
    db_session.commit()

    with pytest.raises(DatasetError):
        dataset_repo.save_samples_batch([
            {"label_id": label_id, "source_id": source_id, "x": 5, "y": 5, "w": 10, "h": 10},
            {"label_id": label_id, "source_id": source_id, "x": 95, "y": 95, "w": 10, "h": 10},
        ])
    db_session.rollback()
    assert dataset_repo.get_samples(source_id=source_id) == []

    label = label_repo.create_custom("Ao phan quang 2", "person")
    source = _source(dataset_repo, "src_img_02")
    label_id = label.id
    source_id = source.id
    db_session.commit()
    saved = dataset_repo.save_samples_batch([
        {"label_id": label_id, "source_id": source_id, "x": 5, "y": 5, "w": 10, "h": 10}
    ])
    assert len(saved) == 1
    assert saved[0].frame_index == 0
    label = label_repo.get_by_id(label_id)
    assert label.sample_count == 1

    dataset_repo.delete_sample(saved[0].id)
    label = label_repo.get_by_id(label_id)
    db_session.refresh(label)
    assert label.sample_count == 0


def test_inactive_label_cannot_be_used_for_samples(db_session):
    label_repo = CustomLabelRepository(db_session)
    dataset_repo = DatasetRepository(db_session)
    label = label_repo.create_custom("Hang de vo", "vehicle_shape")
    source = _source(dataset_repo)
    db_session.commit()

    label_repo.soft_delete_custom(label.id)
    db_session.commit()

    with pytest.raises(DatasetError) as exc:
        dataset_repo.save_samples_batch([
            {"label_id": label.id, "source_id": source.id, "x": 5, "y": 5, "w": 10, "h": 10}
        ])
    assert exc.value.code == "LABEL_INACTIVE"


def test_delete_source_removes_samples_and_recomputes_counts(db_session):
    label_repo = CustomLabelRepository(db_session)
    dataset_repo = DatasetRepository(db_session)
    label = label_repo.create_custom("Pallet lech", "vehicle_shape")
    source = _source(dataset_repo)
    db_session.commit()

    saved = dataset_repo.save_samples_batch([
        {"label_id": label.id, "source_id": source.id, "x": 5, "y": 5, "w": 10, "h": 10},
        {"label_id": label.id, "source_id": source.id, "x": 20, "y": 20, "w": 10, "h": 10},
    ])
    assert len(saved) == 2
    db_session.refresh(label)
    assert label.sample_count == 2

    deleted_source, affected_label_ids, deleted_sample_count = dataset_repo.delete_source(source.id)

    assert deleted_source.id == source.id
    assert affected_label_ids == {label.id}
    assert deleted_sample_count == 2
    assert dataset_repo.get_source(source.id) is None
    assert dataset_repo.get_samples(source_id=source.id) == []
    db_session.refresh(label)
    assert label.sample_count == 0

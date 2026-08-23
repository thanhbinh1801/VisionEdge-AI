from pathlib import Path

from backend.app.core.config import DEFAULT_DB_PATH, PROJECT_ROOT, Settings


def sqlite_path(database_url: str) -> Path:
    assert database_url.startswith("sqlite:///")
    return Path(database_url.removeprefix("sqlite:///"))


def test_default_database_url_uses_project_root_canonical_path(monkeypatch):
    monkeypatch.chdir(PROJECT_ROOT / "backend")

    settings = Settings(_env_file=None)

    assert sqlite_path(settings.DATABASE_URL) == DEFAULT_DB_PATH


def test_sentriai_db_path_is_translated_relative_to_project_root():
    settings = Settings(_env_file=None, SENTRIAI_DB_PATH="backend/db/custom.db")

    assert sqlite_path(settings.DATABASE_URL) == PROJECT_ROOT / "backend" / "db" / "custom.db"


def test_database_url_takes_precedence_over_sentriai_db_path(tmp_path):
    explicit_db = tmp_path / "explicit.db"

    settings = Settings(
        _env_file=None,
        DATABASE_URL=f"sqlite:///{explicit_db}",
        SENTRIAI_DB_PATH="backend/db/ignored.db",
    )

    assert sqlite_path(settings.DATABASE_URL) == explicit_db


def test_relative_database_url_is_canonicalized_from_project_root():
    settings = Settings(_env_file=None, DATABASE_URL="sqlite:///./sentri_ai.db")

    assert sqlite_path(settings.DATABASE_URL) == PROJECT_ROOT / "sentri_ai.db"

import pathlib

import pytest

from db import database


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Points db.database at a throwaway sqlite file so tests never touch nexus.db."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", pathlib.Path(db_path))
    database.init_db()
    return db_path

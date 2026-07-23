import sqlite3

from app.storage.database import Database, MIGRATIONS, SCHEMA_VERSION


def test_schema_version(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    version = db.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION
    db.close()


def test_existing_version_2_case_is_migrated_without_losing_items(tmp_path):
    path = tmp_path / "old.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(MIGRATIONS[1])
    connection.executescript(MIGRATIONS[2])
    connection.execute("PRAGMA user_version = 2")
    connection.execute(
        """INSERT INTO items
        (id,type,x,y,width,height,rotation,z,created_at,modified_at,status,tags_json,locked,payload_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("00000000-0000-0000-0000-000000000001", "note", 0, 0, 100, 100, 0, 0,
         "2026-01-01", "2026-01-01", "Nowe", "[]", 0, "{}"),
    )
    connection.commit()
    connection.close()
    db = Database(path)
    assert db.connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert db.connection.execute("SELECT count(*) FROM items").fetchone()[0] == 1
    assert db.connection.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='analysis_records'"
    ).fetchone()[0] == 1
    db.close()

from pathlib import Path

from app.models import BoardItemModel, ConnectionModel, ItemType
from app.services import CaseManager
from app.storage import CaseRepository


def test_case_roundtrip(tmp_path: Path):
    paths, db, metadata = CaseManager.create(tmp_path / "case", "Test", "Opis")
    repo = CaseRepository(db)
    first = BoardItemModel(ItemType.NOTE, 12.5, -9, payload={"text": "hello"})
    second = BoardItemModel(ItemType.PIN, 50, 60, payload={"name": "x"})
    edge = ConnectionModel(first.id, second.id, label="zna")
    repo.save_all([first, second], [edge])
    assert repo.load_metadata().name == "Test"
    assert [x.id for x in repo.load_items()] == [first.id, second.id]
    assert repo.load_connections()[0].target_id == second.id
    db.close()
    assert paths.manifest.exists()


def test_media_is_copied_with_relative_path(tmp_path: Path):
    paths, db, _ = CaseManager.create(tmp_path / "case", "Test")
    source = tmp_path / "photo.png"
    source.write_bytes(b"not really a png")
    relative = CaseManager.import_media(paths, source)
    assert not relative.is_absolute()
    assert (paths.root / relative).read_bytes() == source.read_bytes()
    db.close()


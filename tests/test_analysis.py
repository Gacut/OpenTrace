import json

from app.models import AnalysisRecord, BoardItemModel, ItemType
from app.services import sha256_file, structural_export, validate_project
from app.services.case_manager import CaseManager
from app.storage import CaseRepository


def test_analysis_record_roundtrip(tmp_path):
    _, db, _ = CaseManager.create(tmp_path / "case", "Analiza")
    repository = CaseRepository(db)
    record = AnalysisRecord(
        kind="hypothesis", title="Hipoteza A", status="Analizowana",
        data={"confidence": 35}, item_ids=["item-a"], tags=["ważne"],
    )
    repository.save_record(record)
    loaded = repository.load_records("hypothesis")[0]
    assert loaded.title == "Hipoteza A"
    assert loaded.data["confidence"] == 35
    assert repository.search_records("ważne")[0].id == record.id
    db.close()


def test_integrity_validation_detects_changed_file(tmp_path):
    case_root = tmp_path / "case"
    case_root.mkdir()
    media = case_root / "media"
    media.mkdir()
    image = media / "evidence.png"
    image.write_bytes(b"original")
    item = BoardItemModel(
        ItemType.IMAGE, 0, 0,
        payload={"path": "media/evidence.png", "sha256": sha256_file(image)},
    )
    image.write_bytes(b"changed")
    issues = validate_project(case_root, [item], [])
    assert any("różni się" in issue["message"] for issue in issues)


def test_structural_export_contains_no_absolute_project_path(tmp_path):
    destination = tmp_path / "export.json"
    item = BoardItemModel(ItemType.IMAGE, 0, 0, payload={"path": "media/a.png"})
    structural_export(destination, {"name": "Test", "local_path": "C:/secret"}, [item], [], [])
    data = json.loads(destination.read_text(encoding="utf-8"))
    assert "local_path" not in data["case"]
    assert data["items"][0]["payload"]["path"] == "media/a.png"

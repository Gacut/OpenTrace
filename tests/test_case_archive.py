import zipfile

import pytest

from app.services import CaseManager


def test_case_zip_round_trip(tmp_path):
    source = tmp_path / "Źródłowa sprawa"
    paths, database, metadata = CaseManager.create(source, "Test archiwum")
    (paths.media / "dowod.txt").write_text("materiał", encoding="utf-8")
    database.close()

    archive = tmp_path / "Kopia sprawy.zip"
    assert CaseManager.pack(paths, archive) == archive

    target = tmp_path / "Rozpakowana sprawa"
    assert CaseManager.unpack(archive, target) == target
    opened_paths, opened_database, opened_metadata = CaseManager.open(target)
    assert opened_metadata.name == metadata.name
    assert (opened_paths.media / "dowod.txt").read_text(encoding="utf-8") == "materiał"
    opened_database.close()


def test_case_zip_rejects_path_traversal(tmp_path):
    archive = tmp_path / "niebezpieczna.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../poza-folderem.txt", "nie")
        output.writestr("case.sqlite3", "nieistotne")

    target = tmp_path / "sprawa"
    with pytest.raises(ValueError, match="niedozwoloną ścieżkę"):
        CaseManager.unpack(archive, target)
    assert not target.exists()
    assert not (tmp_path / "poza-folderem.txt").exists()


def test_case_zip_cannot_be_created_inside_case(tmp_path):
    paths, database, _ = CaseManager.create(tmp_path / "sprawa", "Test")
    database.close()
    with pytest.raises(ValueError, match="wewnątrz folderu sprawy"):
        CaseManager.pack(paths, paths.root / "sprawa.zip")

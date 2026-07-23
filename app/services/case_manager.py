from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.models import CaseMetadata
from app.storage import CaseRepository, Database


@dataclass(frozen=True)
class CasePaths:
    root: Path

    @property
    def database(self) -> Path:
        return self.root / "case.sqlite3"

    @property
    def manifest(self) -> Path:
        return self.root / "project.json"

    @property
    def media(self) -> Path:
        return self.root / "media"

    @property
    def thumbnails(self) -> Path:
        return self.root / "thumbnails"

    @property
    def attachments(self) -> Path:
        return self.root / "attachments"

    @property
    def backups(self) -> Path:
        return self.root / "backups"


class CaseManager:
    @staticmethod
    def create(root: Path, name: str, description: str = "") -> tuple[CasePaths, Database, CaseMetadata]:
        paths = CasePaths(Path(root))
        if paths.root.exists() and any(paths.root.iterdir()):
            raise FileExistsError("Wybrany katalog nie jest pusty.")
        for path in (paths.root, paths.media, paths.thumbnails, paths.attachments, paths.backups):
            path.mkdir(parents=True, exist_ok=True)
        metadata = CaseMetadata(name=name, description=description)
        db = Database(paths.database)
        CaseRepository(db).save_metadata(metadata)
        CaseManager.write_manifest(paths, metadata)
        return paths, db, metadata

    @staticmethod
    def open(root: Path) -> tuple[CasePaths, Database, CaseMetadata]:
        paths = CasePaths(Path(root))
        if not paths.database.exists():
            raise FileNotFoundError("W katalogu nie ma pliku case.sqlite3.")
        db = Database(paths.database)
        return paths, db, CaseRepository(db).load_metadata()

    @staticmethod
    def write_manifest(paths: CasePaths, metadata: CaseMetadata) -> None:
        paths.manifest.write_text(json.dumps({
            "schema_version": 4, "case_id": metadata.id, "name": metadata.name,
            "database": "case.sqlite3", "media": "media",
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def import_media(paths: CasePaths, source: Path) -> Path:
        suffix = source.suffix.lower()
        target = paths.media / f"{uuid4().hex}{suffix}"
        shutil.copy2(source, target)
        return target.relative_to(paths.root)

    @staticmethod
    def backup(paths: CasePaths, *, keep: int = 10) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = paths.backups / f"case-{stamp}.sqlite3"
        shutil.copy2(paths.database, target)
        backups = sorted(paths.backups.glob("case-*.sqlite3"), reverse=True)
        for old in backups[keep:]:
            old.unlink()
        return target

    @staticmethod
    def pack(paths: CasePaths, target: Path) -> Path:
        target = Path(target)
        root = paths.root.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve().is_relative_to(root):
            raise ValueError("Archiwum nie może być zapisane wewnątrz folderu sprawy.")
        temporary = target.with_name(f".{target.name}.tmp")
        try:
            with zipfile.ZipFile(
                temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
            ) as archive:
                for source in sorted(paths.root.rglob("*")):
                    if source.is_file():
                        archive.write(source, source.relative_to(paths.root).as_posix())
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    @staticmethod
    def unpack(archive_path: Path, target_root: Path) -> Path:
        archive_path, target_root = Path(archive_path), Path(target_root)
        if target_root.exists():
            raise FileExistsError("Folder docelowy już istnieje. Wybierz inną nazwę.")
        target_root.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".opentrace-import-", dir=target_root.parent))
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                base = temporary.resolve()
                for member in archive.infolist():
                    destination = (temporary / member.filename).resolve()
                    if not destination.is_relative_to(base):
                        raise ValueError("Archiwum zawiera niedozwoloną ścieżkę pliku.")
                    unix_mode = member.external_attr >> 16
                    if (unix_mode & 0o170000) == 0o120000:
                        raise ValueError("Archiwum zawiera niedozwolone dowiązanie symboliczne.")
                archive.extractall(temporary)
            if not (temporary / "case.sqlite3").is_file():
                raise ValueError("Archiwum nie zawiera prawidłowej sprawy OpenTrace.")
            temporary.replace(target_root)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return target_root

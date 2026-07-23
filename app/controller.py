from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QTimer, Signal
from PySide6.QtGui import QImageReader, QUndoStack

from app.commands import (
    AddConnectionCommand, AddItemCommand, DeleteSelectionCommand, MoveItemCommand,
    ResizeItemCommand,
)
from app.graphics import BoardScene
from app.graphics.items import BaseNodeItem, ConnectionItem
from app.models import AnalysisRecord, BoardItemModel, CaseMetadata, ConnectionModel, ItemType
from app.models.entities import now_iso
from app.services import CaseManager, CasePaths, sha256_file
from app.storage import CaseRepository, Database


class CaseController(QObject):
    saved = Signal()
    dirty_changed = Signal(bool)
    error = Signal(str)

    def __init__(self, paths: CasePaths, database: Database, metadata: CaseMetadata):
        super().__init__()
        self.paths, self.database, self.metadata = paths, database, metadata
        self.repository = CaseRepository(database)
        self.scene = BoardScene(paths.root)
        self.undo_stack = QUndoStack(self)
        self.dirty = False
        self._closed = False
        self.autosave = QTimer(self)
        self.autosave.setSingleShot(True)
        self.autosave.setInterval(1200)
        self.autosave.timeout.connect(self.save)
        self.scene.changed_by_user.connect(self.mark_dirty)
        self.scene.move_finished.connect(self._record_move)
        self.scene.resize_finished.connect(self._record_resize)
        self.load()

    def load(self):
        self.scene.loading = True
        for model in self.repository.load_items():
            self.scene.add_model(model)
        pending = self.repository.load_connections()
        while pending:
            remaining = []
            added = 0
            for connection in pending:
                if self.scene.add_connection(connection):
                    added += 1
                else:
                    remaining.append(connection)
            if not added:
                break
            pending = remaining
        self.scene.loading = False

    def mark_dirty(self):
        if not self.dirty:
            self.dirty = True
            self.dirty_changed.emit(True)
        self.autosave.start()

    def save(self):
        if self._closed:
            return
        try:
            items, connections = self.scene.models()
            for item in items:
                item.modified_at = now_iso()
            self.repository.save_all(items, connections)
            self.repository.save_metadata(self.metadata)
            CaseManager.write_manifest(self.paths, self.metadata)
            self.dirty = False
            self.dirty_changed.emit(False)
            self.saved.emit()
        except Exception as exc:
            self.error.emit(f"Nie udało się zapisać sprawy: {exc}")

    def close(self):
        if self._closed:
            return
        self.autosave.stop()
        if self.dirty:
            self.save()
        self._closed = True
        self.database.close()

    def add_note(self, pos: QPointF, title="Nowa notatka", text=""):
        model = BoardItemModel(ItemType.NOTE, pos.x(), pos.y(),
                               payload={"title": title, "text": text, "color": "#facc15"})
        self.undo_stack.push(AddItemCommand(self, model))
        self.log_event("Utworzono notatkę", "element", item_ids=[model.id])

    def add_pin(self, pos: QPointF, name="Nowa pinezka"):
        model = BoardItemModel(ItemType.PIN, pos.x(), pos.y(), 140, 110,
                               payload={"name": name, "color": "#ef4444", "icon": "●"})
        self.undo_stack.push(AddItemCommand(self, model))
        self.log_event("Utworzono pinezkę", "element", item_ids=[model.id])

    def add_image(self, pos: QPointF, source: Path, reuse: BoardItemModel | None = None):
        relative = Path(reuse.payload["path"]) if reuse else CaseManager.import_media(self.paths, source)
        imported_path = self.paths.root / relative
        reader = QImageReader(str(self.paths.root / relative))
        size = reader.size()
        width = min(max(size.width(), 180), 420) if size.isValid() else 320
        height = min(max(size.height(), 140), 320) if size.isValid() else 240
        model = BoardItemModel(ItemType.IMAGE, pos.x(), pos.y(), width, height,
                               payload={"path": relative.as_posix(),
                                        "filename": reuse.payload.get("filename", source.name) if reuse else source.name,
                                        "caption": "", "sha256": sha256_file(imported_path),
                                        "size_bytes": imported_path.stat().st_size,
                                        "added_at": now_iso()})
        self.undo_stack.push(AddItemCommand(self, model))
        self.log_event(f"Zaimportowano plik: {source.name}", "import", item_ids=[model.id])

    def connect_selected(self, template: ConnectionModel | None = None):
        nodes = [item for item in self.scene.selectedItems() if isinstance(item, BaseNodeItem)]
        edges = [item for item in self.scene.selectedItems() if isinstance(item, ConnectionItem)]
        if len(nodes) == 2 and not edges:
            model = ConnectionModel(nodes[0].model.id, nodes[1].model.id)
        elif len(nodes) == 1 and len(edges) == 1:
            parent = edges[0].model
            target_id = nodes[0].model.id
            if target_id in {parent.source_id, parent.target_id}:
                raise ValueError("Wybierz element, który nie jest już końcem tej linii.")
            model = ConnectionModel(
                parent.source_id, target_id, branch_from_id=parent.id,
            )
        else:
            raise ValueError(
                "Zaznacz dwa elementy albo jedną linię i jeden dodatkowy element."
            )
        if template:
            model.color, model.width, model.style = template.color, template.width, template.style
            model.label, model.direction = template.label, template.direction
            model.relation_type, model.confidence = template.relation_type, template.confidence
        self.undo_stack.push(AddConnectionCommand(self, model))
        self.log_event("Utworzono połączenie", "relacja",
                       item_ids=[model.source_id, model.target_id], connection_id=model.id)

    def delete_selected(self):
        items = self.scene.selectedItems()
        node_ids = [i.model.id for i in items if isinstance(i, BaseNodeItem)]
        edge_ids = [i.model.id for i in items if isinstance(i, ConnectionItem)]
        if node_ids or edge_ids:
            command = DeleteSelectionCommand(self, node_ids, edge_ids)
            self.undo_stack.push(command)

    @staticmethod
    def _deleted_item_name(model) -> str:
        return (
            model.payload.get("title") or model.payload.get("filename")
            or model.payload.get("name") or "Bez nazwy"
        )

    def log_deleted_models(self, items, edges) -> None:
        type_names = {
            ItemType.NOTE: "notatkę", ItemType.IMAGE: "zdjęcie",
            ItemType.PIN: "pinezkę", ItemType.TEXT: "tekst", ItemType.GROUP: "grupę",
        }
        for model in items:
            name = self._deleted_item_name(model)
            self.log_event(
                f"Usunięto {type_names.get(model.type, 'element')}: {name}", "usunięcie",
                body=f"Typ: {model.type.value}\nNazwa: {name}\nUUID: {model.id}",
            )
        for model in edges:
            name = model.label or model.relation_type or "Bez etykiety"
            self.log_event(
                f"Usunięto połączenie: {name}", "usunięcie",
                body=(f"Typ: relacja\nNazwa: {name}\nUUID: {model.id}\n"
                      f"Element źródłowy: {model.source_id}\nElement docelowy: {model.target_id}"),
            )

    def log_restored_models(self, items, edges) -> None:
        for model in items:
            name = self._deleted_item_name(model)
            self.log_event(
                f"Przywrócono usunięty element (CTRL + Z): {name}", "przywrócenie",
                body=f"Typ: {model.type.value}\nNazwa: {name}\nUUID: {model.id}",
                item_ids=[model.id],
            )
        for model in edges:
            name = model.label or model.relation_type or "Bez etykiety"
            self.log_event(
                f"Przywrócono usunięte połączenie (CTRL + Z): {name}", "przywrócenie",
                body=f"Typ: relacja\nNazwa: {name}\nUUID: {model.id}",
                item_ids=[model.source_id, model.target_id], connection_id=model.id,
            )

    def _record_move(self, item_id: str, old: QPointF, new: QPointF):
        if old != new:
            self.undo_stack.push(MoveItemCommand(self, item_id, old, new))

    def _record_resize(self, item_id: str, old_geometry: tuple, new_geometry: tuple):
        if old_geometry != new_geometry:
            self.undo_stack.push(ResizeItemCommand(self, item_id, old_geometry, new_geometry))

    def rename_image(self, item_id: str, requested_name: str) -> str:
        item = self.scene.nodes.get(item_id)
        if not item or item.model.type != ItemType.IMAGE:
            raise ValueError("Nie znaleziono obrazu.")
        old_relative = Path(item.model.payload["path"])
        old_path = self.paths.root / old_relative
        requested = Path(requested_name.strip()).name
        if not requested or requested in {".", ".."}:
            raise ValueError("Nazwa pliku nie może być pusta.")
        if not Path(requested).suffix:
            requested += old_path.suffix
        elif Path(requested).suffix.lower() != old_path.suffix.lower():
            raise ValueError(f"Rozszerzenie obrazu musi pozostać {old_path.suffix}.")
        target = old_path.with_name(requested)
        if target != old_path and target.exists():
            raise FileExistsError("Plik o tej nazwie już istnieje w sprawie.")
        if target != old_path:
            old_path.rename(target)
        relative = target.relative_to(self.paths.root).as_posix()
        item.model.payload["path"] = relative
        item.model.payload["filename"] = target.name
        if hasattr(item, "reload_pixmap"):
            item.reload_pixmap()
        item.update()
        self.mark_dirty()
        return target.name

    def log_event(self, title: str, category: str, *, body: str = "",
                  item_ids: list[str] | None = None,
                  connection_id: str | None = None) -> None:
        data = {"body": body, "category": category}
        if connection_id:
            data["connection_id"] = connection_id
        self.repository.save_record(AnalysisRecord(
            kind="journal", title=title, status=category,
            data=data, item_ids=item_ids or [],
        ))

    def save_record(self, record: AnalysisRecord) -> None:
        previous = next(
            (value for value in self.repository.load_records(record.kind) if value.id == record.id),
            None,
        )
        self.repository.save_record(record)
        uuid_changed = previous is not None and previous.item_ids != record.item_ids
        if uuid_changed:
            old_ids = ", ".join(previous.item_ids) or "brak"
            new_ids = ", ".join(record.item_ids) or "brak"
            self.log_event(
                f"Zmieniono UUID: {record.title}",
                "modyfikacja",
                body=f"Poprzednie UUID: {old_ids}\nNowe UUID: {new_ids}",
                item_ids=record.item_ids,
            )
        elif record.kind != "journal":
            self.log_event(f"Zmieniono: {record.title}", record.kind, item_ids=record.item_ids)

    def duplicate_image(self, sha256: str) -> BoardItemModel | None:
        for item in self.scene.nodes.values():
            if item.model.type == ItemType.IMAGE and item.model.payload.get("sha256") == sha256:
                return item.model
        return None

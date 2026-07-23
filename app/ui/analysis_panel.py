from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget, QMessageBox,
)

from app.models import AnalysisRecord
from app.i18n import combo_source_text, journal_title, tr

RECORD_TYPES = {
    "task": ("Zadania", ["Do zrobienia", "W trakcie", "Zablokowane", "Do ponownej weryfikacji", "Ukończone", "Odrzucone"]),
    "verification": ("Do weryfikacji", ["Nowe", "W trakcie", "Potwierdzone", "Niepotwierdzone", "Odrzucone", "Brak wystarczających danych"]),
    "source": ("Źródła", ["Dostępne", "Niedostępne", "Usunięte", "Zmienione", "Zarchiwizowane lokalnie", "Nieznane"]),
    "hypothesis": ("Hipotezy", ["Nowa", "Analizowana", "Prawdopodobna", "Mało prawdopodobna", "Potwierdzona", "Odrzucona", "Wymaga dodatkowych danych"]),
    "journal": ("Dziennik", ["notatka", "element", "relacja", "modyfikacja", "usunięcie", "przywrócenie", "import", "eksport", "decyzja"]),
}


class ItemSelectionDialog(QDialog):
    def __init__(self, controller, selected_ids: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wybierz elementy z tablicy")
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        selected = set(selected_ids)
        type_names = {"note": "notatka", "image": "zdjęcie", "pin": "pinezka"}
        if controller:
            for node in controller.scene.nodes.values():
                model = node.model
                name = (
                    model.payload.get("title") or model.payload.get("filename")
                    or model.payload.get("name") or "Bez nazwy"
                )
                item = QListWidgetItem(
                    f"{name}  [{type_names.get(model.type.value, model.type.value)}]\n{model.id}"
                )
                item.setData(Qt.ItemDataRole.UserRole, model.id)
                self.list.addItem(item)
                item.setSelected(model.id in selected)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Zaznacz jeden lub kilka elementów:"))
        layout.addWidget(self.list)
        layout.addWidget(buttons)
        self.resize(620, 430)

    def selected_ids(self) -> list[str]:
        return [
            item.data(Qt.ItemDataRole.UserRole) for item in self.list.selectedItems()
        ]


class RecordDialog(QDialog):
    def __init__(self, kind: str, selected_item_ids: list[str], record: AnalysisRecord | None = None,
                 parent=None, controller=None):
        super().__init__(parent)
        self.kind, self.record, self.controller = kind, record, controller
        self.setWindowTitle(f"{'Edytuj' if record else 'Dodaj'}: {RECORD_TYPES[kind][0]}")
        self.title_edit = QLineEdit(record.title if record else "")
        self.status_combo = QComboBox()
        self.status_combo.addItems(RECORD_TYPES[kind][1])
        if record and record.status:
            self.status_combo.setCurrentText(record.status)
        self.tags_edit = QLineEdit(", ".join(record.tags) if record else "")
        self.details_edit = QTextEdit((record.data.get("body") or record.data.get("description", "")) if record else "")
        self.items_edit = QLineEdit(", ".join(record.item_ids if record else selected_item_ids))
        self.items_edit.setReadOnly(True)
        self.unlock_items_button = QPushButton("Odblokuj edycję")
        self.unlock_items_button.setCheckable(True)
        self.unlock_items_button.toggled.connect(self._toggle_items_editing)
        self.select_items_button = QPushButton("Wybierz z tablicy…")
        self.select_items_button.clicked.connect(self.choose_board_items)
        items_row = QWidget()
        items_layout = QHBoxLayout(items_row)
        items_layout.setContentsMargins(0, 0, 0, 0)
        items_layout.setSpacing(6)
        items_layout.addWidget(self.items_edit, 1)
        items_layout.addWidget(self.unlock_items_button)
        items_layout.addWidget(self.select_items_button)
        self.extra_label = QLabel("")
        self.extra_edit = QLineEdit()
        form = QFormLayout()
        form.addRow("Nazwa / tytuł:", self.title_edit)
        form.addRow("Status / kategoria:", self.status_combo)
        form.addRow("Tagi:", self.tags_edit)
        form.addRow("Powiązane UUID:", items_row)
        form.addRow("Opis / notatka:", self.details_edit)
        if kind == "hypothesis":
            self.extra_label.setText("Pewność 0–100:")
            self.extra_edit.setText(str(record.data.get("confidence", 0)) if record else "0")
            form.addRow(self.extra_label, self.extra_edit)
        elif kind == "task":
            self.extra_label.setText("Priorytet:")
            self.extra_edit.setText(record.data.get("priority", "Normalny") if record else "Normalny")
            form.addRow(self.extra_label, self.extra_edit)
        elif kind == "source":
            self.extra_label.setText("URL / ścieżka:")
            self.extra_edit.setText(record.data.get("location", "") if record else "")
            form.addRow(self.extra_label, self.extra_edit)
        elif kind == "verification":
            self.extra_label.setText("Priorytet / powód:")
            self.extra_edit.setText(record.data.get("reason", "") if record else "")
            form.addRow(self.extra_label, self.extra_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(820, 430)

    def _toggle_items_editing(self, unlocked: bool):
        self.items_edit.setReadOnly(not unlocked)
        self.unlock_items_button.setText(
            "Zablokuj edycję" if unlocked else "Odblokuj edycję"
        )
        if unlocked:
            self.items_edit.setFocus()

    def choose_board_items(self):
        current_ids = [
            value.strip() for value in self.items_edit.text().split(",") if value.strip()
        ]
        dialog = ItemSelectionDialog(self.controller, current_ids, self)
        if dialog.exec():
            self.items_edit.setText(", ".join(dialog.selected_ids()))

    def build_record(self) -> AnalysisRecord:
        data = dict(self.record.data) if self.record else {}
        data["body"] = self.details_edit.toPlainText()
        linked_item_ids = [
            value.strip() for value in self.items_edit.text().split(",") if value.strip()
        ]
        if self.record and linked_item_ids != self.record.item_ids:
            # Relation journal entries carry a direct edge target. Once the
            # user changes UUIDs explicitly, that old hidden target must no
            # longer override the newly selected object.
            data.pop("connection_id", None)
        key = {"hypothesis": "confidence", "task": "priority", "source": "location",
               "verification": "reason"}.get(self.kind)
        if key:
            value = self.extra_edit.text().strip()
            if key == "confidence":
                value = max(0, min(100, int(value or 0)))
            data[key] = value
        values = dict(
            kind=self.kind, title=self.title_edit.text().strip(),
            status=combo_source_text(self.status_combo),
            tags=[tag.strip() for tag in self.tags_edit.text().split(",") if tag.strip()],
            item_ids=linked_item_ids,
            data=data,
        )
        if self.record:
            for key_name in ("id", "created_at", "modified_at"):
                values[key_name] = getattr(self.record, key_name)
        return AnalysisRecord(**values)

    def accept(self):
        if not self.title_edit.text().strip():
            return
        if self.kind == "hypothesis":
            try:
                value = int(self.extra_edit.text() or 0)
            except ValueError:
                self.extra_edit.setFocus()
                return
            if not 0 <= value <= 100:
                self.extra_edit.setFocus()
                return
        super().accept()


class RecordTab(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, kind: str, controller_getter, parent=None):
        super().__init__(parent)
        self.kind, self.controller_getter = kind, controller_getter
        self.list = QListWidget()
        if kind in {"task", "journal", "verification"}:
            self.list.itemDoubleClicked.connect(self.navigate_from_double_click)
        else:
            self.list.itemDoubleClicked.connect(self.edit_selected)
        add = QPushButton("Dodaj")
        edit = QPushButton("Edytuj")
        delete = QPushButton("Usuń")
        go = QPushButton("Pokaż element")
        add.clicked.connect(self.add_record)
        edit.clicked.connect(self.edit_selected)
        delete.clicked.connect(self.delete_selected)
        go.clicked.connect(self.navigate)
        buttons = QHBoxLayout()
        for button in (add, edit, delete, go):
            buttons.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addLayout(buttons)

    def refresh(self):
        self._clear_list_safely()
        controller = self.controller_getter()
        if not controller:
            return
        for record in controller.repository.load_records(self.kind):
            suffix = ""
            if self.kind == "hypothesis":
                suffix = f" • pewność {record.data.get('confidence', 0)}%"
            visible_title = journal_title(record.title) if self.kind == "journal" else record.title
            item = QListWidgetItem(f"{visible_title}  [{tr(record.status)}]{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, record.id)
            self.list.addItem(item)
            if self.kind == "journal":
                display_text = item.text()
                timestamp = self._format_timestamp(record.created_at)
                item.setData(Qt.ItemDataRole.UserRole + 1, timestamp)
                item.setData(Qt.ItemDataRole.UserRole + 2, display_text)
                item.setData(Qt.ItemDataRole.AccessibleTextRole, display_text)
                # The custom two-line widget paints the entry. Leaving the
                # QListWidgetItem text set would make Qt paint it a second time.
                item.setText("")
                container = QWidget()
                container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                container.setStyleSheet("background: transparent;")
                title = QLabel(display_text)
                title.setStyleSheet("background: transparent;")
                date = QLabel(timestamp)
                date.setStyleSheet(
                    "background: transparent; color: #94a3b8; font-size: 8pt;"
                )
                item_layout = QVBoxLayout(container)
                item_layout.setContentsMargins(6, 4, 6, 4)
                item_layout.setSpacing(1)
                item_layout.addWidget(title)
                item_layout.addWidget(date)
                item.setSizeHint(container.sizeHint())
                self.list.setItemWidget(item, container)

    def _clear_list_safely(self):
        """Detach custom widgets before releasing their QListWidgetItems.

        PySide can otherwise invalidate the Python item wrapper twice while a
        case is closed and another one is loaded into the same panel.
        """
        while self.list.count():
            item = self.list.item(0)
            widget = self.list.itemWidget(item)
            if widget:
                self.list.removeItemWidget(item)
                widget.deleteLater()
            taken_item = self.list.takeItem(0)
            del taken_item

    @staticmethod
    def _format_timestamp(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo:
                parsed = parsed.astimezone()
            return parsed.strftime("%d.%m.%Y, %H:%M:%S")
        except (TypeError, ValueError):
            return value

    def selected_record(self) -> AnalysisRecord | None:
        item = self.list.currentItem()
        controller = self.controller_getter()
        if not item or not controller:
            return None
        record_id = item.data(Qt.ItemDataRole.UserRole)
        return next((r for r in controller.repository.load_records(self.kind) if r.id == record_id), None)

    def selected_board_ids(self) -> list[str]:
        controller = self.controller_getter()
        if not controller:
            return []
        return [item.model.id for item in controller.scene.selectedItems() if hasattr(item, "model")]

    def add_record(self):
        controller = self.controller_getter()
        if not controller:
            return
        dialog = RecordDialog(
            self.kind, self.selected_board_ids(), parent=self, controller=controller
        )
        if dialog.exec():
            controller.save_record(dialog.build_record())
            self.refresh()

    def edit_selected(self, *_):
        controller, record = self.controller_getter(), self.selected_record()
        if not controller or not record:
            return
        dialog = RecordDialog(
            self.kind, self.selected_board_ids(), record, self, controller=controller
        )
        if dialog.exec():
            controller.save_record(dialog.build_record())
            self.refresh()

    def delete_selected(self):
        controller, record = self.controller_getter(), self.selected_record()
        if controller and record:
            controller.repository.delete_record(record.id)
            self.refresh()

    def navigate(self):
        record = self.selected_record()
        target_id = self.navigation_target(record)
        if target_id:
            self.navigate_requested.emit(target_id)

    def navigate_from_double_click(self, *_):
        record = self.selected_record()
        target_id = self.navigation_target(record)
        if target_id:
            self.navigate_requested.emit(target_id)
        elif record and self.kind == "verification":
            QMessageBox.information(
                self, "Do weryfikacji", "Nie przypisano do żadnego elementu"
            )

    def navigation_target(self, record: AnalysisRecord | None) -> str | None:
        if not record:
            return None
        if self.kind == "journal" and (
            record.status == "relacja" or record.data.get("category") == "relacja"
        ):
            connection_id = record.data.get("connection_id")
            if connection_id:
                return connection_id
            controller = self.controller_getter()
            if controller and len(record.item_ids) >= 2:
                endpoints = {record.item_ids[0], record.item_ids[1]}
                for edge in controller.scene.edges.values():
                    if {edge.model.source_id, edge.model.target_id} == endpoints:
                        return edge.model.id
        return record.item_ids[0] if record.item_ids else None


class AnalysisPanel(QTabWidget):
    navigate_requested = Signal(str)

    def __init__(self, controller_getter, parent=None):
        super().__init__(parent)
        self.tabs: dict[str, RecordTab] = {}
        for kind, (label, _) in RECORD_TYPES.items():
            tab = RecordTab(kind, controller_getter)
            tab.navigate_requested.connect(self.navigate_requested)
            self.tabs[kind] = tab
            self.addTab(tab, label)
        self.currentChanged.connect(lambda _: self.refresh())

    def refresh(self):
        for tab in self.tabs.values():
            tab.refresh()

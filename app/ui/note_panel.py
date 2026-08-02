from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTabWidget,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from app.ui.dialogs import CLASSIFICATIONS, ITEM_STATUSES
from app.i18n import combo_source_text, set_combo_source, tr

URL_RE = re.compile(r"https?://[^\s<>\"]+")


class NotePanel(QWidget):
    note_saved = Signal(str)

    def __init__(self, controller_getter, parent=None):
        super().__init__(parent)
        self.controller_getter = controller_getter
        self.item_id: str | None = None
        self.original_title = ""
        self.original_text = ""
        self.pending_attachment_sources: list[Path] = []

        self.heading = QLabel("Nie wybrano notatki")
        self.heading.setWordWrap(True)
        self.heading.setStyleSheet("font-size: 13pt; font-weight: 700; padding: 4px;")
        self.title_edit = QLineEdit()
        self.title_edit.hide()

        self.text = QTextBrowser()
        self.text.setReadOnly(True)
        self.text.setAcceptRichText(False)
        self.text.setOpenExternalLinks(True)
        self.text.setPlaceholderText("Wybierz notatkę na tablicy.")
        self.text.setToolTip(
            "Tekst można zaznaczyć i skopiować skrótem Ctrl+C. "
            "Kliknięcie linku otwiera domyślną przeglądarkę."
        )

        self.edit_button = QPushButton("Edycja")
        self.save_button = QPushButton("Zapisz")
        self.cancel_button = QPushButton("Anuluj")
        self.save_button.hide()
        self.cancel_button.hide()
        self.edit_button.setEnabled(False)

        self.edit_button.clicked.connect(self.begin_edit)
        self.save_button.clicked.connect(self.save)
        self.cancel_button.clicked.connect(self.cancel)

        buttons = QHBoxLayout()
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        hint = QLabel(
            "Możesz zaznaczać i kopiować tekst. Kliknięcie podświetlonego linku "
            "otwiera domyślną przeglądarkę systemową."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #94a3b8; font-size: 9pt;")

        self.attachments_label = QLabel("Załączniki:")
        self.attachments = QListWidget()
        self.attachments.setMaximumHeight(110)
        self.attachments.itemClicked.connect(self.open_attachment)
        self.add_attachment_button = QPushButton("Dodaj pliki…")
        self.add_attachment_button.clicked.connect(self.choose_attachments)
        self.add_attachment_button.hide()

        note_page = QWidget()
        note_layout = QVBoxLayout(note_page)
        note_layout.addWidget(self.heading)
        note_layout.addWidget(self.title_edit)
        note_layout.addWidget(self.text, 1)
        note_layout.addWidget(self.attachments_label)
        note_layout.addWidget(self.attachments)
        note_layout.addWidget(self.add_attachment_button)
        note_layout.addWidget(hint)
        note_layout.addLayout(buttons)

        self.property_summary = QTextEdit()
        self.property_summary.setReadOnly(True)
        self.property_summary.setTextInteractionFlags(
            self.property_summary.textInteractionFlags()
        )
        self.property_edit_button = QPushButton("Edycja")
        self.property_save_button = QPushButton("Zapisz")
        self.property_cancel_button = QPushButton("Anuluj")
        self.property_save_button.hide()
        self.property_cancel_button.hide()
        self.property_edit_button.setEnabled(False)
        self.property_edit_button.clicked.connect(self.begin_property_edit)
        self.property_save_button.clicked.connect(self.save_properties)
        self.property_cancel_button.clicked.connect(self.cancel_property_edit)

        self.property_form = QWidget()
        property_form_layout = QFormLayout(self.property_form)
        self.property_status = QComboBox()
        self.property_status.addItems(ITEM_STATUSES)
        self.property_tags = QLineEdit()
        self.property_classification = QComboBox()
        self.property_classification.addItems(CLASSIFICATIONS)
        self.property_source = QLineEdit()
        self.property_source_url = QLineEdit()
        self.property_aliases = QTextEdit()
        self.property_aliases.setMaximumHeight(90)
        self.property_visibility = QComboBox()
        self.property_visibility.addItems(
            ["publiczne", "wewnętrzne", "poufne", "wyłączone z eksportu"]
        )
        self.property_layer = QLineEdit()
        property_form_layout.addRow("Status:", self.property_status)
        property_form_layout.addRow("Tagi:", self.property_tags)
        property_form_layout.addRow("Klasyfikacja:", self.property_classification)
        property_form_layout.addRow("Źródło:", self.property_source)
        property_form_layout.addRow("URL źródła:", self.property_source_url)
        property_form_layout.addRow("Aliasy:", self.property_aliases)
        property_form_layout.addRow("Widoczność:", self.property_visibility)
        property_form_layout.addRow("Warstwa:", self.property_layer)
        self.property_form.hide()

        property_buttons = QHBoxLayout()
        property_buttons.addWidget(self.property_edit_button)
        property_buttons.addWidget(self.property_save_button)
        property_buttons.addWidget(self.property_cancel_button)
        property_page = QWidget()
        property_layout = QVBoxLayout(property_page)
        self.property_uuid = QLineEdit()
        self.property_uuid.setReadOnly(True)
        self.property_uuid.setToolTip("UUID można zaznaczyć i skopiować.")
        uuid_layout = QFormLayout()
        uuid_layout.addRow("UUID:", self.property_uuid)
        property_layout.addLayout(uuid_layout)
        property_layout.addWidget(self.property_summary, 1)
        property_layout.addWidget(self.property_form)
        property_layout.addLayout(property_buttons)

        self.tabs = QTabWidget()
        self.note_tab_index = self.tabs.addTab(note_page, "Notatka")
        self.properties_tab_index = self.tabs.addTab(property_page, "Właściwości")
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def show_note(self, item_id: str, tab: str = "note"):
        controller = self.controller_getter()
        item = controller.scene.nodes.get(item_id) if controller else None
        if not item:
            return
        if self.item_id != item_id:
            self.cancel()
        self.item_id = item_id
        self.property_uuid.setText(item.model.id)
        self.original_title = item.model.payload.get("title", "Notatka")
        self.original_text = item.model.payload.get("text", "")
        self.heading.setText(self.original_title)
        self.title_edit.setText(self.original_title)
        self.text.setPlainText(self.original_text)
        self.pending_attachment_sources = []
        self.refresh_attachments()
        self.highlight_links()
        self.set_editing(False)
        self.cancel_property_edit()
        self.refresh_property_summary()
        self.tabs.setCurrentIndex(
            self.properties_tab_index if tab == "properties" else self.note_tab_index
        )
        self.edit_button.setEnabled(True)
        self.property_edit_button.setEnabled(True)

    def set_editing(self, editing: bool):
        self.text.setReadOnly(not editing)
        self.heading.setVisible(not editing)
        self.title_edit.setVisible(editing)
        self.edit_button.setVisible(not editing)
        self.save_button.setVisible(editing)
        self.cancel_button.setVisible(editing)
        self.add_attachment_button.setVisible(editing)
        if editing:
            self.text.setFocus()
        else:
            self.highlight_links()

    def begin_edit(self):
        controller = self.controller_getter()
        item = controller.scene.nodes.get(self.item_id) if controller and self.item_id else None
        if not item or item.model.locked:
            return
        self.original_title = item.model.payload.get("title", "Notatka")
        self.original_text = item.model.payload.get("text", "")
        self.title_edit.setText(self.original_title)
        self.text.setPlainText(self.original_text)
        self.pending_attachment_sources = []
        self.refresh_attachments()
        self.set_editing(True)

    def save(self):
        controller = self.controller_getter()
        item = controller.scene.nodes.get(self.item_id) if controller and self.item_id else None
        if not item:
            return
        title = self.title_edit.text().strip() or "Notatka"
        body = self.text.toPlainText()
        if self.pending_attachment_sources:
            try:
                controller.add_note_attachments(
                    item.model.id, self.pending_attachment_sources
                )
            except Exception as exc:
                QMessageBox.critical(self, tr("Dodawanie załączników"), str(exc))
                return
            self.pending_attachment_sources = []
        item.model.payload["title"] = title
        item.model.payload["text"] = body
        item.update()
        controller.mark_dirty()
        controller.log_event("Edytowano notatkę", "element", item_ids=[item.model.id])
        self.original_title, self.original_text = title, body
        self.heading.setText(title)
        self.refresh_attachments()
        self.set_editing(False)
        self.note_saved.emit(item.model.id)

    def cancel(self):
        if self.item_id:
            self.heading.setText(self.original_title)
            self.title_edit.setText(self.original_title)
            self.text.setPlainText(self.original_text)
        self.pending_attachment_sources = []
        self.refresh_attachments()
        self.set_editing(False)

    def choose_attachments(self):
        filenames, _ = QFileDialog.getOpenFileNames(
            self, tr("Wybierz załączniki"), "", tr("Wszystkie pliki (*)")
        )
        known = {source.resolve() for source in self.pending_attachment_sources}
        for filename in filenames:
            source = Path(filename)
            resolved = source.resolve()
            if resolved not in known:
                self.pending_attachment_sources.append(source)
                known.add(resolved)
        self.refresh_attachments()

    def refresh_attachments(self):
        self.attachments.clear()
        item = self.current_item()
        if item:
            for attachment in item.model.payload.get("attachments", []):
                entry = QListWidgetItem(attachment.get("filename", "Załącznik"))
                entry.setData(Qt.ItemDataRole.UserRole, attachment.get("path", ""))
                size = attachment.get("size_bytes")
                entry.setToolTip(
                    f"{attachment.get('path', '')}"
                    + (f"\n{size} B" if size is not None else "")
                )
                self.attachments.addItem(entry)
        for source in self.pending_attachment_sources:
            entry = QListWidgetItem(
                f"{source.name} ({tr('oczekuje na zapis')})"
            )
            entry.setToolTip(str(source))
            self.attachments.addItem(entry)

    def open_attachment(self, entry: QListWidgetItem):
        relative_value = entry.data(Qt.ItemDataRole.UserRole)
        controller = self.controller_getter()
        if not relative_value or not controller:
            return
        case_root = controller.paths.root.resolve()
        target = (case_root / Path(relative_value)).resolve()
        try:
            target.relative_to(case_root)
        except ValueError:
            QMessageBox.warning(
                self, tr("Otwórz załącznik"),
                tr("Ścieżka załącznika znajduje się poza katalogiem sprawy."),
            )
            return
        if not target.is_file():
            QMessageBox.warning(
                self, tr("Otwórz załącznik"),
                tr("Plik załącznika nie istnieje w katalogu sprawy."),
            )
            return
        self._reveal_attachment(target)

    @staticmethod
    def _reveal_attachment(path: Path):
        if sys.platform == "win32":
            QProcess.startDetached("explorer.exe", ["/select,", str(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def copy(self):
        self.text.copy()

    def current_item(self):
        controller = self.controller_getter()
        return controller.scene.nodes.get(self.item_id) if controller and self.item_id else None

    def refresh_property_summary(self):
        item = self.current_item()
        if not item:
            self.property_summary.setPlainText("Nie wybrano notatki.")
            return
        model, payload = item.model, item.model.payload
        aliases = ", ".join(payload.get("aliases", [])) or "—"
        tags = ", ".join(model.tags) or "—"
        self.property_summary.setPlainText(
            f"{tr('Status:')} {tr(model.status)}\n"
            f"{tr('Tagi:')} {tags}\n"
            f"{tr('Klasyfikacja:')} {tr(payload.get('classification', 'Nieokreślona'))}\n"
            f"{tr('Źródło:')} {payload.get('source', '') or '—'}\n"
            f"{tr('URL źródła:')} {payload.get('source_url', '') or '—'}\n"
            f"{tr('Aliasy:')} {aliases}\n"
            f"{tr('Widoczność:')} {tr(payload.get('visibility', 'wewnętrzne'))}\n"
            f"{tr('Warstwa:')} {tr(payload.get('layer', 'Notatki analityczne'))}"
        )

    def begin_property_edit(self):
        item = self.current_item()
        if not item or item.model.locked:
            return
        model, payload = item.model, item.model.payload
        set_combo_source(self.property_status, model.status)
        self.property_tags.setText(", ".join(model.tags))
        set_combo_source(
            self.property_classification, payload.get("classification", "Nieokreślona")
        )
        self.property_source.setText(payload.get("source", ""))
        self.property_source_url.setText(payload.get("source_url", ""))
        self.property_aliases.setPlainText("\n".join(payload.get("aliases", [])))
        set_combo_source(self.property_visibility, payload.get("visibility", "wewnętrzne"))
        self.property_layer.setText(payload.get("layer", "Notatki analityczne"))
        self.property_summary.hide()
        self.property_form.show()
        self.property_edit_button.hide()
        self.property_save_button.show()
        self.property_cancel_button.show()

    def save_properties(self):
        controller, item = self.controller_getter(), self.current_item()
        if not controller or not item:
            return
        model, payload = item.model, item.model.payload
        model.status = combo_source_text(self.property_status)
        model.tags = [
            tag.strip() for tag in self.property_tags.text().split(",") if tag.strip()
        ]
        payload["classification"] = combo_source_text(self.property_classification)
        payload["source"] = self.property_source.text().strip()
        payload["source_url"] = self.property_source_url.text().strip()
        payload["aliases"] = [
            line.strip() for line in self.property_aliases.toPlainText().splitlines()
            if line.strip()
        ]
        payload["visibility"] = combo_source_text(self.property_visibility)
        payload["layer"] = self.property_layer.text().strip() or "Notatki analityczne"
        item.update()
        controller.mark_dirty()
        controller.log_event(
            "Zmieniono właściwości notatki", "element", item_ids=[model.id]
        )
        self.cancel_property_edit()
        self.refresh_property_summary()

    def cancel_property_edit(self):
        self.property_form.hide()
        self.property_summary.show()
        self.property_edit_button.show()
        self.property_save_button.hide()
        self.property_cancel_button.hide()

    def highlight_links(self):
        if not self.text.isReadOnly():
            return
        document_text = self.text.toPlainText()
        cursor = QTextCursor(self.text.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())
        link_format = QTextCharFormat()
        link_format.setForeground(QColor("#60a5fa"))
        link_format.setFontUnderline(True)
        link_format.setFontWeight(600)
        for match in URL_RE.finditer(document_text):
            cursor.setPosition(match.start())
            cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
            link_format.setAnchor(True)
            link_format.setAnchorHref(match.group())
            cursor.mergeCharFormat(link_format)

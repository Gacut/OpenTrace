from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.i18n import tr
from app.services import OsintTool, ToolLibrary


class ToolDialog(QDialog):
    def __init__(self, library: ToolLibrary, tool: OsintTool | None = None, parent=None):
        super().__init__(parent)
        self.library, self.tool = library, tool
        self.setWindowTitle("Edytuj narzędzie" if tool else "Dodaj narzędzie OSINT")
        self.name = QLineEdit(tool.name if tool else "")
        self.url = QLineEdit(tool.url if tool else "")
        self.url.setPlaceholderText("https://…")
        self.description = QTextEdit(tool.description if tool else "")
        self.description.setMaximumHeight(130)
        self.category = QComboBox()
        for category in library.categories:
            self.category.addItem(tr(category.name), category.id)
        if tool:
            index = self.category.findData(tool.category_id)
            self.category.setCurrentIndex(max(0, index))
        form = QFormLayout()
        form.addRow("Nazwa:", self.name)
        form.addRow("Link:", self.url)
        form.addRow("Opis zastosowania:", self.description)
        form.addRow("Kategoria:", self.category)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(520, 330)

    def build_tool(self) -> OsintTool:
        values = dict(
            name=self.name.text().strip(),
            url=self.url.text().strip(),
            description=self.description.toPlainText().strip(),
            category_id=self.category.currentData(),
        )
        if self.tool:
            values["id"] = self.tool.id
        return OsintTool(**values)

    def accept(self):
        if not self.name.text().strip() or not self.url.text().strip():
            return
        super().accept()


class ToolsPanel(QWidget):
    def __init__(self, library: ToolLibrary, parent=None):
        super().__init__(parent)
        self.library = library
        self.category = QComboBox()
        self.category.currentIndexChanged.connect(self.refresh_tools)
        self.tools = QListWidget()
        self.tools.currentItemChanged.connect(self.show_description)
        self.tools.itemDoubleClicked.connect(lambda _: self.open_selected())
        self.description = QLabel("Wybierz narzędzie.")
        self.description.setWordWrap(True)
        self.description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.description.setStyleSheet(
            "background: #0f172a; border: 1px solid #334155; padding: 8px;"
        )

        add_category = QPushButton("+ Kategoria")
        rename_category = QPushButton("Zmień nazwę")
        delete_category = QPushButton("Usuń kategorię")
        add_category.clicked.connect(self.add_category)
        rename_category.clicked.connect(self.rename_category)
        delete_category.clicked.connect(self.delete_category)
        category_buttons = QHBoxLayout()
        category_buttons.addWidget(add_category)
        category_buttons.addWidget(rename_category)
        category_buttons.addWidget(delete_category)

        add_tool = QPushButton("Dodaj")
        edit_tool = QPushButton("Edytuj")
        delete_tool = QPushButton("Usuń")
        open_tool = QPushButton("Otwórz link")
        add_tool.clicked.connect(self.add_tool)
        edit_tool.clicked.connect(self.edit_tool)
        delete_tool.clicked.connect(self.delete_tool)
        open_tool.clicked.connect(self.open_selected)
        tool_buttons = QHBoxLayout()
        for button in (add_tool, edit_tool, delete_tool, open_tool):
            tool_buttons.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Kategoria narzędzi:"))
        layout.addWidget(self.category)
        layout.addLayout(category_buttons)
        layout.addWidget(QLabel("Narzędzia:"))
        layout.addWidget(self.tools, 1)
        layout.addWidget(QLabel("Opis:"))
        layout.addWidget(self.description)
        layout.addLayout(tool_buttons)
        self.refresh()

    def refresh(self, selected_category_id: str | None = None):
        selected_category_id = selected_category_id or self.category.currentData()
        self.category.blockSignals(True)
        self.category.clear()
        for category in self.library.categories:
            self.category.addItem(tr(category.name), category.id)
        index = self.category.findData(selected_category_id)
        self.category.setCurrentIndex(max(0, index))
        self.category.blockSignals(False)
        self.refresh_tools()

    def refresh_tools(self):
        self.tools.clear()
        category_id = self.category.currentData()
        for tool in sorted(
            (value for value in self.library.tools if value.category_id == category_id),
            key=lambda value: value.name.casefold(),
        ):
            item = QListWidgetItem(tool.name)
            item.setToolTip(tool.url)
            item.setData(Qt.ItemDataRole.UserRole, tool.id)
            self.tools.addItem(item)
        self.show_description()

    def selected_tool(self) -> OsintTool | None:
        item = self.tools.currentItem()
        if not item:
            return None
        tool_id = item.data(Qt.ItemDataRole.UserRole)
        return next((tool for tool in self.library.tools if tool.id == tool_id), None)

    def show_description(self, *_):
        tool = self.selected_tool()
        self.description.setText(
            f"{tool.description or 'Brak opisu.'}\n\n{tool.url}" if tool else "Wybierz narzędzie."
        )

    def add_category(self):
        name, ok = QInputDialog.getText(self, "Nowa kategoria", "Nazwa:")
        if not ok:
            return
        try:
            category = self.library.add_category(name)
            self.refresh(category.id)
        except ValueError as exc:
            QMessageBox.warning(self, "Kategoria", str(exc))

    def rename_category(self):
        category_id = self.category.currentData()
        if not category_id:
            return
        current = self.library.category(category_id)
        name, ok = QInputDialog.getText(self, "Zmień nazwę kategorii", "Nazwa:", text=current.name)
        if not ok:
            return
        try:
            self.library.rename_category(category_id, name)
            self.refresh(category_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Kategoria", str(exc))

    def delete_category(self):
        category_id = self.category.currentData()
        if not category_id:
            return
        if QMessageBox.question(
            self, "Usuń kategorię",
            "Narzędzia z tej kategorii zostaną przeniesione do innej. Kontynuować?",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.library.delete_category(category_id)
            self.refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Kategoria", str(exc))

    def add_tool(self):
        dialog = ToolDialog(self.library, parent=self)
        if dialog.exec():
            try:
                tool = dialog.build_tool()
                self.library.add_tool(tool.name, tool.url, tool.description, tool.category_id)
                self.refresh(tool.category_id)
            except (ValueError, KeyError) as exc:
                QMessageBox.warning(self, "Narzędzie", str(exc))

    def edit_tool(self):
        tool = self.selected_tool()
        if not tool:
            return
        dialog = ToolDialog(self.library, tool, self)
        if dialog.exec():
            try:
                changed = dialog.build_tool()
                self.library.update_tool(changed)
                self.refresh(changed.category_id)
            except (ValueError, KeyError) as exc:
                QMessageBox.warning(self, "Narzędzie", str(exc))

    def delete_tool(self):
        tool = self.selected_tool()
        if not tool:
            return
        if QMessageBox.question(
            self, "Usuń narzędzie", f"Usunąć „{tool.name}”?"
        ) == QMessageBox.StandardButton.Yes:
            self.library.delete_tool(tool.id)
            self.refresh_tools()

    def open_selected(self):
        tool = self.selected_tool()
        if not tool:
            return
        url = QUrl.fromUserInput(tool.url)
        if url.scheme().lower() not in {"http", "https"} or not url.isValid():
            QMessageBox.warning(
                self, "Nieprawidłowy link",
                "Ze względów bezpieczeństwa można otwierać tylko adresy HTTP i HTTPS.",
            )
            return
        QDesktopServices.openUrl(url)

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QVBoxLayout, QWidget,
)
from app.i18n import language, tr


class SearchDialog(QDialog):
    search_requested = Signal(str)
    navigate_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Szukaj w sprawie")
        self.setModal(False)
        self.resize(900, 520)
        self.setMinimumSize(760, 400)

        self.query = QLineEdit()
        self.query.setPlaceholderText("Wpisz tytuł, treść, tag, źródło lub relację…")
        self.query.textChanged.connect(self._schedule_search)
        self.summary = QLabel("Wpisz co najmniej 2 znaki.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color: #94a3b8;")
        left = QWidget()
        left.setMinimumWidth(280)
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Szukana fraza:"))
        left_layout.addWidget(self.query)
        left_layout.addWidget(self.summary)
        left_layout.addStretch()

        self.results = QListWidget()
        self.results.setWordWrap(True)
        self.results.itemClicked.connect(self._navigate)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Wystąpienia w sprawie:"))
        right_layout.addWidget(self.results, 1)

        layout = QHBoxLayout(self)
        layout.addWidget(left, 0)
        layout.addWidget(right, 1)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(220)
        self.timer.timeout.connect(lambda: self.search_requested.emit(self.query.text().strip()))

    def _schedule_search(self, text: str):
        self.timer.stop()
        if len(text.strip()) < 2:
            self.results.clear()
            self.summary.setText(tr("Wpisz co najmniej 2 znaki."))
            return
        self.timer.start()

    def set_results(self, entries: list[dict]):
        self.results.clear()
        for entry in entries:
            item = QListWidgetItem(entry["label"])
            item.setData(Qt.ItemDataRole.UserRole, (entry["kind"], entry["id"]))
            item.setToolTip(entry.get("tooltip", ""))
            self.results.addItem(item)
        count = len(entries)
        if language() == "en":
            self.summary.setText(
                f"Found {count} {'result' if count == 1 else 'results'}. "
                "Click a result to navigate to the item."
            )
        else:
            self.summary.setText(
                f"Znaleziono {count} wynik{'ów' if count != 1 else ''}. "
                "Kliknij wynik, aby przejść do elementu."
            )

    def _navigate(self, item: QListWidgetItem):
        kind, target_id = item.data(Qt.ItemDataRole.UserRole)
        self.navigate_requested.emit(kind, target_id)

    def show_and_focus(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.query.setFocus()

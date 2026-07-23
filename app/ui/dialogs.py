from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)
from app.i18n import combo_source_text

ITEM_STATUSES = [
    "Nowe", "Do sprawdzenia", "Potwierdzone", "Niepotwierdzone",
    "Odrzucone", "Ważne", "Zarchiwizowane",
]
CLASSIFICATIONS = [
    "Nieokreślona", "Fakt bezpośrednio wynikający ze źródła",
    "Interpretacja analityka", "Przypuszczenie", "Informacja niepotwierdzona",
    "Informacja sprzeczna", "Pytanie otwarte",
]
RELATION_TYPES = [
    "zna", "jest powiązany z", "należy do", "pracuje dla", "jest właścicielem",
    "korzysta z", "kontaktował się z", "mieszka w", "przebywał w",
    "opublikował", "udostępnił", "jest autorem", "jest kopią",
    "może być tą samą osobą", "używa tego samego pseudonimu",
    "używa tego samego adresu e-mail", "używa tego samego numeru telefonu",
    "używa tego samego urządzenia", "wystąpił w tym samym miejscu",
    "wydarzyło się przed", "wydarzyło się po", "potwierdza", "przeczy",
    "relacja nieznana",
]


class CaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nowa sprawa")
        self.name = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(100)
        form = QFormLayout()
        form.addRow("Nazwa:", self.name)
        form.addRow("Opis:", self.description)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self):
        if self.name.text().strip():
            super().accept()


class ItemTextDialog(QDialog):
    def __init__(self, title: str, heading: str, body: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.heading = QLineEdit(heading)
        self.body = QTextEdit(body)
        form = QFormLayout()
        form.addRow("Tytuł / nazwa:", self.heading)
        form.addRow("Treść / opis:", self.body)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)


class PropertiesDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Właściwości OSINT")
        self.uuid = QLineEdit(model.id)
        self.uuid.setReadOnly(True)
        self.uuid.setToolTip("UUID można zaznaczyć i skopiować.")
        self.status = QComboBox()
        self.status.addItems(ITEM_STATUSES)
        self.status.setCurrentText(model.status)
        self.tags = QLineEdit(", ".join(model.tags))
        self.classification = QComboBox()
        self.classification.addItems(CLASSIFICATIONS)
        self.classification.setCurrentText(model.payload.get("classification", "Nieokreślona"))
        self.source = QLineEdit(model.payload.get("source", ""))
        self.source_url = QLineEdit(model.payload.get("source_url", ""))
        self.aliases = QTextEdit("\n".join(model.payload.get("aliases", [])))
        self.aliases.setMaximumHeight(90)
        self.visibility = QComboBox()
        self.visibility.addItems(["publiczne", "wewnętrzne", "poufne", "wyłączone z eksportu"])
        self.visibility.setCurrentText(model.payload.get("visibility", "wewnętrzne"))
        self.layer = QLineEdit(model.payload.get("layer", "Notatki analityczne"))
        form = QFormLayout()
        form.addRow("UUID:", self.uuid)
        form.addRow("Status:", self.status)
        form.addRow("Tagi:", self.tags)
        form.addRow("Klasyfikacja:", self.classification)
        form.addRow("Źródło:", self.source)
        form.addRow("URL źródła:", self.source_url)
        form.addRow("Aliasy (po jednym wierszu):", self.aliases)
        form.addRow("Widoczność w eksporcie:", self.visibility)
        form.addRow("Warstwa:", self.layer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def apply(self, model):
        model.status = combo_source_text(self.status)
        model.tags = [tag.strip() for tag in self.tags.text().split(",") if tag.strip()]
        model.payload["classification"] = combo_source_text(self.classification)
        model.payload["source"] = self.source.text().strip()
        model.payload["source_url"] = self.source_url.text().strip()
        model.payload["aliases"] = [line.strip() for line in self.aliases.toPlainText().splitlines() if line.strip()]
        model.payload["visibility"] = combo_source_text(self.visibility)
        model.payload["layer"] = self.layer.text().strip() or "Notatki analityczne"


class ConnectionDialog(QDialog):
    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Znaczenie relacji")
        self.uuid = QLineEdit(model.id if model else "")
        self.uuid.setReadOnly(True)
        self.uuid.setToolTip("UUID można zaznaczyć i skopiować.")
        self.relation_type = QComboBox()
        self.relation_type.setEditable(True)
        self.relation_type.addItems(RELATION_TYPES)
        self.confidence = QComboBox()
        self.confidence.addItems(["nieznany", "przypuszczenie", "prawdopodobne", "potwierdzone"])
        self.label = QLineEdit()
        self.direction = QComboBox()
        self.direction.addItem("Przód", "forward")
        self.direction.addItem("Tył", "backward")
        if model:
            self.relation_type.setCurrentText(model.relation_type)
            self.confidence.setCurrentText(model.confidence)
            self.label.setText(model.label)
            direction_index = self.direction.findData(model.direction)
            self.direction.setCurrentIndex(max(0, direction_index))
        form = QFormLayout()
        form.addRow("UUID:", self.uuid)
        form.addRow("Typ relacji:", self.relation_type)
        form.addRow("Pewność:", self.confidence)
        form.addRow("Etykieta:", self.label)
        form.addRow("Kierunek strzałek:", self.direction)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def apply(self, model):
        model.relation_type = combo_source_text(self.relation_type).strip() or "relacja nieznana"
        model.confidence = combo_source_text(self.confidence)
        model.label = self.label.text().strip()
        model.direction = self.direction.currentData()


class NoteColorDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zmień kolory notatki")
        fallback = model.payload.get("text_color", "#171717")
        self.colors = {
            "background": QColor(model.payload.get("color", "#facc15")),
            "title": QColor(model.payload.get("title_color", fallback)),
            "body": QColor(model.payload.get("body_color", fallback)),
        }
        self.buttons: dict[str, QPushButton] = {}
        tabs = QTabWidget()
        for key, label, description in (
            ("background", "Tło", "Kolor tła całej notatki"),
            ("title", "Tytuł", "Kolor czcionki tytułu"),
            ("body", "Treść", "Kolor czcionki treści"),
        ):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.addWidget(QLabel(description))
            button = QPushButton()
            button.clicked.connect(lambda _=False, color_key=key: self.choose_color(color_key))
            self.buttons[key] = button
            page_layout.addWidget(button)
            page_layout.addStretch()
            tabs.addTab(page, label)
            self.update_button(key)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self.resize(420, 240)

    def choose_color(self, key: str):
        color = QColorDialog.getColor(self.colors[key], self, "Wybierz kolor")
        if color.isValid():
            self.colors[key] = color
            self.update_button(key)

    def update_button(self, key: str):
        color = self.colors[key]
        foreground = "#111827" if color.lightness() > 145 else "#f8fafc"
        self.buttons[key].setText(f"Wybierz kolor — {color.name().upper()}")
        self.buttons[key].setStyleSheet(
            f"background: {color.name()}; color: {foreground};"
            "border: 1px solid #64748b; padding: 10px;"
        )

    def apply(self, model):
        model.payload["color"] = self.colors["background"].name()
        model.payload["title_color"] = self.colors["title"].name()
        model.payload["body_color"] = self.colors["body"].name()

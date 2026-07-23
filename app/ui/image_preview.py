from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGraphicsPixmapItem,
    QGraphicsScene, QGraphicsView, QHBoxLayout, QLineEdit, QMessageBox,
    QPushButton, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from app.ui.dialogs import CLASSIFICATIONS, ITEM_STATUSES
from app.i18n import combo_source_text, set_combo_source, tr


class ZoomableImageView(QGraphicsView):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self.pixmap_item)
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(Qt.GlobalColor.black)
        self._fitted_once = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._fitted_once and not self.pixmap_item.pixmap().isNull():
            self.fit_image()
            self._fitted_once = True

    def fit_image(self):
        self.resetTransform()
        if not self.pixmap_item.pixmap().isNull():
            self.fitInView(
                self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio
            )

    def zoom_by(self, factor: float):
        current = self.transform().m11()
        if 0.03 < current * factor < 30:
            self.scale(factor, factor)

    def wheelEvent(self, event):
        self.zoom_by(1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.fit_image()
        event.accept()


class ImagePreviewDialog(QDialog):
    def __init__(
        self, pixmap: QPixmap, filename: str, description: str, parent=None,
        *, model=None, save_image=None, save_properties=None,
    ):
        super().__init__(parent)
        self.model = model
        self.save_image_callback = save_image
        self.save_properties_callback = save_properties
        self.original_filename = filename
        self.original_description = description
        self.setWindowTitle(f"Podgląd obrazu — {filename}")
        self.resize(1150, 760)
        self.image_view = ZoomableImageView(pixmap)

        self.filename = QLineEdit(filename)
        self.filename.setReadOnly(True)
        self.filename.setToolTip("Nazwę można zaznaczyć i skopiować.")
        self.description = QTextEdit()
        self.description.setReadOnly(True)
        self.description.setAcceptRichText(False)
        self.description.setPlainText(description)
        self.description.setToolTip("Opis można zaznaczyć i skopiować.")
        self.image_edit_button = QPushButton("Edytuj")
        self.image_save_button = QPushButton("Zapisz")
        self.image_cancel_button = QPushButton("Anuluj")
        self.image_save_button.hide()
        self.image_cancel_button.hide()
        self.image_edit_button.setEnabled(save_image is not None)
        self.image_edit_button.clicked.connect(self.begin_image_edit)
        self.image_save_button.clicked.connect(self.save_image)
        self.image_cancel_button.clicked.connect(self.cancel_image_edit)
        image_buttons = QHBoxLayout()
        image_buttons.addWidget(self.image_edit_button)
        image_buttons.addWidget(self.image_save_button)
        image_buttons.addWidget(self.image_cancel_button)
        image_page = QWidget()
        image_layout = QVBoxLayout(image_page)
        image_form = QFormLayout()
        image_form.addRow("Tytuł / nazwa pliku:", self.filename)
        image_form.addRow("Treść / opis:", self.description)
        image_layout.addLayout(image_form)
        image_layout.addLayout(image_buttons)

        self.property_summary = QTextEdit()
        self.property_summary.setReadOnly(True)
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
        self.property_aliases.setMaximumHeight(85)
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
        self.property_edit_button = QPushButton("Edytuj")
        self.property_save_button = QPushButton("Zapisz")
        self.property_cancel_button = QPushButton("Anuluj")
        self.property_save_button.hide()
        self.property_cancel_button.hide()
        self.property_edit_button.setEnabled(model is not None and save_properties is not None)
        self.property_edit_button.clicked.connect(self.begin_property_edit)
        self.property_save_button.clicked.connect(self.save_osint_properties)
        self.property_cancel_button.clicked.connect(self.cancel_property_edit)
        property_buttons = QHBoxLayout()
        property_buttons.addWidget(self.property_edit_button)
        property_buttons.addWidget(self.property_save_button)
        property_buttons.addWidget(self.property_cancel_button)
        property_page = QWidget()
        property_layout = QVBoxLayout(property_page)
        self.property_uuid = QLineEdit(model.id if model else "")
        self.property_uuid.setReadOnly(True)
        self.property_uuid.setToolTip("UUID można zaznaczyć i skopiować.")
        uuid_layout = QFormLayout()
        uuid_layout.addRow("UUID:", self.property_uuid)
        property_layout.addLayout(uuid_layout)
        property_layout.addWidget(self.property_summary, 1)
        property_layout.addWidget(self.property_form)
        property_layout.addLayout(property_buttons)
        self.refresh_property_summary()

        self.tabs = QTabWidget()
        self.image_tab_index = self.tabs.addTab(image_page, "Zdjęcie")
        self.properties_tab_index = self.tabs.addTab(property_page, "Właściwości OSINT")
        self.tabs.setMinimumWidth(340)
        self.tabs.setMaximumWidth(480)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.image_view)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([800, 350])

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter, 1)
        layout.addWidget(buttons)

    def begin_image_edit(self):
        self.original_filename = self.filename.text()
        self.original_description = self.description.toPlainText()
        self.filename.setReadOnly(False)
        self.description.setReadOnly(False)
        self.image_edit_button.hide()
        self.image_save_button.show()
        self.image_cancel_button.show()
        self.filename.setFocus()

    def cancel_image_edit(self):
        self.filename.setText(self.original_filename)
        self.description.setPlainText(self.original_description)
        self.filename.setReadOnly(True)
        self.description.setReadOnly(True)
        self.image_edit_button.show()
        self.image_save_button.hide()
        self.image_cancel_button.hide()

    def save_image(self):
        if not self.save_image_callback:
            return
        try:
            actual_name = self.save_image_callback(
                self.filename.text(), self.description.toPlainText()
            )
        except (ValueError, FileExistsError, OSError) as exc:
            QMessageBox.warning(self, "Edycja zdjęcia", str(exc))
            return
        self.original_filename = actual_name or self.filename.text()
        self.original_description = self.description.toPlainText()
        self.filename.setText(self.original_filename)
        self.setWindowTitle(f"Podgląd obrazu — {self.original_filename}")
        self.filename.setReadOnly(True)
        self.description.setReadOnly(True)
        self.image_edit_button.show()
        self.image_save_button.hide()
        self.image_cancel_button.hide()

    def refresh_property_summary(self):
        if not self.model:
            self.property_summary.setPlainText("Brak właściwości.")
            return
        payload = self.model.payload
        self.property_summary.setPlainText(
            f"{tr('Status:')} {tr(self.model.status)}\n"
            f"{tr('Tagi:')} {', '.join(self.model.tags) or '—'}\n"
            f"{tr('Klasyfikacja:')} {tr(payload.get('classification', 'Nieokreślona'))}\n"
            f"{tr('Źródło:')} {payload.get('source', '') or '—'}\n"
            f"{tr('URL źródła:')} {payload.get('source_url', '') or '—'}\n"
            f"{tr('Aliasy:')} {', '.join(payload.get('aliases', [])) or '—'}\n"
            f"{tr('Widoczność:')} {tr(payload.get('visibility', 'wewnętrzne'))}\n"
            f"{tr('Warstwa:')} {tr(payload.get('layer', 'Materiały źródłowe'))}\n"
            f"{tr('SHA-256:')} {payload.get('sha256', '—')}\n"
            f"{tr('Rozmiar pliku:')} {payload.get('size_bytes', '—')} B"
        )

    def begin_property_edit(self):
        if not self.model:
            return
        payload = self.model.payload
        set_combo_source(self.property_status, self.model.status)
        self.property_tags.setText(", ".join(self.model.tags))
        set_combo_source(
            self.property_classification, payload.get("classification", "Nieokreślona")
        )
        self.property_source.setText(payload.get("source", ""))
        self.property_source_url.setText(payload.get("source_url", ""))
        self.property_aliases.setPlainText("\n".join(payload.get("aliases", [])))
        set_combo_source(self.property_visibility, payload.get("visibility", "wewnętrzne"))
        self.property_layer.setText(payload.get("layer", "Materiały źródłowe"))
        self.property_summary.hide()
        self.property_form.show()
        self.property_edit_button.hide()
        self.property_save_button.show()
        self.property_cancel_button.show()

    def cancel_property_edit(self):
        self.property_form.hide()
        self.property_summary.show()
        self.property_edit_button.show()
        self.property_save_button.hide()
        self.property_cancel_button.hide()

    def save_osint_properties(self):
        if not self.model or not self.save_properties_callback:
            return
        self.model.status = combo_source_text(self.property_status)
        self.model.tags = [
            tag.strip() for tag in self.property_tags.text().split(",") if tag.strip()
        ]
        payload = self.model.payload
        payload["classification"] = combo_source_text(self.property_classification)
        payload["source"] = self.property_source.text().strip()
        payload["source_url"] = self.property_source_url.text().strip()
        payload["aliases"] = [
            line.strip() for line in self.property_aliases.toPlainText().splitlines()
            if line.strip()
        ]
        payload["visibility"] = combo_source_text(self.property_visibility)
        payload["layer"] = self.property_layer.text().strip() or "Materiały źródłowe"
        self.save_properties_callback()
        self.cancel_property_edit()
        self.refresh_property_summary()

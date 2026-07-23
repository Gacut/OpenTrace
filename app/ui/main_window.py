from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QProcess, QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QDesktopServices, QImage, QKeySequence, QPainter, QPen,
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QDockWidget, QFileDialog, QInputDialog, QLabel,
    QGraphicsItem, QGraphicsOpacityEffect, QHBoxLayout, QMainWindow, QMenu, QMessageBox, QPushButton,
    QToolBar, QToolButton, QStyle, QTabWidget, QVBoxLayout, QWidget,
)

from app.controller import CaseController
from app.i18n import install_translation_filter, journal_title, language, set_language, tr
from app.graphics import BoardView
from app.graphics.items import BaseNodeItem, ConnectionItem, ImageItem
from app.models import AnalysisRecord, ConnectionModel, ItemType
from app.services import (
    AppSettings, CaseManager, ToolLibrary, case_statistics, sha256_file, structural_export,
)
from app.ui.analysis_panel import AnalysisPanel, RecordDialog
from app.ui.dialogs import (
    CaseDialog, ConnectionDialog, ItemTextDialog, NoteColorDialog, PropertiesDialog,
)
from app.ui.note_panel import NotePanel
from app.ui.image_preview import ImagePreviewDialog
from app.ui.search_dialog import SearchDialog
from app.ui.tools_panel import ToolsPanel

DARK_STYLE = """
QWidget { background: #111827; color: #e5e7eb; font-size: 10pt; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #1f2937; }
QLineEdit, QTextEdit, QListWidget { background: #0f172a; border: 1px solid #475569; padding: 5px; }
QPushButton { background: #2563eb; border: 0; border-radius: 4px; padding: 6px 12px; }
QToolTip { background: #f8fafc; color: #111827; }
"""


class AnimatedWelcomeWidget(QWidget):
    """A subtle, drifting network used only behind the welcome screen."""

    def __init__(self, accent_index: int, animation_enabled: bool = True, parent=None):
        super().__init__(parent)
        self.animation_phase = 0.0
        self.accent_index = accent_index
        self._animation_enabled = animation_enabled
        generator = random.Random(2026)
        self._particles = [
            [
                generator.uniform(-0.1, 1.1),
                generator.uniform(-0.1, 1.1),
                generator.uniform(-0.00032, 0.00032),
                generator.uniform(-0.00028, 0.00028),
                generator.uniform(0.35, 1.0),
            ]
            for _ in range(63)
        ]
        # Keep the network extending beyond every edge at all times.
        self._particles[0][:2] = [-0.1, 0.25]
        self._particles[1][:2] = [1.1, 0.7]
        self._particles[2][:2] = [0.35, -0.1]
        self._particles[3][:2] = [0.75, 1.1]
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(33)
        self.animation_timer.timeout.connect(self._advance_animation)
        if animation_enabled:
            self.animation_timer.start()

    def set_animation_enabled(self, enabled: bool):
        self._animation_enabled = enabled
        if enabled:
            self.animation_timer.start()
        else:
            self.animation_timer.stop()
        self.update()

    def _advance_animation(self):
        self.animation_phase += 0.018
        for particle in self._particles:
            particle[0] += particle[2]
            particle[1] += particle[3]
            if particle[0] < -0.12 or particle[0] > 1.12:
                particle[2] *= -1
            if particle[1] < -0.12 or particle[1] > 1.12:
                particle[3] *= -1
        self.update()

    def _mesh_points(self) -> list[QPointF]:
        width, height = max(1, self.width()), max(1, self.height())
        return [QPointF(particle[0] * width, particle[1] * height) for particle in self._particles]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111827"))
        if not self._animation_enabled:
            return
        points = self._mesh_points()
        maximum_distance = max(120.0, min(self.width(), self.height()) * 0.24)
        drawn_connections = set()
        for index, point in enumerate(points):
            neighbours = sorted(
                (
                    ((point - candidate).manhattanLength(), other_index)
                    for other_index, candidate in enumerate(points)
                    if other_index != index
                ),
                key=lambda entry: entry[0],
            )
            connected = 0
            for _, other_index in neighbours:
                delta = point - points[other_index]
                distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
                if distance > maximum_distance:
                    continue
                connection = tuple(sorted((index, other_index)))
                if connection in drawn_connections:
                    continue
                depth = min(self._particles[index][4], self._particles[other_index][4])
                closeness = 1.0 - distance / maximum_distance
                painter.setPen(QPen(QColor(148, 163, 184, int((18 + 62 * closeness) * depth)), 0.7 + depth * 0.45))
                painter.drawLine(point, points[other_index])
                drawn_connections.add(connection)
                connected += 1
                if connected == 3:
                    break

        painter.setPen(Qt.PenStyle.NoPen)
        for index, (point, particle) in enumerate(zip(points, self._particles)):
            depth = particle[4]
            if index == self.accent_index:
                painter.setBrush(QColor(239, 68, 68, 62))
                painter.drawEllipse(point, 11.0, 11.0)
                painter.setBrush(QColor(239, 68, 68, 235))
                painter.drawEllipse(point, 2.4, 2.4)
                continue
            painter.setBrush(QColor(148, 163, 184, int(18 * depth)))
            painter.drawEllipse(point, 5.5 + depth * 3.0, 5.5 + depth * 3.0)
            painter.setBrush(QColor(203, 213, 225, int(95 + 120 * depth)))
            painter.drawEllipse(point, 0.8 + depth * 1.2, 0.8 + depth * 1.2)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller: CaseController | None = None
        self.view: BoardView | None = None
        self.undo_action: QAction | None = None
        self.redo_action: QAction | None = None
        self.last_context_pos = QPointF()
        self.read_only = False
        self._active_right_dock: QDockWidget | None = None
        self.search_dialog: SearchDialog | None = None
        self.tool_library = ToolLibrary()
        self.app_settings = AppSettings()
        set_language(self.app_settings.language)
        install_translation_filter(QApplication.instance())
        self.welcome_accent_index = random.SystemRandom().randrange(63)
        self.setWindowTitle("OpenTrace")
        self.resize(1400, 900)
        self.setStyleSheet(DARK_STYLE)
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self.setCentralWidget(self._build_welcome_widget())
        self.statusBar().showMessage(tr("Dane pozostają lokalnie na tym komputerze."))

    def _build_welcome_widget(self) -> QWidget:
        welcome = AnimatedWelcomeWidget(
            self.welcome_accent_index,
            animation_enabled=not self.app_settings.animation_disabled,
        )
        title = QLabel("OpenTrace")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 24pt; font-weight: 700; color: #f8fafc; background: transparent;"
        )
        subtitle = QLabel("Utwórz nową sprawę lub otwórz istniejący projekt lokalny.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 11pt; color: #94a3b8; background: transparent;")
        self.welcome_new_button = QPushButton("Nowa Sprawa")
        self.welcome_open_button = QPushButton("Otwórz sprawę")
        self.welcome_unpack_button = QPushButton("Rozpakuj sprawę z pliku ZIP")
        for button in (
            self.welcome_new_button,
            self.welcome_open_button,
            self.welcome_unpack_button,
        ):
            button.setMinimumSize(250, 64)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton { background: #2563eb; color: white; border: 1px solid #3b82f6;"
                "border-radius: 10px; padding: 12px 24px; font-size: 14pt; font-weight: 700; }"
                "QPushButton:hover { background: #1d4ed8; }"
                "QPushButton:pressed { background: #1e40af; }"
            )
        self.welcome_new_button.clicked.connect(lambda: self.new_case())
        self.welcome_open_button.clicked.connect(lambda: self.open_case())
        self.welcome_unpack_button.clicked.connect(lambda: self.unpack_case())
        buttons = QHBoxLayout()
        buttons.setSpacing(18)
        buttons.addStretch()
        buttons.addWidget(self.welcome_new_button)
        buttons.addWidget(self.welcome_open_button)
        buttons.addStretch()
        unpack_button_row = QHBoxLayout()
        unpack_button_row.addStretch()
        unpack_button_row.addWidget(self.welcome_unpack_button)
        unpack_button_row.addStretch()
        self.welcome_language_label = QLabel("Język:")
        self.welcome_language_label.setStyleSheet(
            "color: #94a3b8; background: transparent;"
        )
        self.welcome_language_combo = QComboBox()
        self.welcome_language_combo.addItem("Polski", "pl")
        self.welcome_language_combo.addItem("Angielski", "en")
        self.welcome_language_combo.setCurrentIndex(
            max(0, self.welcome_language_combo.findData(self.app_settings.language))
        )
        self.welcome_language_combo.currentIndexChanged.connect(
            lambda _index: self.change_language(self.welcome_language_combo.currentData())
        )
        language_row = QHBoxLayout()
        language_row.addStretch()
        language_row.addWidget(self.welcome_language_label)
        language_row.addWidget(self.welcome_language_combo)
        language_row.addStretch()
        layout = QVBoxLayout(welcome)
        layout.addStretch(2)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(24)
        layout.addLayout(buttons)
        layout.addSpacing(12)
        layout.addLayout(unpack_button_row)
        layout.addStretch(3)
        layout.addLayout(language_row)
        layout.addSpacing(14)
        return welcome

    def _action(self, text, slot, shortcut=None):
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        return action

    def _build_actions(self):
        self.new_action = self._action("Nowa sprawa…", self.new_case, "Ctrl+N")
        self.open_action = self._action("Otwórz sprawę…", self.open_case, "Ctrl+O")
        self.pack_case_action = self._action("Spakuj sprawę do pliku ZIP…", self.pack_case)
        self.unpack_case_action = self._action("Rozpakuj sprawę z pliku ZIP…", self.unpack_case)
        self.save_action = self._action("Zapisz", self.save, "Ctrl+S")
        self.export_action = self._action("Eksport tablicy do PNG…", self.export_png, "Ctrl+E")
        self.export_json_action = self._action("Eksport strukturalny JSON…", self.export_json)
        self.close_case_action = self._action("Zamknij sprawę", self.close_case)
        self.note_action = self._action("Dodaj notatkę", lambda: self.add_note(self.viewport_center()), "Ctrl+Shift+N")
        self.pin_action = self._action("Dodaj pinezkę", lambda: self.add_pin(self.viewport_center()), "Ctrl+Shift+P")
        self.image_action = self._action("Dodaj obraz…", lambda: self.add_image(self.viewport_center()), "Ctrl+Shift+I")
        self.connect_action = self._action("Połącz zaznaczone", self.connect_selected, "Ctrl+L")
        self.delete_action = self._action("Usuń zaznaczone", self.delete_selected, "Delete")
        self.fit_action = self._action("Dopasuj wszystko", lambda: self.view and self.view.fit_all(), "Home")
        self.grid_action = self._action("Pokaż siatkę", self.toggle_grid)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.search_action = self._action("Szukaj…", self.search, "Ctrl+F")
        self.stats_action = self._action("Statystyki sprawy", self.show_statistics)
        self.read_only_action = self._action("Tylko odczyt", self.toggle_read_only)
        self.read_only_action.setCheckable(True)
        self.layer_action = self._action("Pokaż/ukryj warstwę…", self.toggle_layer)
        self.disable_welcome_animation_action = self._action(
            "Wyłącz animację na ekranie głównym", self.toggle_welcome_animation
        )
        self.disable_welcome_animation_action.setCheckable(True)
        self.disable_welcome_animation_action.setChecked(self.app_settings.animation_disabled)

    def _build_menus(self):
        # Keep explicit Python references. PySide may otherwise collect a QMenu
        # wrapper even though its QAction is still present in the menu bar.
        self.file_menu = self.menuBar().addMenu("Plik")
        self.file_menu.addActions([
            self.new_action, self.open_action, self.save_action,
            self.export_action, self.export_json_action,
            self.pack_case_action, self.unpack_case_action,
        ])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.close_case_action)
        self.edit_menu = self.menuBar().addMenu("Edycja")
        self.edit_menu.setMinimumWidth(230)
        self.edit_menu.addActions(
            [self.note_action, self.pin_action, self.image_action, self.connect_action, self.delete_action]
        )
        self.view_menu = self.menuBar().addMenu("Widok")
        self.view_menu.addActions([
            self.fit_action, self.grid_action, self.search_action,
            self.stats_action, self.read_only_action, self.layer_action,
        ])
        self.about_action = self._action("O programie", self.show_about_dialog)
        self.menuBar().addAction(self.about_action)

    def show_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("O programie")
        dialog.setMinimumWidth(500)

        title = QLabel("OpenTrace")
        title.setStyleSheet("font-size: 17pt; font-weight: 700; color: #f8fafc;")
        if language() == "en":
            information_text = (
                "<p>A local application for organizing OSINT analysis and collected materials.</p>"
                "<p><b>Libraries and technologies:</b></p>"
                "<ul>"
                "<li><b>PySide6 (Qt for Python)</b>: application user interface</li>"
                "<li><b>SQLite (sqlite3)</b>: local database provided by the Python standard library</li>"
                "<li><b>Python standard library</b>: zipfile for ZIP archives, hashlib for "
                "SHA-256 checksums, and json for manifests, settings, and data exports</li>"
                "</ul>"
                "<p><b>Development tools:</b></p>"
                "<ul>"
                "<li><b>pytest</b> and <b>pytest-qt</b>: automated testing</li>"
                "<li><b>PyInstaller</b>: building a standalone application</li>"
                "</ul>"
                "<p><b>License:</b> OpenTrace is distributed under the MIT License. "
                "Qt for Python components are used under LGPLv3. Full license texts, "
                "third-party notices, and Qt source/relinking information are included "
                "with the application.</p>"
                '<p>Author: <a href="https://github.com/Gacut">github.com/Gacut</a></p>'
                '<p><a href="https://openai.com/pl-PL/codex/">Created with Codex</a></p>'
            )
        else:
            information_text = (
                "<p>Lokalna aplikacja do organizowania analiz i materiałów OSINT.</p>"
                "<p><b>Biblioteki i technologie:</b></p>"
                "<ul>"
                "<li><b>PySide6 (Qt for Python)</b>: interfejs graficzny aplikacji</li>"
                "<li><b>SQLite (sqlite3)</b>: lokalna baza danych, dostępna w standardowej bibliotece Pythona</li>"
                "<li><b>Standardowa biblioteka Pythona</b>: zipfile do archiwów ZIP, "
                "hashlib do sum SHA-256 oraz json do manifestów, ustawień i eksportu danych</li>"
                "</ul>"
                "<p><b>Narzędzia używane podczas tworzenia:</b></p>"
                "<ul>"
                "<li><b>pytest</b> i <b>pytest-qt</b>: testy automatyczne</li>"
                "<li><b>PyInstaller</b>: przygotowywanie samodzielnej wersji programu</li>"
                "</ul>"
                "<p><b>Licencja:</b> OpenTrace jest udostępniany na licencji MIT. "
                "Komponenty Qt for Python są używane na warunkach LGPLv3. Pełne teksty "
                "licencji, informacje o komponentach oraz instrukcje dotyczące źródeł "
                "i podmiany Qt są dołączone do programu.</p>"
                '<p>Autor: <a href="https://github.com/Gacut">github.com/Gacut</a></p>'
                '<p><a href="https://openai.com/pl-PL/codex/">Stworzone za pomocą Codex</a></p>'
            )
        information = QLabel(information_text)
        information.setOpenExternalLinks(True)
        information.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        information.setWordWrap(True)

        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(dialog.accept)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(close_button)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(information)
        layout.addLayout(button_row)
        dialog.exec()

    def toggle_welcome_animation(self, disabled: bool):
        self.app_settings.animation_disabled = disabled
        self.app_settings.save()
        welcome = self.centralWidget()
        if isinstance(welcome, AnimatedWelcomeWidget):
            welcome.set_animation_enabled(not disabled)

    def change_language(self, language_code: str):
        if language_code == self.app_settings.language:
            return
        self.app_settings.language = language_code
        self.app_settings.save()
        for action in self.language_group.actions():
            action.setChecked(action.data() == language_code)
        if hasattr(self, "welcome_language_combo"):
            self.welcome_language_combo.blockSignals(True)
            self.welcome_language_combo.setCurrentIndex(
                max(0, self.welcome_language_combo.findData(language_code))
            )
            self.welcome_language_combo.blockSignals(False)
        if language_code == "en":
            title = "Language change"
            message = "The language change will be applied after restarting OpenTrace."
        else:
            title = "Zmiana języka"
            message = "Zmiana języka zostanie zastosowana po ponownym uruchomieniu OpenTrace."
        QMessageBox.information(self, title, message)

    def _build_toolbar(self):
        self.main_toolbar = QToolBar("Narzędzia")
        self.main_toolbar.setMovable(False)
        self.main_toolbar.addActions([
            self.note_action, self.pin_action, self.image_action, self.connect_action,
            self.delete_action, self.fit_action, self.search_action,
        ])
        self.addToolBar(self.main_toolbar)
        self.main_toolbar.hide()
        toolbar_view_action = self.main_toolbar.toggleViewAction()
        toolbar_view_action.setText("Górny pasek narzędzi")
        self.view_menu.addAction(toolbar_view_action)
        self.language_menu = self.view_menu.addMenu("Język")
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        for code, label in (("pl", "Polski"), ("en", "Angielski")):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setData(code)
            action.setChecked(self.app_settings.language == code)
            action.triggered.connect(
                lambda checked=False, language_code=code: self.change_language(language_code)
            )
            self.language_group.addAction(action)
            self.language_menu.addAction(action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.disable_welcome_animation_action)
        self.tools_panel = ToolsPanel(self.tool_library, self)
        self.tools_dock = QDockWidget("Zasobnik narzędzi OSINT", self)
        self.tools_dock.setWidget(self.tools_panel)
        self.tools_dock.setMinimumWidth(400)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tools_dock)
        self.tools_dock.hide()
        # Floating edge button: unlike a QToolBar it does not reserve a visible
        # strip beside the board while the tools dock is closed.
        self.tools_toggle_action = QAction("⚙", self)
        self.tools_toggle_action.setToolTip(tr("Wysuń zasobnik narzędzi OSINT"))
        self.tools_toggle_action.triggered.connect(self.toggle_tools_panel)
        self.tools_toggle_button = QToolButton(self)
        self.tools_toggle_button.setDefaultAction(self.tools_toggle_action)
        self.tools_toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.tools_toggle_button.setFixedSize(62, 52)
        self.tools_toggle_button.setStyleSheet(
            "QToolButton { background: #1f2937; border: 1px solid #475569;"
            "border-radius: 11px; font-size: 14pt; padding: 4px; }"
            "QToolButton:hover { background: #334155; }"
            "QToolButton:pressed { background: #475569; }"
        )
        self.tools_toggle_button.show()
        self.tools_toggle_button.raise_()
        self.tools_dock.visibilityChanged.connect(self.update_tools_toggle)
        self.tools_dock.dockLocationChanged.connect(lambda _: self._schedule_edge_buttons())
        self.tools_dock.topLevelChanged.connect(lambda _: self._schedule_edge_buttons())
        self.analysis_panel = AnalysisPanel(lambda: self.controller, self)
        self.analysis_panel.navigate_requested.connect(self.navigate_to_item)
        self.analysis_dock = QDockWidget("Organizacja analizy", self)
        self.analysis_dock.setWidget(self.analysis_panel)
        self.analysis_dock.setMinimumWidth(390)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.analysis_dock)
        self.analysis_dock.hide()
        self.note_panel = NotePanel(lambda: self.controller, self)
        self.note_dock = QDockWidget("Notatka", self)
        self.note_dock.setWidget(self.note_panel)
        self.note_dock.setMinimumWidth(390)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.note_dock)
        self.setTabPosition(
            Qt.DockWidgetArea.RightDockWidgetArea, QTabWidget.TabPosition.North
        )
        self.tabifyDockWidget(self.analysis_dock, self.note_dock)
        self.note_dock.hide()
        self._build_right_panel_buttons()
        self._set_edge_buttons_enabled(False)

    def _edge_button_style(self) -> str:
        return (
            "QToolButton { background: #1f2937; border: 1px solid #475569;"
            "border-radius: 11px; font-size: 14pt; padding: 4px; }"
            "QToolButton:hover { background: #334155; }"
            "QToolButton:pressed { background: #475569; }"
        )

    def _set_edge_buttons_enabled(self, enabled: bool):
        for name in (
            "tools_toggle_action", "fit_toggle_action", "search_toggle_action",
            "analysis_toggle_action", "note_toggle_action",
        ):
            action = getattr(self, name, None)
            if action:
                action.setEnabled(enabled)
        for name in (
            "tools_toggle_button", "fit_toggle_button", "search_toggle_button",
            "analysis_toggle_button", "note_toggle_button",
        ):
            button = getattr(self, name, None)
            if button:
                button.setEnabled(enabled)
                effect = button.graphicsEffect()
                if not isinstance(effect, QGraphicsOpacityEffect):
                    effect = QGraphicsOpacityEffect(button)
                    button.setGraphicsEffect(effect)
                effect.setOpacity(1.0 if enabled else 0.4)

    def _build_right_panel_buttons(self):
        self.fit_toggle_action = QAction("⛶", self)
        self.fit_toggle_action.setToolTip(tr("Dopasuj wszystko"))
        self.fit_toggle_action.triggered.connect(lambda: self.fit_action.trigger())
        self.fit_toggle_button = QToolButton(self)
        self.fit_toggle_button.setDefaultAction(self.fit_toggle_action)

        self.search_toggle_action = QAction("🔍", self)
        self.search_toggle_action.setToolTip(tr("Szukaj w sprawie"))
        self.search_toggle_action.triggered.connect(lambda: self.search())
        self.search_toggle_button = QToolButton(self)
        self.search_toggle_button.setDefaultAction(self.search_toggle_action)

        self.analysis_toggle_action = QAction("📊", self)
        self.analysis_toggle_action.setToolTip(tr("Wysuń panel analizy"))
        self.analysis_toggle_action.triggered.connect(
            lambda: self._toggle_right_dock(self.analysis_dock)
        )
        self.analysis_toggle_button = QToolButton(self)
        self.analysis_toggle_button.setDefaultAction(self.analysis_toggle_action)

        self.note_toggle_action = QAction("📝", self)
        self.note_toggle_action.setToolTip(tr("Wysuń panel notatki"))
        self.note_toggle_action.triggered.connect(
            lambda: self._toggle_right_dock(self.note_dock)
        )
        self.note_toggle_button = QToolButton(self)
        self.note_toggle_button.setDefaultAction(self.note_toggle_action)

        for button in (
            self.fit_toggle_button,
            self.search_toggle_button,
            self.analysis_toggle_button,
            self.note_toggle_button,
        ):
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setFixedSize(68, 52)
            button.setStyleSheet(self._edge_button_style())
            button.show()
            button.raise_()
        self.analysis_dock.visibilityChanged.connect(
            lambda visible: self._update_right_toggle("analysis", visible)
        )
        self.note_dock.visibilityChanged.connect(
            lambda visible: self._update_right_toggle("note", visible)
        )
        self._position_right_panel_buttons()

    def _toggle_right_dock(self, dock: QDockWidget):
        show = not dock.isVisible()
        dock.setVisible(show)
        if show:
            self._active_right_dock = dock
            dock.raise_()
        elif self._active_right_dock is dock:
            self._active_right_dock = next(
                (candidate for candidate in (self.analysis_dock, self.note_dock)
                 if candidate is not dock and candidate.isVisible()),
                None,
            )
        self._position_all_edge_buttons()
        self._schedule_edge_buttons()

    def _update_right_toggle(self, kind: str, visible: bool):
        dock = self.analysis_dock if kind == "analysis" else self.note_dock
        if visible:
            self._active_right_dock = dock
        elif self._active_right_dock is dock:
            self._active_right_dock = next(
                (candidate for candidate in (self.analysis_dock, self.note_dock)
                 if candidate is not dock and candidate.isVisible()),
                None,
            )
        if kind == "analysis":
            self.analysis_toggle_action.setToolTip(
                tr("Schowaj panel analizy" if visible else "Wysuń panel analizy")
            )
        else:
            self.note_toggle_action.setToolTip(
                tr("Schowaj panel notatki" if visible else "Wysuń panel notatki")
            )
        self._schedule_edge_buttons()

    def _position_right_panel_buttons(self):
        if not hasattr(self, "analysis_toggle_button"):
            return
        button_width = self.analysis_toggle_button.width()
        scrollbar_width = (
            self.view.verticalScrollBar().width()
            if self.view and self.view.verticalScrollBar().isVisible()
            else self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        )
        right_inset = scrollbar_width + 12
        window_edge_x = self.width() - button_width - right_inset
        x = window_edge_x
        visible_dock = self._active_right_dock
        if visible_dock:
            if (
                visible_dock.isVisible()
                and not visible_dock.isFloating()
                and self.dockWidgetArea(visible_dock) == Qt.DockWidgetArea.RightDockWidgetArea
            ):
                panel_left = visible_dock.geometry().left()
                # Ignore transient geometry reported while Qt switches tabified
                # docks. A delayed second pass will pick up the settled value.
                if button_width + 12 < panel_left < self.width():
                    x = panel_left - button_width - right_inset
        x = max(6, min(window_edge_x, x))
        top_y = self.menuBar().height() + 56
        self.search_toggle_button.move(max(0, x), top_y)
        horizontal_scrollbar_height = (
            self.view.horizontalScrollBar().height()
            if self.view and self.view.horizontalScrollBar().isVisible()
            else self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        )
        bottom_y = (
            self.height() - self.fit_toggle_button.height()
            - self.statusBar().height() - horizontal_scrollbar_height - 12
        )
        self.fit_toggle_button.move(max(0, x), max(top_y, bottom_y))
        center_y = (self.height() - (self.analysis_toggle_button.height() * 2 + 10)) // 2
        self.analysis_toggle_button.move(max(0, x), max(self.menuBar().height() + 56, center_y))
        self.note_toggle_button.move(
            max(0, x),
            max(self.menuBar().height() + 56, center_y) + self.analysis_toggle_button.height() + 10,
        )
        self.fit_toggle_button.raise_()
        self.search_toggle_button.raise_()
        self.analysis_toggle_button.raise_()
        self.note_toggle_button.raise_()

    def toggle_tools_panel(self):
        self.tools_dock.setVisible(not self.tools_dock.isVisible())
        if self.tools_dock.isVisible():
            self.tools_dock.raise_()
        self._position_all_edge_buttons()
        self._schedule_edge_buttons()

    def update_tools_toggle(self, visible: bool):
        self.tools_toggle_action.setToolTip(
            tr("Schowaj zasobnik narzędzi OSINT" if visible
               else "Wysuń zasobnik narzędzi OSINT")
        )
        self._schedule_edge_buttons()

    def _position_tools_toggle(self):
        if not hasattr(self, "tools_toggle_button"):
            return
        x = 6
        if (
            self.tools_dock.isVisible()
            and not self.tools_dock.isFloating()
            and self.dockWidgetArea(self.tools_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
        ):
            panel_right = self.tools_dock.geometry().right()
            candidate = panel_right + 7
            maximum = self.width() - self.tools_toggle_button.width() - 6
            if 0 < panel_right < self.width() - self.tools_toggle_button.width():
                x = max(6, min(maximum, candidate))
        top = self.menuBar().height() + 56
        y = max(top, (self.height() - self.tools_toggle_button.height()) // 2)
        self.tools_toggle_button.move(x, y)
        self.tools_toggle_button.raise_()

    def _schedule_edge_buttons(self):
        QTimer.singleShot(0, self._position_all_edge_buttons)
        QTimer.singleShot(75, self._position_all_edge_buttons)

    def _position_all_edge_buttons(self):
        self._position_tools_toggle()
        self._position_right_panel_buttons()
        for name in (
            "tools_toggle_button", "fit_toggle_button", "search_toggle_button",
            "analysis_toggle_button", "note_toggle_button",
        ):
            button = getattr(self, name, None)
            if button:
                button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_all_edge_buttons()

    def _set_controller(self, controller: CaseController):
        if self.controller:
            self.controller.close()
        self.controller = controller
        self.view = BoardView(controller.scene)
        self.view.context_position.connect(self.show_context_menu)
        self.view.files_dropped.connect(self.import_dropped_files)
        controller.scene.edit_requested.connect(self.edit_item)
        controller.scene.preview_requested.connect(self.preview_image)
        controller.saved.connect(lambda: self.statusBar().showMessage(tr("Zapisano"), 2500))
        controller.error.connect(lambda message: QMessageBox.critical(self, "Błąd", message))
        controller.dirty_changed.connect(self._update_title)
        if self.undo_action:
            self.edit_menu.removeAction(self.undo_action)
            self.undo_action.deleteLater()
        if self.redo_action:
            self.edit_menu.removeAction(self.redo_action)
            self.redo_action.deleteLater()
        self.undo_action = controller.undo_stack.createUndoAction(self, "Cofnij")
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.redo_action = controller.undo_stack.createRedoAction(self, "Ponów")
        self.redo_action.setShortcuts([QKeySequence.StandardKey.Redo, QKeySequence("Ctrl+Shift+Z")])
        controller.undo_stack.indexChanged.connect(self.analysis_panel.refresh)
        first_edit_action = self.edit_menu.actions()[0] if self.edit_menu.actions() else None
        self.edit_menu.insertAction(first_edit_action, self.undo_action)
        self.edit_menu.insertAction(first_edit_action, self.redo_action)
        self.edit_menu.insertSeparator(first_edit_action)
        self.setCentralWidget(self.view)
        self._set_edge_buttons_enabled(True)
        self.analysis_panel.refresh()
        self._restore_camera()
        self._update_title(False)
        # setCentralWidget() places the new board viewport above floating edge
        # controls. Raise them again immediately and after Qt settles layout.
        self._position_all_edge_buttons()
        self._schedule_edge_buttons()

    def showEvent(self, event):
        super().showEvent(event)
        self._position_all_edge_buttons()
        self._schedule_edge_buttons()

    def _update_title(self, dirty=False):
        name = self.controller.metadata.name if self.controller else ""
        self.setWindowTitle(f"{'*' if dirty else ''}{name} — OpenTrace")

    def new_case(self):
        dialog = CaseDialog(self)
        if not dialog.exec():
            return
        root = QFileDialog.getExistingDirectory(self, "Wybierz pusty katalog nadrzędny")
        if not root:
            return
        case_root = Path(root) / self._safe_name(dialog.name.text())
        try:
            paths, db, metadata = CaseManager.create(case_root, dialog.name.text().strip(),
                                                     dialog.description.toPlainText())
            self._set_controller(CaseController(paths, db, metadata))
        except Exception as exc:
            QMessageBox.critical(self, "Nie udało się utworzyć sprawy", str(exc))

    def open_case(self):
        root = QFileDialog.getExistingDirectory(self, "Wybierz katalog sprawy")
        if not root:
            return
        try:
            paths, db, metadata = CaseManager.open(Path(root))
            self._set_controller(CaseController(paths, db, metadata))
        except Exception as exc:
            QMessageBox.critical(self, "Nie udało się otworzyć sprawy", str(exc))

    def pack_case(self):
        if not self.require_case():
            return
        self.save()
        root = self.controller.paths.root
        default_path = root.parent / f"{root.name}.zip"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Spakuj sprawę do pliku ZIP", str(default_path), "Archiwa ZIP (*.zip)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix.lower() != ".zip":
            target = target.with_suffix(".zip")
        try:
            CaseManager.pack(self.controller.paths, target)
            self.statusBar().showMessage(f"{tr('Spakowano sprawę:')} {target}", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Nie udało się spakować sprawy", str(exc))

    def unpack_case(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Wybierz archiwum sprawy", "", "Archiwa ZIP (*.zip)"
        )
        if not filename:
            return
        archive_path = Path(filename)
        folder_name, accepted = QInputDialog.getText(
            self, "Nazwa folderu sprawy", "Nazwa folderu:", text=archive_path.stem
        )
        if not accepted:
            return
        parent = QFileDialog.getExistingDirectory(
            self, "Wybierz miejsce dla rozpakowanej sprawy"
        )
        if not parent:
            return
        target_root = Path(parent) / self._safe_name(folder_name)
        try:
            CaseManager.unpack(archive_path, target_root)
            paths, db, metadata = CaseManager.open(target_root)
            self._set_controller(CaseController(paths, db, metadata))
            self.statusBar().showMessage(
                f"{tr('Rozpakowano i otwarto sprawę:')} {target_root}", 5000
            )
        except Exception as exc:
            QMessageBox.critical(self, "Nie udało się rozpakować sprawy", str(exc))

    def close_case(self):
        if not self.controller:
            return
        controller = self.controller
        self._save_camera()
        controller.save()
        try:
            CaseManager.backup(controller.paths)
        except OSError:
            pass
        controller.close()
        self.controller = None
        self.view = None

        if self.search_dialog:
            self.search_dialog.close()
            self.search_dialog = None
        self.tools_dock.hide()
        self.analysis_dock.hide()
        self.note_dock.hide()
        self._active_right_dock = None
        self.analysis_panel.refresh()
        self.read_only = False
        self.read_only_action.setChecked(False)

        for action_name in ("undo_action", "redo_action"):
            action = getattr(self, action_name)
            if action:
                self.edit_menu.removeAction(action)
                action.deleteLater()
                setattr(self, action_name, None)

        self.setCentralWidget(self._build_welcome_widget())
        self.setWindowTitle("OpenTrace")
        self._set_edge_buttons_enabled(False)
        self.statusBar().showMessage(tr("Sprawa została zapisana i zamknięta."), 4000)
        self._position_all_edge_buttons()
        self._schedule_edge_buttons()

    @staticmethod
    def _safe_name(name: str) -> str:
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
        return safe or "Nowa sprawa"

    def require_case(self) -> bool:
        if not self.controller:
            QMessageBox.information(self, "Brak sprawy", "Najpierw utwórz lub otwórz sprawę.")
            return False
        return True

    def can_edit(self) -> bool:
        if not self.require_case():
            return False
        if self.read_only:
            self.statusBar().showMessage(
                tr("Tryb tylko do odczytu — edycja jest zablokowana."), 4000
            )
            return False
        return True

    def viewport_center(self) -> QPointF:
        return self.view.mapToScene(self.view.viewport().rect().center()) if self.view else QPointF()

    def add_note(self, pos):
        if not self.can_edit():
            return
        dialog = ItemTextDialog("Nowa notatka", tr("Nowa notatka"), parent=self)
        if dialog.exec():
            self.controller.add_note(pos, dialog.heading.text(), dialog.body.toPlainText())

    def add_pin(self, pos):
        if not self.can_edit():
            return
        name, ok = QInputDialog.getText(self, "Nowa pinezka", "Nazwa:")
        if ok:
            self.controller.add_pin(pos, name or "Pinezka")

    def add_image(self, pos):
        if not self.can_edit():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Dodaj obraz", "", "Obrazy (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if filename:
            try:
                source = Path(filename)
                duplicate = self.controller.duplicate_image(sha256_file(source))
                reuse = None
                if duplicate:
                    box = QMessageBox(self)
                    box.setWindowTitle("Wykryto identyczny plik")
                    box.setText(
                        f"Plik ma taki sam SHA-256 jak „{duplicate.payload.get('filename', '')}”."
                    )
                    reuse_button = box.addButton("Użyj istniejącego pliku", QMessageBox.ButtonRole.AcceptRole)
                    copy_button = box.addButton("Zaimportuj osobną kopię", QMessageBox.ButtonRole.ActionRole)
                    box.addButton(QMessageBox.StandardButton.Cancel)
                    box.exec()
                    if box.clickedButton() is reuse_button:
                        reuse = duplicate
                    elif box.clickedButton() is not copy_button:
                        return
                self.controller.add_image(pos, source, reuse)
            except Exception as exc:
                QMessageBox.critical(self, "Import obrazu", str(exc))

    def connect_selected(self):
        if not self.can_edit():
            return
        try:
            template = ConnectionModel("", "")
            dialog = ConnectionDialog(template, self)
            if dialog.exec():
                dialog.apply(template)
                self.controller.connect_selected(template)
        except ValueError as exc:
            QMessageBox.information(self, "Łączenie", str(exc))

    def delete_selected(self):
        if self.controller and not self.read_only:
            self.controller.delete_selected()
            self.analysis_panel.refresh()

    def show_context_menu(self, scene_pos, global_pos):
        if not self.controller:
            return
        self.last_context_pos = scene_pos
        selected = self.controller.scene.itemAt(scene_pos, self.view.transform())
        menu = QMenu(self)
        if isinstance(selected, BaseNodeItem):
            selected.setSelected(True)
            menu.addAction(
                "Edycja", lambda: self.edit_item(selected.model.id, start_edit=True)
            )
            if self._selection_can_be_connected():
                menu.addAction("Połącz zaznaczone", self.connect_selected)
            menu.addAction("Właściwości OSINT", lambda: self.edit_properties(selected))
            menu.addAction("Utwórz zadanie", lambda: self.add_record_for_item("task", selected.model.id))
            menu.addAction("Dodaj do weryfikacji",
                           lambda: self.add_record_for_item("verification", selected.model.id))
            if isinstance(selected, ImageItem):
                menu.addAction("Podgląd obrazu", lambda: self.preview_image(selected.model.id))
                menu.addAction(
                    "Pokaż w eksploratorze plików",
                    lambda: self.show_image_in_explorer(selected),
                )
            menu.addAction("Zmień kolor", lambda: self.change_color(selected))
            menu.addAction("Duplikuj", lambda: self.duplicate(selected))
            menu.addAction("Zablokuj" if not selected.model.locked else "Odblokuj",
                           lambda: self.toggle_lock(selected))
            menu.addSeparator()
            menu.addAction("Usuń", self.delete_selected)
        elif isinstance(selected, ConnectionItem):
            selected.setSelected(True)
            if self._selection_can_be_connected():
                menu.addAction("Połącz zaznaczone", self.connect_selected)
            menu.addAction("Edytuj znaczenie relacji", lambda: self.edit_connection(selected))
            menu.addAction("Zmień kolor linii", lambda: self.change_connection_color(selected))
            menu.addAction("Usuń", self.delete_selected)
        else:
            menu.addAction("Dodaj notatkę", lambda: self.add_note(scene_pos))
            menu.addAction("Dodaj zdjęcie", lambda: self.add_image(scene_pos))
            menu.addAction("Dodaj pinezkę", lambda: self.add_pin(scene_pos))
            menu.addSeparator()
            menu.addAction("Wyśrodkuj widok tutaj", lambda: self.view.centerOn(scene_pos))
        menu.exec(global_pos)

    def _selection_can_be_connected(self) -> bool:
        if not self.controller:
            return False
        selected = self.controller.scene.selectedItems()
        nodes = [item for item in selected if isinstance(item, BaseNodeItem)]
        edges = [item for item in selected if isinstance(item, ConnectionItem)]
        return (len(nodes) == 2 and not edges) or (len(nodes) == 1 and len(edges) == 1)

    def edit_item(self, item_id, start_edit=False):
        item = self.controller.scene.nodes.get(item_id) if self.controller else None
        if not item:
            return
        if item.model.type == ItemType.NOTE:
            self.note_panel.show_note(item_id)
            self.note_dock.show()
            self._active_right_dock = self.note_dock
            self.note_dock.raise_()
            self._position_all_edge_buttons()
            self._schedule_edge_buttons()
            self.note_panel.edit_button.setEnabled(not self.read_only and not item.model.locked)
            if start_edit and not self.read_only and not item.model.locked:
                self.note_panel.begin_edit()
            return
        if item.model.type == ItemType.IMAGE:
            self.preview_image(item_id, tab="image", start_edit=True)
            return
        if item.model.locked or self.read_only:
            return
        payload = item.model.payload
        if item.model.type == ItemType.IMAGE:
            heading = payload.get("filename", "")
            body = payload.get("caption", "")
        else:
            heading = payload.get("title") or payload.get("name") or ""
            body = payload.get("text") or payload.get("description", "")
        dialog = ItemTextDialog("Edytuj element", heading, body, self)
        if dialog.exec():
            if item.model.type == ItemType.NOTE:
                payload["title"], payload["text"] = dialog.heading.text(), dialog.body.toPlainText()
            elif item.model.type == ItemType.PIN:
                payload["name"], payload["description"] = dialog.heading.text(), dialog.body.toPlainText()
            else:
                try:
                    self.controller.rename_image(item.model.id, dialog.heading.text())
                except (ValueError, FileExistsError, OSError) as exc:
                    QMessageBox.warning(self, "Zmiana nazwy obrazu", str(exc))
                    return
                payload["caption"] = dialog.body.toPlainText()
            item.update()
            self.controller.mark_dirty()

    def change_color(self, item):
        if self.read_only:
            return
        if item.model.type == ItemType.NOTE:
            dialog = NoteColorDialog(item.model, self)
            if dialog.exec():
                dialog.apply(item.model)
                item.update()
                self.controller.mark_dirty()
                self.controller.log_event(
                    "Zmieniono kolory notatki", "element", item_ids=[item.model.id]
                )
            return
        color = QColorDialog.getColor(QColor(item.model.payload.get("color", "#facc15")), self)
        if color.isValid():
            item.model.payload["color"] = color.name()
            item.update()
            self.controller.mark_dirty()

    def change_connection_color(self, edge):
        if self.read_only:
            return
        color = QColorDialog.getColor(QColor(edge.model.color), self)
        if color.isValid():
            edge.model.color = color.name()
            edge.update_path()
            self.controller.mark_dirty()

    def duplicate(self, item):
        if self.read_only:
            return
        from app.commands import AddItemCommand
        self.controller.undo_stack.push(AddItemCommand(self.controller, item.model.copy()))

    def import_dropped_files(self, pos, files):
        if not self.controller:
            return
        supported = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
        imported = 0
        for index, filename in enumerate(files):
            path = Path(filename)
            if path.suffix.lower() in supported:
                try:
                    offset = QPointF((index % 4) * 40, (index // 4) * 40)
                    self.controller.add_image(pos + offset, path)
                    imported += 1
                except Exception as exc:
                    QMessageBox.warning(self, "Import obrazu", f"{path.name}: {exc}")
        if imported:
            self.statusBar().showMessage(f"{tr('Zaimportowano obrazów:')} {imported}", 4000)

    def toggle_lock(self, item):
        if self.read_only:
            return
        item.model.locked = not item.model.locked
        item.sync_lock()
        self.controller.mark_dirty()

    def toggle_grid(self, checked):
        if self.controller:
            self.controller.scene.grid_enabled = checked
            self.controller.scene.invalidate()

    def search(self):
        if not self.require_case():
            return
        if self.search_dialog is None:
            self.search_dialog = SearchDialog(self)
            self.search_dialog.search_requested.connect(self._perform_live_search)
            self.search_dialog.navigate_requested.connect(self._navigate_search_result)
        self.search_dialog.show_and_focus()
        if len(self.search_dialog.query.text().strip()) >= 2:
            self._perform_live_search(self.search_dialog.query.text().strip())

    @staticmethod
    def _search_snippet(text: str, query: str, radius: int = 42) -> str:
        flat = " ".join(text.split())
        index = flat.casefold().find(query.casefold())
        if index < 0:
            return flat[: radius * 2]
        start = max(0, index - radius)
        end = min(len(flat), index + len(query) + radius)
        return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")

    def _perform_live_search(self, query: str):
        if not self.controller or not self.search_dialog or len(query) < 2:
            return
        entries = []
        for node in self.controller.scene.nodes.values():
            model = node.model
            searchable = " ".join([
                model.id, json.dumps(model.payload, ensure_ascii=False), " ".join(model.tags),
                model.status, model.type.value,
            ])
            if query.casefold() not in searchable.casefold():
                continue
            title = (
                model.payload.get("title") or model.payload.get("name")
                or model.payload.get("filename") or "Element"
            )
            entries.append({
                "kind": "node", "id": model.id,
                "label": f"{title}  [{model.type.value}]\n{self._search_snippet(searchable, query)}",
                "tooltip": f"UUID: {model.id}",
            })
        for edge in self.controller.scene.edges.values():
            searchable = (
                f"{edge.model.id} {edge.model.label} "
                f"{edge.model.relation_type} {edge.model.confidence}"
            )
            if query.casefold() in searchable.casefold():
                entries.append({
                    "kind": "edge", "id": edge.model.id,
                    "label": f"Relacja: {edge.model.label or edge.model.relation_type}\n"
                             f"{self._search_snippet(searchable, query)}",
                    "tooltip": f"UUID relacji: {edge.model.id}",
                })
        for record in self.controller.repository.search_records(query):
            if not record.item_ids:
                continue
            record_title = journal_title(record.title) if record.kind == "journal" else record.title
            entries.append({
                "kind": "node", "id": record.item_ids[0],
                "label": f"{record_title}  [{tr(record.kind)}: {tr(record.status)}]\n"
                         f"{self._search_snippet(json.dumps(record.data, ensure_ascii=False), query)}",
                "tooltip": "Powiązany rekord analityczny",
            })
        self.search_dialog.set_results(entries[:300])

    def _navigate_search_result(self, kind: str, target_id: str):
        if not self.controller:
            return
        for selected in self.controller.scene.selectedItems():
            selected.setSelected(False)
        if kind == "node" and target_id in self.controller.scene.nodes:
            item = self.controller.scene.nodes[target_id]
            item.setSelected(True)
            self.view.centerOn(item)
        elif kind == "edge" and target_id in self.controller.scene.edges:
            edge = self.controller.scene.edges[target_id]
            edge.setSelected(True)
            self.view.centerOn(edge.center())

    def edit_properties(self, item):
        if item.model.type == ItemType.NOTE:
            self.note_panel.show_note(item.model.id, tab="properties")
            self.note_dock.show()
            self._active_right_dock = self.note_dock
            self.note_dock.raise_()
            editable = not self.read_only and not item.model.locked
            self.note_panel.property_edit_button.setEnabled(editable)
            self._position_all_edge_buttons()
            self._schedule_edge_buttons()
            return
        if item.model.type == ItemType.IMAGE:
            self.preview_image(item.model.id, tab="properties", start_edit=False)
            return
        if self.read_only:
            return
        dialog = PropertiesDialog(item.model, self)
        if dialog.exec():
            dialog.apply(item.model)
            item.update()
            self.controller.mark_dirty()
            self.controller.log_event("Zmieniono właściwości elementu", "element",
                                      item_ids=[item.model.id])

    def edit_connection(self, edge):
        if self.read_only:
            return
        dialog = ConnectionDialog(edge.model, self)
        if dialog.exec():
            dialog.apply(edge.model)
            edge.update_path()
            self.controller.mark_dirty()
            self.controller.log_event("Zmieniono znaczenie relacji", "relacja",
                                      item_ids=[edge.model.source_id, edge.model.target_id],
                                      connection_id=edge.model.id)

    def add_record_for_item(self, kind, item_id):
        if self.read_only:
            return
        dialog = RecordDialog(kind, [item_id], parent=self, controller=self.controller)
        if dialog.exec():
            self.controller.save_record(dialog.build_record())
            self.analysis_panel.refresh()
            self.analysis_dock.show()

    def navigate_to_item(self, item_id):
        if not self.controller:
            return
        for selected in self.controller.scene.selectedItems():
            selected.setSelected(False)
        if item_id in self.controller.scene.nodes:
            item = self.controller.scene.nodes[item_id]
            item.setSelected(True)
            self.view.centerOn(item)
        elif item_id in self.controller.scene.edges:
            edge = self.controller.scene.edges[item_id]
            edge.setSelected(True)
            self.view.centerOn(edge.center())

    def toggle_read_only(self, checked):
        self.read_only = checked
        if self.controller:
            for item in self.controller.scene.nodes.values():
                item.setFlag(
                    QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
                    not checked and not item.model.locked,
                )
        if checked:
            self.note_panel.cancel()
            self.note_panel.cancel_property_edit()
            self.note_panel.edit_button.setEnabled(False)
            self.note_panel.property_edit_button.setEnabled(False)
        elif self.controller and self.note_panel.item_id:
            note = self.controller.scene.nodes.get(self.note_panel.item_id)
            editable = bool(note and not note.model.locked)
            self.note_panel.edit_button.setEnabled(editable)
            self.note_panel.property_edit_button.setEnabled(editable)
        self.statusBar().showMessage(
            tr("Tryb tylko do odczytu włączony.")
            if checked else tr("Edycja ponownie włączona."), 4000
        )

    def export_json(self):
        if not self.require_case():
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Eksport strukturalny", "", "JSON (*.json)")
        if not filename:
            return
        if not filename.lower().endswith(".json"):
            filename += ".json"
        items, connections = self.controller.scene.models()
        records = self.controller.repository.load_records()
        structural_export(Path(filename), self.controller.metadata.to_dict(), items, connections, records)
        self.controller.log_event("Wyeksportowano dane strukturalne JSON", "eksport")
        self.statusBar().showMessage(f"{tr('Wyeksportowano:')} {filename}", 5000)

    def show_statistics(self):
        if not self.require_case():
            return
        items, connections = self.controller.scene.models()
        stats = case_statistics(items, connections, self.controller.repository.load_records())
        tags = ", ".join(f"{tag} ({count})" for tag, count in stats["top_tags"]) or "brak"
        QMessageBox.information(
            self, "Statystyki sprawy",
            f"Elementy: {stats['elements']}\nPołączenia: {stats['connections']}\n"
            f"Źródła: {stats['sources']}\nHipotezy: {stats['hypotheses']}\n"
            f"Materiały niezweryfikowane: {stats['unverified']}\n"
            f"Otwarte zadania: {stats['open_tasks']}\nNajczęstsze tagi: {tags}\n\n"
            "Statystyki służą wyłącznie nawigacji i nie oceniają znaczenia informacji."
        )

    def available_layers(self):
        if not self.controller:
            return []
        return sorted({
            node.model.payload.get("layer", "Notatki analityczne")
            for node in self.controller.scene.nodes.values()
        })

    def toggle_layer(self):
        if not self.require_case():
            return
        layers = self.available_layers()
        if not layers:
            return
        layer, ok = QInputDialog.getItem(self, "Warstwy", "Warstwa:", layers, 0, False)
        if not ok:
            return
        nodes = [
            node for node in self.controller.scene.nodes.values()
            if node.model.payload.get("layer", "Notatki analityczne") == layer
        ]
        visible = not any(node.isVisible() for node in nodes)
        for node in nodes:
            node.setVisible(visible)

    def preview_image(self, item_id, tab="image", start_edit=False):
        item = self.controller.scene.nodes.get(item_id)
        if not isinstance(item, ImageItem):
            return
        editable = not self.read_only and not item.model.locked

        def save_image_changes(filename, description):
            actual_name = self.controller.rename_image(item.model.id, filename)
            item.model.payload["caption"] = description
            item.update()
            self.controller.mark_dirty()
            self.controller.log_event(
                "Edytowano nazwę lub opis zdjęcia", "element",
                item_ids=[item.model.id],
            )
            return actual_name

        def save_image_properties():
            item.update()
            self.controller.mark_dirty()
            self.controller.log_event(
                "Zmieniono właściwości OSINT zdjęcia", "element",
                item_ids=[item.model.id],
            )

        dialog = ImagePreviewDialog(
            item.pixmap,
            item.model.payload.get("filename", "Obraz"),
            item.model.payload.get("caption", ""),
            self,
            model=item.model,
            save_image=save_image_changes if editable else None,
            save_properties=save_image_properties if editable else None,
        )
        if tab == "properties":
            dialog.tabs.setCurrentIndex(dialog.properties_tab_index)
            if start_edit and editable:
                dialog.begin_property_edit()
        else:
            dialog.tabs.setCurrentIndex(dialog.image_tab_index)
            if start_edit and editable:
                dialog.begin_image_edit()
        dialog.exec()

    def show_image_in_explorer(self, item: ImageItem):
        if not self.controller:
            return
        case_root = self.controller.paths.root.resolve()
        relative = Path(item.model.payload.get("path", ""))
        file_path = (case_root / relative).resolve()
        try:
            file_path.relative_to(case_root)
        except ValueError:
            QMessageBox.warning(
                self, "Pokaż w eksploratorze",
                "Ścieżka obrazu znajduje się poza katalogiem sprawy.",
            )
            return
        if not file_path.is_file():
            QMessageBox.warning(
                self, "Pokaż w eksploratorze",
                "Plik obrazu nie istnieje w katalogu sprawy.",
            )
            return
        self._reveal_local_file(file_path)

    @staticmethod
    def _reveal_local_file(file_path: Path):
        if sys.platform == "win32":
            QProcess.startDetached(
                "explorer.exe", ["/select,", str(file_path)]
            )
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent)))

    def save(self):
        if self.controller:
            self._save_camera()
            self.controller.save()

    def _save_camera(self):
        if self.controller and self.view:
            center = self.viewport_center()
            self.controller.metadata.camera_x = center.x()
            self.controller.metadata.camera_y = center.y()
            self.controller.metadata.zoom = self.view.transform().m11()

    def _restore_camera(self):
        zoom = max(.08, min(8, self.controller.metadata.zoom))
        self.view.resetTransform()
        self.view.scale(zoom, zoom)
        self.view.centerOn(self.controller.metadata.camera_x, self.controller.metadata.camera_y)

    def export_png(self):
        if not self.require_case():
            return
        rect = self.controller.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        if rect.isEmpty():
            QMessageBox.information(self, "Eksport", "Tablica jest pusta.")
            return
        scale = 1.0
        if rect.width() > 16000 or rect.height() > 16000:
            if QMessageBox.warning(
                self, "Bardzo duży obraz",
                f"Tablica ma {int(rect.width())} × {int(rect.height())} px. Zmniejszyć do bezpiecznego rozmiaru?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            ) != QMessageBox.StandardButton.Yes:
                return
            scale = min(16000 / rect.width(), 16000 / rect.height())
        filename, _ = QFileDialog.getSaveFileName(self, "Eksport PNG", "", "PNG (*.png)")
        if not filename:
            return
        if not filename.lower().endswith(".png"):
            filename += ".png"
        image = QImage(max(1, int(rect.width() * scale)), max(1, int(rect.height() * scale)),
                       QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#0f172a"))
        painter = QPainter(image)
        self.controller.scene.render(painter, QRectF(image.rect()), rect)
        painter.end()
        if not image.save(filename):
            QMessageBox.critical(self, "Eksport", "Nie udało się zapisać pliku PNG.")
        else:
            self.statusBar().showMessage(f"{tr('Wyeksportowano:')} {filename}", 5000)

    def closeEvent(self, event):
        controller = self.controller
        if controller:
            self._save_camera()
            controller.save()
            try:
                CaseManager.backup(controller.paths)
            except OSError:
                pass
            controller.close()
            # A widget can receive another close event during Qt/pytest teardown.
            # Never try to save again through an already closed SQLite connection.
            self.controller = None
        event.accept()

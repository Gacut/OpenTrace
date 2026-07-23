import gc

from PySide6.QtCore import QPointF, Qt

from app.controller import CaseController
from app.services import CaseManager
from app.ui import MainWindow
from app.ui.dialogs import ConnectionDialog, NoteColorDialog
from app.ui.image_preview import ImagePreviewDialog


def test_controller_can_be_attached_after_menus_survive_collection(qtbot, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    gc.collect()
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Nowa sprawa")
    window._set_controller(CaseController(paths, database, metadata))
    assert window.centralWidget() is window.view
    assert window.undo_action in window.edit_menu.actions()
    assert window.redo_action in window.edit_menu.actions()
    window.close()


def test_welcome_screen_buttons_use_new_and_open_case_actions(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    window = MainWindow()
    qtbot.addWidget(window)
    calls = []
    monkeypatch.setattr(window, "new_case", lambda: calls.append("new"))
    monkeypatch.setattr(window, "open_case", lambda: calls.append("open"))
    monkeypatch.setattr(window, "unpack_case", lambda: calls.append("unpack"))
    assert window.controller is None
    assert window.centralWidget().animation_timer.isActive()
    welcome = window.centralWidget()
    assert len(welcome._particles) == 63
    assert 0 <= welcome.accent_index < 63
    welcome.resize(1000, 700)
    points = welcome._mesh_points()
    assert min(point.x() for point in points) < 0
    assert max(point.x() for point in points) > welcome.width()
    assert min(point.y() for point in points) < 0
    assert max(point.y() for point in points) > welcome.height()
    phase = window.centralWidget().animation_phase
    qtbot.waitUntil(lambda: window.centralWidget().animation_phase > phase, timeout=500)
    assert window.main_toolbar.isHidden()
    assert not window.main_toolbar.toggleViewAction().isChecked()
    for button in (
        window.tools_toggle_button,
        window.fit_toggle_button,
        window.search_toggle_button,
        window.analysis_toggle_button,
        window.note_toggle_button,
    ):
        assert not button.isEnabled()
        assert button.graphicsEffect().opacity() == 0.4
    assert window.welcome_new_button.text() == "Nowa Sprawa"
    assert window.welcome_open_button.text() == "Otwórz sprawę"
    assert window.welcome_unpack_button.text() == "Rozpakuj sprawę z pliku ZIP"
    window.welcome_new_button.click()
    window.welcome_open_button.click()
    window.welcome_unpack_button.click()
    assert calls == ["new", "open", "unpack"]
    window.close()


def test_live_search_lists_multiple_occurrences_and_stays_open_on_navigation(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Wyszukiwanie")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(-500, -100), "Pierwsza", "wspólna fraza w materiale")
    controller.add_note(QPointF(650, 300), "Druga", "inna wspólna fraza")
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.show()
    window.search()
    dialog = window.search_dialog
    assert dialog.width() >= 760
    dialog.query.setText("wspólna fraza")
    qtbot.wait(300)
    assert dialog.results.count() == 2
    second_result = dialog.results.item(1)
    dialog.results.itemClicked.emit(second_result)
    qtbot.wait(10)
    kind, target_id = second_result.data(Qt.ItemDataRole.UserRole)
    target = controller.scene.nodes[target_id]
    assert kind == "node"
    assert target.isSelected()
    assert dialog.isVisible()
    view_center = window.view.mapToScene(window.view.viewport().rect().center())
    assert (view_center - target.center()).manhattanLength() < 3
    window.close()


def test_image_can_be_renamed_inside_case(qtbot, tmp_path):
    source = tmp_path / "original.png"
    source.write_bytes(b"test image payload")
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    controller.add_image(QPointF(0, 0), source)
    image_id = next(iter(controller.scene.nodes))
    new_name = controller.rename_image(image_id, "dowod.png")
    model = controller.scene.nodes[image_id].model
    assert new_name == "dowod.png"
    assert model.payload["filename"] == "dowod.png"
    assert (paths.root / model.payload["path"]).exists()
    controller.close()


def test_resize_is_undoable(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(10, 20))
    item = next(iter(controller.scene.nodes.values()))
    old_geometry = (10.0, 20.0, 220.0, 150.0)
    new_geometry = (30.0, 40.0, 340.0, 260.0)
    item.apply_geometry(*new_geometry)
    controller._record_resize(item.model.id, old_geometry, new_geometry)
    controller.undo_stack.undo()
    assert (item.pos().x(), item.pos().y(), item.model.width, item.model.height) == old_geometry
    controller.undo_stack.redo()
    assert (item.pos().x(), item.pos().y(), item.model.width, item.model.height) == new_geometry
    controller.close()


def test_note_opens_and_is_edited_in_right_panel(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "Tytuł", "Pierwszy wiersz\nDrugi wiersz")
    item_id = next(iter(controller.scene.nodes))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.edit_item(item_id)
    assert window.note_dock.isVisible() or not window.isVisible()
    assert window.note_panel.text.isReadOnly()
    assert window.note_panel.text.toPlainText() == "Pierwszy wiersz\nDrugi wiersz"
    window.note_panel.begin_edit()
    assert not window.note_panel.text.isReadOnly()
    window.note_panel.text.setPlainText("Zmieniona treść\nz formatowaniem wierszy")
    window.note_panel.save()
    assert controller.scene.nodes[item_id].model.payload["text"] == "Zmieniona treść\nz formatowaniem wierszy"
    assert window.note_panel.text.isReadOnly()
    window.edit_item(item_id, start_edit=True)
    assert not window.note_panel.text.isReadOnly()
    window.note_panel.cancel()
    window.close()


def test_links_are_highlighted_as_copyable_text_in_note_panel(qtbot, tmp_path):
    from PySide6.QtGui import QTextCursor

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    url = "https://example.org/material"
    controller.add_note(QPointF(0, 0), "Źródło", f"Sprawdź {url} później")
    item_id = next(iter(controller.scene.nodes))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.edit_item(item_id)
    cursor = QTextCursor(window.note_panel.text.document())
    start = window.note_panel.text.toPlainText().index(url)
    cursor.setPosition(start)
    cursor.setPosition(start + len(url), QTextCursor.MoveMode.KeepAnchor)
    assert cursor.charFormat().fontUnderline()
    assert cursor.charFormat().isAnchor()
    assert cursor.charFormat().anchorHref() == url
    assert window.note_panel.text.openExternalLinks()
    assert window.note_panel.text.isReadOnly()
    assert not window.note_panel.text.acceptRichText()
    window.close()


def test_note_osint_properties_open_read_only_tab_then_edit_inline(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "Notatka", "Treść")
    node = next(iter(controller.scene.nodes.values()))
    node.model.status = "Do sprawdzenia"
    node.model.tags = ["ważne"]
    node.model.payload["source"] = "Źródło A"
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.edit_properties(node)
    panel = window.note_panel
    assert panel.tabs.currentIndex() == panel.properties_tab_index
    assert panel.property_summary.isVisible() or not window.isVisible()
    assert "Status: Do sprawdzenia" in panel.property_summary.toPlainText()
    assert "Źródło: Źródło A" in panel.property_summary.toPlainText()
    assert not panel.property_form.isVisible()
    panel.begin_property_edit()
    assert panel.property_form.isVisible() or not window.isVisible()
    panel.property_status.setCurrentText("Potwierdzone")
    panel.property_tags.setText("ważne, źródło")
    panel.property_classification.setCurrentText("Fakt bezpośrednio wynikający ze źródła")
    panel.save_properties()
    assert node.model.status == "Potwierdzone"
    assert node.model.tags == ["ważne", "źródło"]
    assert "Status: Potwierdzone" in panel.property_summary.toPlainText()
    assert not panel.property_form.isVisible()
    window.close()


def test_image_preview_shows_copyable_metadata_and_supports_zoom(qtbot):
    from PySide6.QtGui import QColor, QPixmap

    pixmap = QPixmap(320, 200)
    pixmap.fill(QColor("#336699"))
    dialog = ImagePreviewDialog(
        pixmap, "dowod.png", "Opis materiału\nz zachowaniem wierszy"
    )
    qtbot.addWidget(dialog)
    assert dialog.filename.isReadOnly()
    assert dialog.filename.text() == "dowod.png"
    assert dialog.description.isReadOnly()
    assert dialog.description.toPlainText() == "Opis materiału\nz zachowaniem wierszy"
    initial_scale = dialog.image_view.transform().m11()
    dialog.image_view.zoom_by(1.2)
    assert dialog.image_view.transform().m11() > initial_scale


def test_image_preview_edits_file_description_and_osint_properties(qtbot):
    from PySide6.QtGui import QColor, QPixmap
    from app.models import BoardItemModel, ItemType

    pixmap = QPixmap(120, 80)
    pixmap.fill(QColor("#123456"))
    model = BoardItemModel(
        ItemType.IMAGE, 0, 0,
        payload={"filename": "stare.png", "caption": "Stary opis"},
    )
    saved_image = []
    saved_properties = []

    def save_image(name, description):
        saved_image.append((name, description))
        model.payload["filename"] = name
        model.payload["caption"] = description
        return name

    dialog = ImagePreviewDialog(
        pixmap, "stare.png", "Stary opis", model=model,
        save_image=save_image,
        save_properties=lambda: saved_properties.append(True),
    )
    qtbot.addWidget(dialog)
    assert dialog.tabs.currentIndex() == dialog.image_tab_index
    assert dialog.filename.isReadOnly()
    dialog.begin_image_edit()
    dialog.filename.setText("nowe.png")
    dialog.description.setPlainText("Nowy opis")
    dialog.save_image()
    assert saved_image == [("nowe.png", "Nowy opis")]
    assert dialog.filename.isReadOnly()

    assert "Status: Nowe" in dialog.property_summary.toPlainText()
    dialog.begin_property_edit()
    dialog.property_status.setCurrentText("Potwierdzone")
    dialog.property_tags.setText("dowód, obraz")
    dialog.property_source.setText("Archiwum lokalne")
    dialog.save_osint_properties()
    assert saved_properties == [True]
    assert model.status == "Potwierdzone"
    assert model.tags == ["dowód", "obraz"]
    assert model.payload["source"] == "Archiwum lokalne"
    assert "Status: Potwierdzone" in dialog.property_summary.toPlainText()


def test_image_context_actions_route_to_preview_edit_tabs(qtbot, tmp_path, monkeypatch):
    source = tmp_path / "obraz.png"
    source.write_bytes(b"image payload")
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Zdjęcia")
    controller = CaseController(paths, database, metadata)
    controller.add_image(QPointF(0, 0), source)
    image = next(iter(controller.scene.nodes.values()))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    calls = []
    monkeypatch.setattr(
        window, "preview_image",
        lambda item_id, tab="image", start_edit=False:
            calls.append((item_id, tab, start_edit)),
    )
    window.edit_item(image.model.id, start_edit=True)
    window.edit_properties(image)
    assert calls == [
        (image.model.id, "image", True),
        (image.model.id, "properties", False),
    ]
    window.close()


def test_image_can_be_revealed_in_case_explorer(qtbot, tmp_path, monkeypatch):
    source = tmp_path / "material.png"
    source.write_bytes(b"image payload")
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Zdjęcia")
    controller = CaseController(paths, database, metadata)
    controller.add_image(QPointF(0, 0), source)
    image = next(iter(controller.scene.nodes.values()))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    revealed = []
    monkeypatch.setattr(window, "_reveal_local_file", lambda path: revealed.append(path))
    window.show_image_in_explorer(image)
    assert len(revealed) == 1
    assert revealed[0].is_file()
    assert revealed[0].is_relative_to(paths.root.resolve())
    window.close()


def test_connection_dialog_uses_polish_forward_and_backward_arrow_directions(qtbot):
    from app.models import ConnectionModel

    model = ConnectionModel("source", "target", direction="forward")
    dialog = ConnectionDialog(model)
    qtbot.addWidget(dialog)
    assert [dialog.direction.itemText(index) for index in range(dialog.direction.count())] == [
        "Przód", "Tył"
    ]
    assert dialog.direction.currentData() == "forward"
    dialog.direction.setCurrentIndex(1)
    dialog.apply(model)
    assert model.direction == "backward"


def test_connection_label_is_clickable_and_selects_whole_line(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Relacje")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(-250, -60), "A")
    controller.add_pin(QPointF(250, -20), "B")
    nodes = list(controller.scene.nodes.values())
    nodes[0].setSelected(True)
    nodes[1].setSelected(True)
    controller.connect_selected()
    edge = next(iter(controller.scene.edges.values()))
    for selected in controller.scene.selectedItems():
        selected.setSelected(False)

    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.show()
    qtbot.wait(20)
    label_center = edge.label_rect().center()
    assert edge.shape().contains(label_center)
    viewport_position = window.view.mapFromScene(label_center)
    qtbot.mouseClick(window.view.viewport(), Qt.MouseButton.LeftButton, pos=viewport_position)
    assert edge.isSelected()
    # The same hit test is used by MainWindow.show_context_menu for PPM.
    assert controller.scene.itemAt(label_center, window.view.transform()) is edge
    window.close()


def test_note_has_independent_background_title_and_body_colors(qtbot):
    from PySide6.QtGui import QColor
    from app.models import BoardItemModel, ItemType

    model = BoardItemModel(
        ItemType.NOTE, 0, 0,
        payload={"color": "#facc15", "text_color": "#171717"},
    )
    dialog = NoteColorDialog(model)
    qtbot.addWidget(dialog)
    dialog.colors["background"] = QColor("#112233")
    dialog.colors["title"] = QColor("#445566")
    dialog.colors["body"] = QColor("#778899")
    dialog.apply(model)
    assert model.payload["color"] == "#112233"
    assert model.payload["title_color"] == "#445566"
    assert model.payload["body_color"] == "#778899"


def test_double_clicking_task_navigates_without_opening_editor(qtbot, tmp_path, monkeypatch):
    from app.models import AnalysisRecord

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(650, 420), "Materiał", "Treść")
    item_id = next(iter(controller.scene.nodes))
    controller.save_record(AnalysisRecord(
        kind="task", title="Sprawdź materiał", status="Do zrobienia",
        item_ids=[item_id],
    ))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.analysis_panel.tabs["task"].refresh()
    task_tab = window.analysis_panel.tabs["task"]
    task_tab.list.setCurrentRow(0)
    editor_called = False

    def mark_editor(*_):
        nonlocal editor_called
        editor_called = True

    monkeypatch.setattr(task_tab, "edit_selected", mark_editor)
    task_tab.list.itemDoubleClicked.emit(task_tab.list.currentItem())
    assert not editor_called
    node = controller.scene.nodes[item_id]
    assert node.isSelected()
    view_center = window.view.mapToScene(window.view.viewport().rect().center())
    assert (view_center - node.center()).manhattanLength() < 3
    window.close()


def test_double_clicking_journal_entry_navigates_without_editing(qtbot, tmp_path, monkeypatch):
    from app.models import AnalysisRecord

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    controller.add_pin(QPointF(-500, 275), "Materiał dziennika")
    item_id = next(iter(controller.scene.nodes))
    controller.save_record(AnalysisRecord(
        kind="journal", title="Sprawdzono materiał", status="decyzja",
        item_ids=[item_id], data={"body": "Wynik ręcznej weryfikacji"},
    ))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    journal_tab = window.analysis_panel.tabs["journal"]
    journal_tab.refresh()
    target_row = next(
        row for row in range(journal_tab.list.count())
        if journal_tab.list.item(row).data(Qt.ItemDataRole.UserRole + 2).startswith("Sprawdzono materiał")
    )
    journal_tab.list.setCurrentRow(target_row)
    timestamp = journal_tab.list.item(target_row).data(Qt.ItemDataRole.UserRole + 1)
    assert len(timestamp) == 20
    assert timestamp[2] == "." and timestamp[5] == "."
    assert timestamp[10:12] == ", "
    journal_widget = journal_tab.list.itemWidget(journal_tab.list.item(target_row))
    from PySide6.QtWidgets import QLabel
    labels = journal_widget.findChildren(QLabel)
    assert journal_tab.list.item(target_row).text() == ""
    assert sum("Sprawdzono materiał" in label.text() for label in labels) == 1
    assert labels[-1].text() == timestamp
    assert "font-size: 8pt" in labels[-1].styleSheet()
    editor_called = False

    def mark_editor(*_):
        nonlocal editor_called
        editor_called = True

    monkeypatch.setattr(journal_tab, "edit_selected", mark_editor)
    journal_tab.list.itemDoubleClicked.emit(journal_tab.list.currentItem())
    node = controller.scene.nodes[item_id]
    assert not editor_called
    assert node.isSelected()
    view_center = window.view.mapToScene(window.view.viewport().rect().center())
    assert (view_center - node.center()).manhattanLength() < 3
    window.close()


def test_left_gear_button_toggles_global_tools_panel(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    window = MainWindow()
    qtbot.addWidget(window)
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    window._set_controller(CaseController(paths, database, metadata))
    window.show()
    qtbot.wait(10)
    assert not window.tools_dock.isVisible()
    assert window.tools_toggle_button.isVisible()
    assert window.tools_toggle_button.x() == 6
    assert not hasattr(window, "tools_toggle_toolbar")
    window.tools_toggle_action.trigger()
    assert window.tools_dock.isVisible()
    assert window.tools_toggle_action.text() == "⚙"
    qtbot.wait(100)
    assert window.tools_toggle_button.x() > window.tools_dock.geometry().right()
    window.tools_toggle_action.trigger()
    assert not window.tools_dock.isVisible()
    assert window.tools_toggle_action.text() == "⚙"
    assert window.tools_toggle_button.x() == 6
    window.close()


def test_right_edge_buttons_toggle_analysis_and_note_panels(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    window = MainWindow()
    qtbot.addWidget(window)
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    window._set_controller(CaseController(paths, database, metadata))
    window.show()
    qtbot.wait(10)
    assert not window.analysis_dock.isVisible()
    assert not window.note_dock.isVisible()
    from PySide6.QtWidgets import QTabWidget
    assert window.tabPosition(Qt.DockWidgetArea.RightDockWidgetArea) == QTabWidget.TabPosition.North
    assert window.analysis_toggle_button.y() < window.note_toggle_button.y()
    assert window.search_toggle_button.y() < window.analysis_toggle_button.y()
    assert window.fit_toggle_button.y() > window.note_toggle_button.y()
    from PySide6.QtWidgets import QStyle
    right_x = (
        window.width() - window.analysis_toggle_button.width()
        - window.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) - 12
    )
    assert window.analysis_toggle_button.x() == right_x
    assert window.search_toggle_button.x() == right_x
    assert window.fit_toggle_button.x() == right_x
    window.analysis_toggle_action.trigger()
    qtbot.wait(100)
    assert window.analysis_dock.isVisible()
    assert window.analysis_toggle_action.text() == "📊"
    assert window.analysis_toggle_button.x() < window.analysis_dock.geometry().left()
    assert window.tools_toggle_button.isVisible()
    assert window.tools_toggle_button.x() == 6
    window.note_toggle_action.trigger()
    qtbot.wait(100)
    assert window.note_dock.isVisible()
    assert window.note_toggle_action.text() == "📝"
    assert window.note_toggle_button.x() < window.note_dock.geometry().left()
    assert window.analysis_toggle_button.x() == window.note_toggle_button.x()
    assert window.search_toggle_button.x() == window.note_toggle_button.x()
    assert window.fit_toggle_button.x() == window.note_toggle_button.x()
    open_right_inset = (
        window.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) + 12
    )
    assert (
        window.note_toggle_button.x()
        == window.note_dock.geometry().left() - window.note_toggle_button.width()
        - open_right_inset
    )
    assert window.tools_toggle_button.isVisible()
    window.note_toggle_action.trigger()
    qtbot.wait(100)
    assert not window.note_dock.isVisible()
    assert window.note_toggle_action.text() == "📝"
    if window.analysis_dock.isVisible():
        assert window.note_toggle_button.x() < window.analysis_dock.geometry().left()
        assert window.analysis_toggle_button.x() == window.note_toggle_button.x()
    else:
        assert window.note_toggle_button.x() == right_x
    window.close()


def test_top_right_search_button_opens_search(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    window = MainWindow()
    qtbot.addWidget(window)
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    window._set_controller(CaseController(paths, database, metadata))
    calls = []
    monkeypatch.setattr(window, "search", lambda: calls.append("search"))
    assert window.search_toggle_action.text() == "🔍"
    assert window.search_toggle_button.size() == window.analysis_toggle_button.size()
    window.search_toggle_action.trigger()
    assert calls == ["search"]
    window.close()


def test_bottom_right_fit_button_triggers_existing_fit_action(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    window = MainWindow()
    qtbot.addWidget(window)
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    window._set_controller(CaseController(paths, database, metadata))
    calls = []
    window.fit_action.triggered.connect(lambda: calls.append("fit"))
    assert window.fit_toggle_action.text() == "⛶"
    assert window.fit_toggle_button.size() == window.analysis_toggle_button.size()
    from PySide6.QtWidgets import QStyle
    expected_y = (
        window.height() - window.fit_toggle_button.height()
        - window.statusBar().height()
        - window.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) - 12
    )
    assert window.fit_toggle_button.y() == expected_y
    window.fit_toggle_action.trigger()
    assert calls == ["fit"]
    window.close()


def test_two_selected_nodes_enable_context_connection_action(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Relacje")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "A")
    controller.add_pin(QPointF(300, 0), "B")
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    for node in controller.scene.nodes.values():
        node.setSelected(True)
    assert window._selection_can_be_connected()
    controller.connect_selected()
    assert len(controller.scene.edges) == 1
    window.close()


def test_opening_case_keeps_floating_panel_buttons_above_new_board(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(10)
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Otwarta sprawa")
    window._set_controller(CaseController(paths, database, metadata))
    qtbot.wait(100)
    for button in (
        window.tools_toggle_button,
        window.fit_toggle_button,
        window.search_toggle_button,
        window.analysis_toggle_button,
        window.note_toggle_button,
    ):
        assert button.isEnabled()
        assert button.graphicsEffect().opacity() == 1.0
        assert button.isVisible()
        assert window.childAt(button.geometry().center()) is button
    window.close()


def test_connection_can_branch_from_another_connection_and_survive_reload(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Relacje")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "A")
    controller.add_pin(QPointF(400, 0), "B")
    controller.add_pin(QPointF(210, 300), "C")
    nodes = list(controller.scene.nodes.values())
    nodes[0].setSelected(True)
    nodes[1].setSelected(True)
    controller.connect_selected()
    parent = next(iter(controller.scene.edges.values()))
    old_label_center = parent.label_rect().center()
    nodes[1].setPos(520, 40)
    new_label_center = parent.label_rect().center()
    assert new_label_center != old_label_center
    assert parent.boundingRect().contains(parent.label_rect())
    assert parent.boundingRect().right() >= parent.label_rect().right() + 3
    for node in nodes:
        node.setSelected(False)
    parent.setSelected(True)
    nodes[2].setSelected(True)
    controller.connect_selected()
    branches = [edge for edge in controller.scene.edges.values() if edge.model.branch_from_id]
    assert len(branches) == 1
    branch = branches[0]
    assert branch.model.branch_from_id == parent.model.id
    assert (branch.path().pointAtPercent(0) - parent.center()).manhattanLength() < 1
    controller.undo_stack.undo()
    assert branch.model.id not in controller.scene.edges
    controller.undo_stack.redo()
    assert branch.model.id in controller.scene.edges
    for selected in controller.scene.selectedItems():
        selected.setSelected(False)
    parent.setSelected(True)
    controller.delete_selected()
    assert not controller.scene.edges
    controller.undo_stack.undo()
    assert len(controller.scene.edges) == 2
    controller.save()
    controller.close()

    paths, database, metadata = CaseManager.open(tmp_path / "case")
    reopened = CaseController(paths, database, metadata)
    loaded_branches = [
        edge for edge in reopened.scene.edges.values() if edge.model.branch_from_id
    ]
    assert len(reopened.scene.edges) == 2
    assert len(loaded_branches) == 1
    loaded_parent = reopened.scene.edges[loaded_branches[0].model.branch_from_id]
    assert (
        loaded_branches[0].path().pointAtPercent(0) - loaded_parent.center()
    ).manhattanLength() < 1
    reopened.close()


def test_about_action_opens_dialog_with_dependencies_and_github(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog, QLabel

    captured = {}

    def capture_dialog(dialog):
        captured["title"] = dialog.windowTitle()
        captured["text"] = " ".join(
            label.text() for label in dialog.findChildren(QLabel)
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", capture_dialog)
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "OpenTrace"
    assert window.about_action in window.menuBar().actions()
    window.about_action.trigger()

    assert captured["title"] == "O programie"
    assert "OpenTrace" in captured["text"]
    assert "PySide6" in captured["text"]
    assert "SQLite" in captured["text"]
    assert "zipfile" in captured["text"]
    assert "hashlib" in captured["text"]
    assert "json" in captured["text"]
    assert "pytest" in captured["text"]
    assert "PyInstaller" in captured["text"]
    assert "https://github.com/Gacut" in captured["text"]
    assert "Stworzone za pomocą Codex" in captured["text"]
    assert "https://openai.com/pl-PL/codex/" in captured["text"]
    assert "—" not in captured["text"]
    window.close()


def test_application_icon_is_available_and_valid():
    from PySide6.QtGui import QIcon

    from app.main import application_icon_path

    icon_path = application_icon_path()
    assert icon_path.is_file()
    assert not QIcon(str(icon_path)).isNull()


def test_view_menu_omits_actions_available_elsewhere(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    menu_labels = {action.text().replace("&", "") for action in window.view_menu.actions()}
    assert "Sprawdź projekt" not in menu_labels
    assert "Zapisz bieżący widok…" not in menu_labels
    assert "Otwórz zapisany widok…" not in menu_labels
    assert "Zasobnik narzędzi OSINT" not in menu_labels
    assert "Panel analizy" not in menu_labels
    assert "Panel notatki" not in menu_labels
    assert window.view_menu.actions()[-1].text() == "Wyłącz animację na ekranie głównym"
    window.close()


def test_edit_menu_has_room_for_action_names_and_shortcuts(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.edit_menu.minimumWidth() == 230
    window.close()


def test_welcome_animation_preference_persists(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    first_window = MainWindow()
    qtbot.addWidget(first_window)
    assert not first_window.disable_welcome_animation_action.isChecked()
    assert first_window.centralWidget().animation_timer.isActive()

    first_window.disable_welcome_animation_action.trigger()
    assert first_window.disable_welcome_animation_action.isChecked()
    assert not first_window.centralWidget().animation_timer.isActive()
    first_window.close()

    second_window = MainWindow()
    qtbot.addWidget(second_window)
    assert second_window.disable_welcome_animation_action.isChecked()
    assert not second_window.centralWidget().animation_timer.isActive()
    assert second_window.app_settings.animation_disabled
    second_window.close()


def test_file_menu_contains_case_zip_actions_in_order(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    labels = [action.text().replace("&", "") for action in window.file_menu.actions()]
    pack_index = labels.index("Spakuj sprawę do pliku ZIP…")
    unpack_index = labels.index("Rozpakuj sprawę z pliku ZIP…")
    export_index = labels.index("Eksport strukturalny JSON…")
    assert pack_index == export_index + 1
    assert unpack_index == pack_index + 1
    assert "Zakończ" not in labels
    assert "Zamknij sprawę" in labels
    window.close()


def test_close_case_saves_and_returns_to_welcome_screen(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Zamykana")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(10, 20), "Zapisana notatka")
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)

    window.close_case_action.trigger()

    assert window.controller is None
    assert window.view is None
    assert window.windowTitle() == "OpenTrace"
    assert window.centralWidget() is not None
    assert window.welcome_new_button.text() == "Nowa Sprawa"
    assert all(
        not button.isEnabled()
        for button in (
            window.tools_toggle_button,
            window.fit_toggle_button,
            window.search_toggle_button,
            window.analysis_toggle_button,
            window.note_toggle_button,
        )
    )

    reopened_paths, reopened_database, reopened_metadata = CaseManager.open(paths.root)
    reopened = CaseController(reopened_paths, reopened_database, reopened_metadata)
    assert any(item.model.payload.get("title") == "Zapisana notatka" for item in reopened.scene.nodes.values())
    reopened.close()
    window.close()


def test_double_clicking_verification_navigates_or_reports_missing_item(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from app.models import AnalysisRecord

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Sprawa")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(720, -310), "Materiał do weryfikacji", "Treść")
    item_id = next(iter(controller.scene.nodes))
    controller.save_record(AnalysisRecord(
        kind="verification", title="Powiązana weryfikacja", status="Nowe",
        item_ids=[item_id],
    ))
    controller.save_record(AnalysisRecord(
        kind="verification", title="Bez przypisania", status="Nowe", item_ids=[],
    ))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    verification_tab = window.analysis_panel.tabs["verification"]
    verification_tab.refresh()

    linked_row = next(
        row for row in range(verification_tab.list.count())
        if verification_tab.list.item(row).text().startswith("Powiązana weryfikacja")
    )
    verification_tab.list.setCurrentRow(linked_row)
    verification_tab.list.itemDoubleClicked.emit(verification_tab.list.currentItem())
    assert controller.scene.nodes[item_id].isSelected()

    messages = []
    monkeypatch.setattr(
        QMessageBox, "information",
        lambda _parent, title, message: messages.append((title, message)),
    )
    missing_row = next(
        row for row in range(verification_tab.list.count())
        if verification_tab.list.item(row).text().startswith("Bez przypisania")
    )
    verification_tab.list.setCurrentRow(missing_row)
    verification_tab.list.itemDoubleClicked.emit(verification_tab.list.currentItem())
    assert messages == [("Do weryfikacji", "Nie przypisano do żadnego elementu")]
    window.close()


def test_double_clicking_connection_journal_entry_centers_on_edge(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Relacje")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(-420, -180), "A")
    controller.add_pin(QPointF(610, 330), "B")
    nodes = list(controller.scene.nodes.values())
    for node in nodes:
        node.setSelected(True)
    controller.connect_selected()
    edge = next(iter(controller.scene.edges.values()))
    journal_record = next(
        record for record in controller.repository.load_records("journal")
        if record.title == "Utworzono połączenie"
    )
    assert journal_record.data["connection_id"] == edge.model.id

    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    journal_tab = window.analysis_panel.tabs["journal"]
    journal_tab.refresh()
    row = next(
        index for index in range(journal_tab.list.count())
        if journal_tab.list.item(index).data(Qt.ItemDataRole.UserRole + 2).startswith("Utworzono połączenie")
    )
    journal_tab.list.setCurrentRow(row)
    journal_tab.list.itemDoubleClicked.emit(journal_tab.list.currentItem())

    assert edge.isSelected()
    assert not any(node.isSelected() for node in nodes)
    view_center = window.view.mapToScene(window.view.viewport().rect().center())
    assert (view_center - edge.center()).manhattanLength() < 3
    window.close()


def test_deleting_item_and_connected_edge_creates_journal_entries(tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "Usuwanie")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "Notatka do usunięcia")
    controller.add_pin(QPointF(350, 0), "Drugi element")
    nodes = list(controller.scene.nodes.values())
    for node in nodes:
        node.setSelected(True)
    controller.connect_selected()
    edge = next(iter(controller.scene.edges.values()))
    for selected in controller.scene.selectedItems():
        selected.setSelected(False)
    nodes[0].setSelected(True)

    controller.delete_selected()

    deletion_entries = [
        record for record in controller.repository.load_records("journal")
        if record.status == "usunięcie"
    ]
    assert any(
        record.title == "Usunięto notatkę: Notatka do usunięcia"
        and nodes[0].model.id in record.data["body"]
        for record in deletion_entries
    )
    assert any(
        record.title.startswith("Usunięto połączenie:")
        and edge.model.id in record.data["body"]
        and edge.model.source_id in record.data["body"]
        and edge.model.target_id in record.data["body"]
        for record in deletion_entries
    )
    controller.undo_stack.undo()
    restoration_entries = [
        record for record in controller.repository.load_records("journal")
        if record.status == "przywrócenie"
    ]
    assert any(
        record.title == "Przywrócono usunięty element (CTRL + Z): Notatka do usunięcia"
        and record.item_ids == [nodes[0].model.id]
        for record in restoration_entries
    )
    assert any(
        record.title.startswith("Przywrócono usunięte połączenie (CTRL + Z):")
        and record.data.get("connection_id") == edge.model.id
        for record in restoration_entries
    )
    assert nodes[0].model.id in controller.scene.nodes
    assert edge.model.id in controller.scene.edges
    controller.close()


def test_record_uuid_field_is_read_only_unlockable_and_selectable_from_board(
    qtbot, tmp_path, monkeypatch
):
    from app.models import AnalysisRecord
    from app.ui.analysis_panel import ItemSelectionDialog, RECORD_TYPES, RecordDialog

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Powiązania")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "Pierwsza notatka")
    controller.add_pin(QPointF(300, 0), "Drugi element")
    item_ids = list(controller.scene.nodes)

    for kind in RECORD_TYPES:
        record = AnalysisRecord(kind=kind, title="Test", item_ids=[item_ids[0]])
        dialog = RecordDialog(kind, [], record, controller=controller)
        qtbot.addWidget(dialog)
        assert dialog.items_edit.isReadOnly()
        assert dialog.items_edit.text() == item_ids[0]
        dialog.close()

    dialog = RecordDialog(
        "task", [], AnalysisRecord(kind="task", title="Test", item_ids=[item_ids[0]]),
        controller=controller,
    )
    qtbot.addWidget(dialog)
    dialog.unlock_items_button.click()
    assert not dialog.items_edit.isReadOnly()
    assert dialog.unlock_items_button.text() == "Zablokuj edycję"
    dialog.unlock_items_button.click()
    assert dialog.items_edit.isReadOnly()

    monkeypatch.setattr(ItemSelectionDialog, "exec", lambda _dialog: True)
    monkeypatch.setattr(ItemSelectionDialog, "selected_ids", lambda _dialog: [item_ids[1]])
    dialog.select_items_button.click()
    assert dialog.items_edit.text() == item_ids[1]
    controller.close()


def test_changing_relation_journal_uuid_replaces_original_navigation_target(qtbot, tmp_path):
    from app.models import AnalysisRecord
    from app.ui.analysis_panel import RecordDialog

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Zmiana UUID")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "A")
    controller.add_pin(QPointF(350, 0), "B")
    controller.add_pin(QPointF(700, 0), "Nowy cel")
    nodes = list(controller.scene.nodes.values())
    nodes[0].setSelected(True)
    nodes[1].setSelected(True)
    controller.connect_selected()
    edge = next(iter(controller.scene.edges.values()))
    original = next(
        record for record in controller.repository.load_records("journal")
        if record.title == "Utworzono połączenie"
    )
    assert original.data["connection_id"] == edge.model.id

    dialog = RecordDialog("journal", [], original, controller=controller)
    qtbot.addWidget(dialog)
    dialog.items_edit.setText(nodes[2].model.id)
    changed = dialog.build_record()
    assert changed.item_ids == [nodes[2].model.id]
    assert "connection_id" not in changed.data
    controller.save_record(changed)
    uuid_change = next(
        record for record in controller.repository.load_records("journal")
        if record.title == "Zmieniono UUID: Utworzono połączenie"
    )
    assert uuid_change.status == "modyfikacja"
    assert f"Poprzednie UUID: {', '.join(original.item_ids)}" in uuid_change.data["body"]
    assert f"Nowe UUID: {nodes[2].model.id}" in uuid_change.data["body"]
    assert uuid_change.item_ids == [nodes[2].model.id]

    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    journal_tab = window.analysis_panel.tabs["journal"]
    journal_tab.refresh()
    target_row = next(
        row for row in range(journal_tab.list.count())
        if journal_tab.list.item(row).data(Qt.ItemDataRole.UserRole) == original.id
    )
    journal_tab.list.setCurrentRow(target_row)
    journal_tab.list.itemDoubleClicked.emit(journal_tab.list.currentItem())
    assert nodes[2].isSelected()
    assert not edge.isSelected()
    window.close()


def test_board_object_uuid_is_visible_copyable_and_read_only(qtbot, tmp_path):
    from PySide6.QtGui import QPixmap
    from app.models import BoardItemModel, ConnectionModel, ItemType
    from app.ui.dialogs import ConnectionDialog, PropertiesDialog

    paths, database, metadata = CaseManager.create(tmp_path / "case", "UUID")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "Notatka")
    note = next(iter(controller.scene.nodes.values()))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.note_panel.show_note(note.model.id, tab="properties")
    assert window.note_panel.property_uuid.text() == note.model.id
    assert window.note_panel.property_uuid.isReadOnly()

    pin_model = BoardItemModel(ItemType.PIN, 0, 0, payload={"name": "Pinezka"})
    properties = PropertiesDialog(pin_model)
    qtbot.addWidget(properties)
    assert properties.uuid.text() == pin_model.id
    assert properties.uuid.isReadOnly()

    image_model = BoardItemModel(ItemType.IMAGE, 0, 0, payload={"filename": "obraz.png"})
    image_preview = ImagePreviewDialog(
        QPixmap(20, 20), "obraz.png", "", model=image_model
    )
    qtbot.addWidget(image_preview)
    assert image_preview.property_uuid.text() == image_model.id
    assert image_preview.property_uuid.isReadOnly()

    connection_model = ConnectionModel(pin_model.id, image_model.id)
    connection_dialog = ConnectionDialog(connection_model)
    qtbot.addWidget(connection_dialog)
    assert connection_dialog.uuid.text() == connection_model.id
    assert connection_dialog.uuid.isReadOnly()
    window.close()


def test_searching_uuid_returns_board_item_and_linked_journal_entry(qtbot, tmp_path):
    paths, database, metadata = CaseManager.create(tmp_path / "case", "UUID search")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(480, 260), "Wyszukiwany materiał")
    item_id = next(iter(controller.scene.nodes))
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.search()
    window._perform_live_search(item_id)

    results = [
        (
            window.search_dialog.results.item(row).data(Qt.ItemDataRole.UserRole),
            window.search_dialog.results.item(row).text(),
        )
        for row in range(window.search_dialog.results.count())
    ]
    assert any(target == ("node", item_id) and "Wyszukiwany materiał" in label
               for target, label in results)
    assert any("Utworzono notatkę" in label for _target, label in results)
    window.close()


def test_same_case_can_be_closed_and_opened_again_with_journal_widgets(
    qtbot, tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QFileDialog

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Ponowne otwarcie")
    controller = CaseController(paths, database, metadata)
    for index in range(8):
        controller.add_note(QPointF(index * 30, index * 20), f"Notatka {index}")
    window = MainWindow()
    qtbot.addWidget(window)
    window._set_controller(controller)
    window.analysis_panel.refresh()
    assert window.analysis_panel.tabs["journal"].list.count() >= 8

    window.close_case()
    qtbot.wait(20)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(paths.root)
    )
    window.open_case()
    qtbot.wait(20)

    assert window.controller is not None
    assert window.controller.paths.root == paths.root
    assert window.analysis_panel.tabs["journal"].list.count() >= 8
    window.close()


def test_language_choice_persists_and_applies_after_restart(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from app.i18n import set_language
    from app.models import BoardItemModel, ItemType
    from app.ui.dialogs import PropertiesDialog

    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    messages = []
    monkeypatch.setattr(
        QMessageBox, "information",
        lambda _parent, title, message: messages.append((title, message)),
    )
    first_window = MainWindow()
    qtbot.addWidget(first_window)
    english_action = next(
        action for action in first_window.language_group.actions() if action.data() == "en"
    )
    english_action.trigger()
    assert first_window.app_settings.language == "en"
    assert first_window.welcome_language_combo.currentData() == "en"
    assert messages == [(
        "Language change",
        "The language change will be applied after restarting OpenTrace.",
    )]
    first_window.close()

    second_window = MainWindow()
    qtbot.addWidget(second_window)
    second_window.show()
    qtbot.wait(20)
    assert second_window.menuBar().actions()[0].text() == "File"
    assert second_window.welcome_new_button.text() == "New Case"
    assert second_window.language_menu.title() == "Language"
    assert second_window.statusBar().currentMessage() == "Data remains local on this computer."

    paths, database, metadata = CaseManager.create(tmp_path / "status-case", "Status")
    status_controller = CaseController(paths, database, metadata)
    second_window._set_controller(status_controller)
    status_controller.saved.emit()
    assert second_window.statusBar().currentMessage() == "Saved"

    model = BoardItemModel(ItemType.PIN, 0, 0, status="Potwierdzone")
    properties = PropertiesDialog(model)
    qtbot.addWidget(properties)
    properties.show()
    qtbot.wait(10)
    assert properties.status.currentText() == "Confirmed"
    properties.apply(model)
    assert model.status == "Potwierdzone"
    second_window.close()
    set_language("pl")


def test_home_language_selector_uses_target_language_for_restart_message(
    qtbot, tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    messages = []
    monkeypatch.setattr(
        QMessageBox, "information",
        lambda _parent, title, message: messages.append((title, message)),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.welcome_language_label.text() == "Język:"
    assert window.welcome_language_combo.currentData() == "pl"

    window.welcome_language_combo.setCurrentIndex(
        window.welcome_language_combo.findData("en")
    )
    assert messages[-1] == (
        "Language change",
        "The language change will be applied after restarting OpenTrace.",
    )
    window.welcome_language_combo.setCurrentIndex(
        window.welcome_language_combo.findData("pl")
    )
    assert messages[-1] == (
        "Zmiana języka",
        "Zmiana języka zostanie zastosowana po ponownym uruchomieniu OpenTrace.",
    )
    window.close()


def test_search_dialog_missing_english_strings_are_translated(qtbot):
    from PySide6.QtWidgets import QApplication, QLabel
    from app.i18n import install_translation_filter, set_language
    from app.ui.search_dialog import SearchDialog

    set_language("en")
    install_translation_filter(QApplication.instance())
    dialog = SearchDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(10)
    labels = [label.text() for label in dialog.findChildren(QLabel)]
    assert dialog.windowTitle() == "Search case"
    assert "Search phrase:" in labels
    assert dialog.summary.text() == "Enter at least 2 characters."
    dialog.query.setText("x")
    assert dialog.summary.text() == "Enter at least 2 characters."
    dialog.set_results([])
    assert dialog.summary.text() == "Found 0 results. Click a result to navigate to the item."
    dialog.close()
    set_language("pl")


def test_journal_titles_are_translated_only_for_display(qtbot, tmp_path):
    from app.i18n import set_language
    from app.ui.analysis_panel import AnalysisPanel

    paths, database, metadata = CaseManager.create(tmp_path / "case", "Journal translation")
    controller = CaseController(paths, database, metadata)
    controller.add_note(QPointF(0, 0), "User title")
    stored = next(
        record for record in controller.repository.load_records("journal")
        if record.title == "Utworzono notatkę"
    )
    set_language("en")
    panel = AnalysisPanel(lambda: controller)
    qtbot.addWidget(panel)
    panel.refresh()
    journal = panel.tabs["journal"]
    displayed = [
        journal.list.item(row).data(Qt.ItemDataRole.UserRole + 2)
        for row in range(journal.list.count())
    ]
    assert any(text.startswith("Created note  [item]") for text in displayed)
    reloaded = next(
        record for record in controller.repository.load_records("journal")
        if record.id == stored.id
    )
    assert reloaded.title == "Utworzono notatkę"
    controller.close()
    set_language("pl")


def test_node_context_menu_labels_have_english_translations():
    from app.i18n import set_language, tr

    set_language("en")
    assert tr("Dodaj do weryfikacji") == "Add for verification"
    assert tr("Duplikuj") == "Duplicate"
    assert tr("Zablokuj") == "Lock"
    assert tr("Odblokuj") == "Unlock"
    set_language("pl")


def test_image_read_only_property_summary_is_translated(qtbot):
    from PySide6.QtGui import QPixmap
    from app.i18n import set_language
    from app.models import BoardItemModel, ItemType

    model = BoardItemModel(
        ItemType.IMAGE, 0, 0, status="Nowe",
        payload={
            "filename": "image.png", "classification": "Nieokreślona",
            "visibility": "wewnętrzne", "layer": "Materiały źródłowe",
            "sha256": "abc123", "size_bytes": 103900,
        },
    )
    set_language("en")
    dialog = ImagePreviewDialog(QPixmap(20, 20), "image.png", "", model=model)
    qtbot.addWidget(dialog)
    summary = dialog.property_summary.toPlainText()
    assert "Status: New" in summary
    assert "Tags: —" in summary
    assert "Classification: Unspecified" in summary
    assert "Visibility: internal" in summary
    assert "Layer: Source materials" in summary
    assert "File size: 103900 B" in summary
    assert "SHA-256: abc123" in summary
    assert model.status == "Nowe"
    dialog.close()
    set_language("pl")


def test_about_dialog_has_complete_english_content(qtbot, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QDialog, QLabel
    from app.i18n import set_language

    monkeypatch.setenv("OSINT_BOARD_CONFIG_DIR", str(tmp_path / "config"))
    captured = {}

    def capture_dialog(dialog):
        captured["text"] = " ".join(
            label.text() for label in dialog.findChildren(QLabel)
        )
        return QDialog.DialogCode.Accepted

    set_language("en")
    monkeypatch.setattr(QDialog, "exec", capture_dialog)
    window = MainWindow()
    qtbot.addWidget(window)
    # MainWindow loads the persisted default, so emulate the next English launch.
    set_language("en")
    window.show_about_dialog()
    assert "Libraries and technologies" in captured["text"]
    assert "Python standard library" in captured["text"]
    assert "Development tools" in captured["text"]
    assert "automated testing" in captured["text"]
    assert "Author:" in captured["text"]
    assert "Created with Codex" in captured["text"]
    assert "Biblioteki i technologie" not in captured["text"]
    window.close()
    set_language("pl")

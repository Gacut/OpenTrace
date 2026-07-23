from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QUndoCommand

from app.models import BoardItemModel, ConnectionModel


class AddItemCommand(QUndoCommand):
    def __init__(self, controller, model: BoardItemModel):
        super().__init__("Dodaj element")
        self.controller, self.model = controller, model

    def redo(self):
        if self.model.id not in self.controller.scene.nodes:
            self.controller.scene.add_model(self.model)
        self.controller.mark_dirty()

    def undo(self):
        self.controller.scene.remove_model(self.model.id)
        self.controller.mark_dirty()


class AddConnectionCommand(QUndoCommand):
    def __init__(self, controller, model: ConnectionModel):
        super().__init__("Połącz elementy")
        self.controller, self.model = controller, model

    def redo(self):
        self.controller.scene.add_connection(self.model)
        self.controller.mark_dirty()

    def undo(self):
        self.controller.scene.remove_connection(self.model.id)
        self.controller.mark_dirty()


class MoveItemCommand(QUndoCommand):
    def __init__(self, controller, item_id: str, old: QPointF, new: QPointF):
        super().__init__("Przesuń element")
        self.controller, self.item_id = controller, item_id
        self.old, self.new = QPointF(old), QPointF(new)
        self._first = True

    def _set(self, pos: QPointF):
        item = self.controller.scene.nodes.get(self.item_id)
        if item:
            self.controller.scene.loading = True
            item.setPos(pos)
            self.controller.scene.loading = False
            self.controller.mark_dirty()

    def redo(self):
        if self._first:
            self._first = False
            return
        self._set(self.new)

    def undo(self):
        self._set(self.old)


class ResizeItemCommand(QUndoCommand):
    def __init__(self, controller, item_id: str, old_geometry: tuple, new_geometry: tuple):
        super().__init__("Zmień rozmiar elementu")
        self.controller, self.item_id = controller, item_id
        self.old_geometry, self.new_geometry = old_geometry, new_geometry
        self._first = True

    def _set(self, geometry: tuple):
        item = self.controller.scene.nodes.get(self.item_id)
        if not item:
            return
        x, y, width, height = geometry
        self.controller.scene.loading = True
        item.apply_geometry(x, y, width, height)
        self.controller.scene.loading = False
        self.controller.mark_dirty()

    def redo(self):
        if self._first:
            self._first = False
            return
        self._set(self.new_geometry)

    def undo(self):
        self._set(self.old_geometry)


class DeleteSelectionCommand(QUndoCommand):
    def __init__(self, controller, item_ids: list[str], edge_ids: list[str]):
        super().__init__("Usuń zaznaczenie")
        self.controller = controller
        scene = controller.scene
        self.items = [scene.nodes[item_id].model for item_id in item_ids if item_id in scene.nodes]
        connected = {}

        def collect(edge):
            if edge.model.id in connected:
                return
            connected[edge.model.id] = edge.model
            for branch in edge.branches:
                collect(branch)

        for item_id in item_ids:
            if item_id in scene.nodes:
                for edge in scene.nodes[item_id].connections:
                    collect(edge)
        for edge_id in edge_ids:
            if edge_id in scene.edges:
                collect(scene.edges[edge_id])
        self.edges = list(connected.values())

    def redo(self):
        for edge in self.edges:
            self.controller.scene.remove_connection(edge.id)
        for item in self.items:
            self.controller.scene.remove_model(item.id)
        self.controller.mark_dirty()
        self.controller.log_deleted_models(self.items, self.edges)

    def undo(self):
        for item in self.items:
            self.controller.scene.add_model(item)
        for edge in self.edges:
            self.controller.scene.add_connection(edge)
        self.controller.mark_dirty()
        self.controller.log_restored_models(self.items, self.edges)

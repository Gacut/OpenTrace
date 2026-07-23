from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from app.graphics.items import BaseNodeItem, ConnectionItem, make_item
from app.models import BoardItemModel, ConnectionModel


class BoardScene(QGraphicsScene):
    changed_by_user = Signal()
    move_finished = Signal(str, QPointF, QPointF)
    resize_finished = Signal(str, tuple, tuple)
    edit_requested = Signal(str)
    preview_requested = Signal(str)

    def __init__(self, case_root: Path):
        super().__init__(-50000, -50000, 100000, 100000)
        self.case_root = case_root
        self.nodes: dict[str, BaseNodeItem] = {}
        self.edges: dict[str, ConnectionItem] = {}
        self.loading = False
        self.grid_enabled = True
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, QColor("#0f172a"))
        if not self.grid_enabled:
            return
        step = 40
        left = int(rect.left()) - (int(rect.left()) % step)
        top = int(rect.top()) - (int(rect.top()) % step)
        painter.setPen(QPen(QColor("#1e293b"), 0))
        x = left
        while x < rect.right():
            painter.drawLine(x, rect.top(), x, rect.bottom())
            x += step
        y = top
        while y < rect.bottom():
            painter.drawLine(rect.left(), y, rect.right(), y)
            y += step

    def add_model(self, model: BoardItemModel) -> BaseNodeItem:
        item = make_item(model, self.case_root)
        self.nodes[model.id] = item
        self.addItem(item)
        return item

    def remove_model(self, item_id: str) -> BoardItemModel | None:
        item = self.nodes.pop(item_id, None)
        if not item:
            return None
        for edge in list(item.connections):
            self.remove_connection(edge.model.id)
        self.removeItem(item)
        return item.model

    def add_connection(self, model: ConnectionModel) -> ConnectionItem | None:
        if model.target_id not in self.nodes:
            return None
        if model.branch_from_id:
            source = self.edges.get(model.branch_from_id)
            if not source:
                return None
        else:
            source = self.nodes.get(model.source_id)
            if not source:
                return None
        edge = ConnectionItem(model, source, self.nodes[model.target_id])
        self.edges[model.id] = edge
        self.addItem(edge)
        return edge

    def remove_connection(self, edge_id: str) -> ConnectionModel | None:
        edge = self.edges.pop(edge_id, None)
        if not edge:
            return None
        for branch in list(edge.branches):
            self.remove_connection(branch.model.id)
        edge.detach()
        self.removeItem(edge)
        return edge.model

    def models(self) -> tuple[list[BoardItemModel], list[ConnectionModel]]:
        return ([node.model for node in self.nodes.values()],
                [edge.model for edge in self.edges.values()])


class BoardView(QGraphicsView):
    context_position = Signal(QPointF, QPoint)
    files_dropped = Signal(QPointF, list)

    def __init__(self, scene: BoardScene):
        super().__init__(scene)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._panning = False
        self._space = False
        self._last = QPoint()
        self.setAcceptDrops(True)

    def wheelEvent(self, event):
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        current = self.transform().m11()
        if .08 < current * factor < 8:
            self.scale(factor, factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space
        ):
            self._panning = True
            self._last = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position().toPoint() - self._last
            self._last = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor if self._space else Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.context_position.emit(self.mapToScene(event.pos()), event.globalPos())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if files:
            self.files_dropped.emit(self.mapToScene(event.position().toPoint()), files)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def fit_all(self) -> None:
        rect = self.scene().itemsBoundingRect().adjusted(-80, -80, 80, 80)
        if rect.isValid() and not rect.isEmpty():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

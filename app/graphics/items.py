from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsObject, QGraphicsPathItem, QStyleOptionGraphicsItem,
)

from app.models import BoardItemModel, ConnectionModel, ItemType

class BaseNodeItem(QGraphicsObject):
    HANDLE_SIZE = 10.0
    MIN_WIDTH = 80.0
    MIN_HEIGHT = 60.0

    def __init__(self, model: BoardItemModel):
        super().__init__()
        self.model = model
        self.connections: set[ConnectionItem] = set()
        self.setPos(model.x, model.y)
        self.setRotation(model.rotation)
        self.setZValue(model.z)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setToolTip("Dwuklik: edycja • Prawy przycisk: opcje")
        self._drag_start = QPointF()
        self._resize_handle: str | None = None
        self._resize_start_scene = QPointF()
        self._resize_start_geometry: tuple[float, float, float, float] | None = None
        self.setAcceptHoverEvents(True)
        self.sync_lock()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.model.width, self.model.height)

    def sync_lock(self) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not self.model.locked)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.model.locked:
            return self.pos()
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.model.x, self.model.y = self.pos().x(), self.pos().y()
            for connection in self.connections:
                connection.update_path()
            if self.scene() and not getattr(self.scene(), "loading", False):
                self.scene().changed_by_user.emit()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        handle = self.handle_at(event.pos())
        if handle and not self.model.locked:
            self._resize_handle = handle
            self._resize_start_scene = event.scenePos()
            self._resize_start_geometry = (
                self.pos().x(), self.pos().y(), self.model.width, self.model.height
            )
            event.accept()
            return
        self._drag_start = self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_handle and self._resize_start_geometry:
            x, y, width, height = self._resize_start_geometry
            delta = event.scenePos() - self._resize_start_scene
            handle = self._resize_handle
            new_x, new_y, new_width, new_height = x, y, width, height
            if "e" in handle:
                new_width = max(self.MIN_WIDTH, width + delta.x())
            if "s" in handle:
                new_height = max(self.MIN_HEIGHT, height + delta.y())
            if "w" in handle:
                new_width = max(self.MIN_WIDTH, width - delta.x())
                new_x = x + width - new_width
            if "n" in handle:
                new_height = max(self.MIN_HEIGHT, height - delta.y())
                new_y = y + height - new_height
            self.apply_geometry(new_x, new_y, new_width, new_height)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_handle and self._resize_start_geometry:
            old_geometry = self._resize_start_geometry
            new_geometry = (self.pos().x(), self.pos().y(), self.model.width, self.model.height)
            self._resize_handle = None
            self._resize_start_geometry = None
            if self.scene() and hasattr(self.scene(), "resize_finished"):
                self.scene().resize_finished.emit(self.model.id, old_geometry, new_geometry)
            event.accept()
            return
        old = self._drag_start
        new = self.pos()
        super().mouseReleaseEvent(event)
        if old != new and self.scene() and hasattr(self.scene(), "move_finished"):
            self.scene().move_finished.emit(self.model.id, old, new)

    def apply_geometry(self, x: float, y: float, width: float, height: float) -> None:
        self.prepareGeometryChange()
        self.model.width = max(self.MIN_WIDTH, width)
        self.model.height = max(self.MIN_HEIGHT, height)
        self.setPos(x, y)
        self.update()
        for connection in self.connections:
            connection.update_path()

    def resize_handles(self) -> dict[str, QRectF]:
        if self.model.type not in {ItemType.NOTE, ItemType.IMAGE}:
            return {}
        size = self.HANDLE_SIZE
        half = size / 2
        w, h = self.model.width, self.model.height
        points = {
            "nw": QPointF(half, half), "n": QPointF(w / 2, half),
            "ne": QPointF(w - half, half), "e": QPointF(w - half, h / 2),
            "se": QPointF(w - half, h - half), "s": QPointF(w / 2, h - half),
            "sw": QPointF(half, h - half), "w": QPointF(half, h / 2),
        }
        return {name: QRectF(point.x() - half, point.y() - half, size, size)
                for name, point in points.items()}

    def handle_at(self, position: QPointF) -> str | None:
        if not self.isSelected():
            return None
        for name, rect in self.resize_handles().items():
            if rect.adjusted(-3, -3, 3, 3).contains(position):
                return name
        return None

    def paint_resize_handles(self, painter: QPainter) -> None:
        if not self.isSelected() or self.model.locked:
            return
        painter.save()
        painter.setPen(QPen(QColor("#dbeafe"), 1))
        painter.setBrush(QColor("#2563eb"))
        for rect in self.resize_handles().values():
            painter.drawRect(rect)
        painter.restore()

    def hoverMoveEvent(self, event):
        handle = self.handle_at(event.pos())
        if handle in {"nw", "se"}:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in {"ne", "sw"}:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle in {"n", "s"}:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle in {"e", "w"}:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def center(self) -> QPointF:
        return self.mapToScene(self.boundingRect().center())


class NoteItem(BaseNodeItem):
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        bg = QColor(self.model.payload.get("color", "#facc15"))
        painter.setPen(QPen(QColor("#ffffff") if self.isSelected() else bg.darker(150), 3 if self.isSelected() else 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(self.boundingRect(), 8, 8)
        fallback_text_color = self.model.payload.get("text_color", "#171717")
        painter.setPen(QColor(self.model.payload.get("title_color", fallback_text_color)))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        painter.setFont(title_font)
        painter.drawText(QRectF(12, 9, self.model.width - 24, 28), Qt.TextFlag.TextWordWrap,
                         self.model.payload.get("title", "Notatka"))
        painter.setFont(title_font)
        text = self.model.payload.get("text", "")
        painter.setPen(QColor(self.model.payload.get("body_color", fallback_text_color)))
        painter.drawText(QRectF(12, 40, self.model.width - 24, self.model.height - 50),
                         Qt.TextFlag.TextWordWrap, text)
        self.paint_resize_handles(painter)

    def mouseDoubleClickEvent(self, event):
        if self.scene() and hasattr(self.scene(), "edit_requested"):
            self.scene().edit_requested.emit(self.model.id)
        super().mouseDoubleClickEvent(event)


class PinItem(BaseNodeItem):
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.model.width, self.model.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        color = QColor(self.model.payload.get("color", "#ef4444"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#fff") if self.isSelected() else color.darker(160), 3))
        painter.setBrush(color)
        center = QPointF(self.model.width / 2, min(38, self.model.height / 2))
        painter.drawEllipse(center, 25, 25)
        painter.drawLine(center.x(), center.y() + 25, center.x(), self.model.height - 22)
        painter.setPen(QColor("#f8fafc"))
        painter.setFont(QFont("", 18))
        painter.drawText(QRectF(center.x() - 20, center.y() - 19, 40, 38),
                         Qt.AlignmentFlag.AlignCenter, self.model.payload.get("icon", "●"))
        label_font = QFont()
        label_font.setBold(True)
        label_font.setPointSize(11)
        painter.setFont(label_font)
        painter.drawText(QRectF(3, self.model.height - 22, self.model.width - 6, 20),
                         Qt.AlignmentFlag.AlignCenter, self.model.payload.get("name", "Pinezka"))

    def mouseDoubleClickEvent(self, event):
        if self.scene() and hasattr(self.scene(), "edit_requested"):
            self.scene().edit_requested.emit(self.model.id)
        super().mouseDoubleClickEvent(event)


class ImageItem(BaseNodeItem):
    def __init__(self, model: BoardItemModel, case_root: Path):
        super().__init__(model)
        self.pixmap = QPixmap(str(case_root / model.payload.get("path", "")))

    def reload_pixmap(self) -> None:
        self.pixmap = QPixmap(str(self.scene().case_root / self.model.payload.get("path", "")))

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        painter.setPen(QPen(QColor("#fff") if self.isSelected() else QColor("#475569"), 3))
        painter.setBrush(QColor("#1e293b"))
        painter.drawRoundedRect(self.boundingRect(), 5, 5)
        image_rect = QRectF(6, 6, self.model.width - 12, self.model.height - 34)
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(image_rect.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            target = QRectF(0, 0, scaled.width(), scaled.height())
            target.moveCenter(image_rect.center())
            painter.drawPixmap(target.toRect(), scaled)
        painter.setPen(QColor("#e2e8f0"))
        painter.drawText(QRectF(6, self.model.height - 26, self.model.width - 12, 20),
                         Qt.AlignmentFlag.AlignCenter,
                         self.model.payload.get("caption") or self.model.payload.get("filename", "Obraz"))
        self.paint_resize_handles(painter)

    def mouseDoubleClickEvent(self, event):
        if self.scene() and hasattr(self.scene(), "preview_requested"):
            self.scene().preview_requested.emit(self.model.id)
        super().mouseDoubleClickEvent(event)


class ConnectionItem(QGraphicsPathItem):
    def __init__(
        self, model: ConnectionModel,
        source: BaseNodeItem | "ConnectionItem", target: BaseNodeItem,
    ):
        super().__init__()
        self.model, self.source, self.target = model, source, target
        self.branches: set[ConnectionItem] = set()
        if isinstance(source, BaseNodeItem):
            source.connections.add(self)
        else:
            source.branches.add(self)
        target.connections.add(self)
        self.setZValue(-1000)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_path()

    def update_path(self) -> None:
        old_scene_rect = (
            self.mapRectToScene(self.boundingRect()).adjusted(-8, -8, 8, 8)
            if self.scene() else QRectF()
        )
        start, end = self.source.center(), self.target.center()
        path = QPainterPath(start)
        dx = (end.x() - start.x()) * .5
        path.cubicTo(start + QPointF(dx, 0), end - QPointF(dx, 0), end)
        self.setPath(path)
        pen = QPen(QColor(self.model.color), self.model.width)
        if self.model.style == "dashed" or self.model.confidence == "przypuszczenie":
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setToolTip(f"{self.model.relation_type}: {self.model.label}")
        if self.scene():
            self.scene().update(old_scene_rect)
            self.scene().update(
                self.mapRectToScene(self.boundingRect()).adjusted(-8, -8, 8, 8)
            )
        for branch in self.branches:
            branch.update_path()

    def center(self) -> QPointF:
        return self.path().pointAtPercent(.5)

    def label_text(self) -> str:
        return self.model.label or self.model.relation_type

    def label_rect(self) -> QRectF:
        label = self.label_text()
        if not label or self.path().isEmpty():
            return QRectF()
        rect = QFontMetricsF(QFont()).boundingRect(label).adjusted(-5, -3, 5, 3)
        rect.moveCenter(self.path().pointAtPercent(.5))
        return rect

    def boundingRect(self) -> QRectF:
        # QGraphicsPathItem only accounts for the curve. The label and arrow
        # heads are painted outside it and must be included so Qt invalidates
        # their old pixels when connected nodes move.
        rect = super().boundingRect().adjusted(-14, -14, 14, 14)
        label = self.label_rect()
        # Rounded border and antialiased glyphs can extend beyond font metrics
        # by a fraction of a pixel. Keep a symmetric repaint safety margin.
        return rect.united(label.adjusted(-3, -3, 3, 3)) if not label.isEmpty() else rect

    def shape(self) -> QPainterPath:
        # The label is painted by this item but QGraphicsPathItem normally
        # exposes only the thin curve as its clickable shape. Include the
        # rounded label area so LPM selection and PPM context menus work on it.
        shape = super().shape()
        label = self.label_rect()
        if not label.isEmpty():
            shape.addRoundedRect(label.adjusted(-2, -2, 2, 2), 4, 4)
        return shape

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        path = self.path()
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.model.color))
        if self.model.direction == "backward":
            self._draw_arrow(painter, path.pointAtPercent(.31), path.pointAtPercent(.26))
            self._draw_arrow(painter, path.pointAtPercent(.74), path.pointAtPercent(.69))
        else:
            # Two small directional markers sit on the curve itself. This is
            # easier to read than a single endpoint arrow when nodes overlap.
            self._draw_arrow(painter, path.pointAtPercent(.26), path.pointAtPercent(.31))
            self._draw_arrow(painter, path.pointAtPercent(.69), path.pointAtPercent(.74))
        label = self.label_text()
        if label:
            painter.setFont(QFont())
            rect = self.label_rect()
            painter.setPen(QColor("#e2e8f0"))
            painter.setBrush(QColor("#0f172a"))
            painter.drawRoundedRect(rect, 4, 4)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

    @staticmethod
    def _draw_arrow(painter: QPainter, previous: QPointF, tip: QPointF):
        angle = math.atan2(tip.y() - previous.y(), tip.x() - previous.x())
        size = 8
        left = tip - QPointF(math.cos(angle - .55) * size, math.sin(angle - .55) * size)
        right = tip - QPointF(math.cos(angle + .55) * size, math.sin(angle + .55) * size)
        painter.drawPolygon(QPolygonF([tip, left, right]))

    def detach(self) -> None:
        if isinstance(self.source, BaseNodeItem):
            self.source.connections.discard(self)
        else:
            self.source.branches.discard(self)
        self.target.connections.discard(self)


def make_item(model: BoardItemModel, case_root: Path) -> BaseNodeItem:
    if model.type == ItemType.NOTE:
        return NoteItem(model)
    if model.type == ItemType.IMAGE:
        return ImageItem(model, case_root)
    return PinItem(model)

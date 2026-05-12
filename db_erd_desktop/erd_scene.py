from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsRectItem, QGraphicsScene, QGraphicsTextItem

from .models import DatabaseModel, TableModel


BOX_WIDTH = 330
HEADER_HEIGHT = 34
ROW_HEIGHT = 22
BOX_GAP_X = 90
BOX_GAP_Y = 80


@dataclass(frozen=True)
class BoxGeometry:
    table: TableModel
    rect: QRectF


class ErdSceneBuilder:
    def build(self, model: DatabaseModel, mode: str) -> QGraphicsScene:
        scene = QGraphicsScene()
        scene.setBackgroundBrush(QColor("#f8fafc"))
        boxes = self._layout(model.tables)

        for relationship in model.relationships:
            source = boxes.get(relationship.from_table)
            target = boxes.get(relationship.to_table)
            if source and target:
                self._add_relationship(scene, source.rect, target.rect, relationship.name)

        for geometry in boxes.values():
            self._add_table(scene, geometry, mode)

        scene.setSceneRect(scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))
        return scene

    def export_png(self, scene: QGraphicsScene, output_path: Path) -> None:
        rect = scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        image = QImage(math.ceil(rect.width()), math.ceil(rect.height()), QImage.Format_ARGB32)
        image.fill(QColor("#ffffff"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        scene.render(painter, QRectF(image.rect()), rect)
        painter.end()
        image.save(str(output_path))

    def _layout(self, tables: list[TableModel]) -> dict[str, BoxGeometry]:
        if not tables:
            return {}
        columns = max(1, math.ceil(math.sqrt(len(tables))))
        row_heights: list[float] = []
        heights = [HEADER_HEIGHT + ROW_HEIGHT * max(1, len(table.columns)) + 16 for table in tables]

        for row_index in range(math.ceil(len(tables) / columns)):
            start = row_index * columns
            end = min(start + columns, len(tables))
            row_heights.append(max(heights[start:end]))

        geometries: dict[str, BoxGeometry] = {}
        y = 0.0
        for row_index, row_height in enumerate(row_heights):
            x = 0.0
            for col_index in range(columns):
                table_index = row_index * columns + col_index
                if table_index >= len(tables):
                    break
                table = tables[table_index]
                height = heights[table_index]
                rect = QRectF(x, y, BOX_WIDTH, height)
                geometries[table.qualified_name] = BoxGeometry(table, rect)
                x += BOX_WIDTH + BOX_GAP_X
            y += row_height + BOX_GAP_Y
        return geometries

    def _add_table(self, scene: QGraphicsScene, geometry: BoxGeometry, mode: str) -> None:
        rect = geometry.rect
        table = geometry.table

        shadow = QGraphicsRectItem(rect.adjusted(3, 4, 3, 4))
        shadow.setBrush(QColor(15, 23, 42, 24))
        shadow.setPen(Qt.NoPen)
        scene.addItem(shadow)

        body = QGraphicsRectItem(rect)
        body.setBrush(QColor("#ffffff"))
        body.setPen(QPen(QColor("#cbd5e1"), 1.2))
        scene.addItem(body)

        header = QGraphicsRectItem(QRectF(rect.x(), rect.y(), rect.width(), HEADER_HEIGHT))
        header.setBrush(QColor("#1f2937") if mode == "physical" else QColor("#155e75"))
        header.setPen(Qt.NoPen)
        scene.addItem(header)

        title = table.name if mode == "physical" else table.logical_name or table.name
        subtitle = table.qualified_name if mode == "logical" else table.logical_name or ""
        title_item = self._text(title, 10, True, QColor("#ffffff"))
        title_item.setPos(rect.x() + 12, rect.y() + 7)
        title_item.setTextWidth(rect.width() - 24)
        scene.addItem(title_item)

        if subtitle and subtitle != title:
            subtitle_item = self._text(subtitle, 7, False, QColor("#64748b"))
            subtitle_item.setPos(rect.x() + 12, rect.y() + HEADER_HEIGHT + 5)
            subtitle_item.setTextWidth(rect.width() - 24)
            scene.addItem(subtitle_item)
            y = rect.y() + HEADER_HEIGHT + 25
        else:
            y = rect.y() + HEADER_HEIGHT + 8

        for column in table.columns:
            flags = []
            if column.is_primary_key:
                flags.append("PK")
            if column.foreign_key:
                flags.append("FK")
            flag_text = f"[{','.join(flags)}] " if flags else ""
            if mode == "physical":
                null_text = "NULL" if column.nullable else "NOT NULL"
                text_value = f"{flag_text}{column.name} : {column.data_type} {null_text}"
            else:
                text_value = f"{flag_text}{column.logical_name}"
            item = self._text(text_value, 8, column.is_primary_key, QColor("#0f172a"))
            item.setPos(rect.x() + 12, y)
            item.setTextWidth(rect.width() - 24)
            scene.addItem(item)
            y += ROW_HEIGHT

    def _add_relationship(self, scene: QGraphicsScene, source: QRectF, target: QRectF, name: str) -> None:
        start = source.center()
        end = target.center()
        if source.right() <= target.left():
            start.setX(source.right())
            end.setX(target.left())
        elif target.right() <= source.left():
            start.setX(source.left())
            end.setX(target.right())
        elif source.bottom() <= target.top():
            start.setY(source.bottom())
            end.setY(target.top())
        else:
            start.setY(source.top())
            end.setY(target.bottom())

        middle_x = (start.x() + end.x()) / 2
        path = QPainterPath(start)
        path.lineTo(middle_x, start.y())
        path.lineTo(middle_x, end.y())
        path.lineTo(end)

        item = QGraphicsPathItem(path)
        item.setPen(QPen(QColor("#64748b"), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        item.setZValue(-10)
        scene.addItem(item)

        label = self._text(name, 7, False, QColor("#475569"))
        label.setDefaultTextColor(QColor("#475569"))
        label.setPos(middle_x + 4, (start.y() + end.y()) / 2 - 10)
        label.setTextWidth(150)
        label.setZValue(-9)
        scene.addItem(label)

    def _text(self, value: str, point_size: int, bold: bool, color: QColor) -> QGraphicsTextItem:
        item = QGraphicsTextItem(value)
        font = QFont("Segoe UI", point_size)
        font.setBold(bold)
        item.setFont(font)
        item.setDefaultTextColor(color)
        return item

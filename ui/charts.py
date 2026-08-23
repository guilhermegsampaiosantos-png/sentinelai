"""
ui/charts.py
Pequenos widgets de gráfico desenhados via QPainter — sem dependências
externas (sem matplotlib/pyqtgraph). Usados no Dashboard.
"""
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

from ui import theme


class DonutRing(QWidget):
    """Anel de progresso circular com valor percentual no centro."""

    def __init__(self, color: str, thickness: int = 9, parent=None):
        super().__init__(parent)
        self._color = color
        self._thickness = thickness
        self._value = 0.0          # 0-100
        self._display = "—"
        self.setFixedSize(84, 84)

    def set_value(self, value: float, display: str | None = None):
        self._value = max(0.0, min(100.0, value))
        self._display = display if display is not None else f"{value:.0f}"
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        margin = self._thickness / 2 + 2
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        # trilho de fundo
        track_pen = QPen(QColor(theme.BORDER))
        track_pen.setWidthF(self._thickness)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(track_pen)
        p.drawArc(rect, 0, 360 * 16)

        # arco de valor
        if self._value > 0:
            value_pen = QPen(QColor(self._color))
            value_pen.setWidthF(self._thickness)
            value_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(value_pen)
            span = int(-(self._value / 100.0) * 360 * 16)
            p.drawArc(rect, 90 * 16, span)

        # texto central
        p.setPen(QColor(theme.TEXT_PRIMARY))
        font = QFont("Monospace", 13, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._display)
        p.end()


class BarChart(QWidget):
    """Gráfico de barras horizontais simples: [(label, value, color), ...]."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, int, str]] = []
        self._row_h = 30
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def set_data(self, items: list[tuple[str, int, str]]):
        self._items = items
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        h = max(1, len(self._items)) * self._row_h + 8
        return QSize(300, h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._items:
            p.setPen(QColor(theme.TEXT_MUTED))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sem dados")
            p.end()
            return

        max_val = max(v for _, v, _ in self._items) or 1
        label_w = 96
        value_w = 44
        chart_left = label_w
        chart_right = self.width() - value_w
        chart_w = max(10, chart_right - chart_left)

        font_label = QFont("Segoe UI", 10)
        font_value = QFont("Monospace", 11, QFont.Weight.Bold)

        for i, (label, value, color) in enumerate(self._items):
            y = i * self._row_h
            bar_h = self._row_h - 12
            bar_y = y + 6

            p.setFont(font_label)
            p.setPen(QColor(theme.TEXT_MUTED))
            label_rect = QRectF(0, y, label_w - 10, self._row_h)
            p.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, label)

            bar_w = chart_w * (value / max_val)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.BG_ELEVATED))
            p.drawRoundedRect(QRectF(chart_left, bar_y, chart_w, bar_h), 4, 4)
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(chart_left, bar_y, bar_w, bar_h), 4, 4)

            p.setFont(font_value)
            p.setPen(QColor(theme.TEXT_PRIMARY))
            value_rect = QRectF(chart_right + 8, y, value_w - 8, self._row_h)
            p.drawText(value_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, str(value))

        p.end()

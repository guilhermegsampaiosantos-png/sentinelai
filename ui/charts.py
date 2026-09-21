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
    """
    Anel de risco com TRÊS estados visualmente distintos — a distinção é o
    ponto principal deste widget, não a decoração:

      1. SEM COBERTURA  -> traço pontilhado apagado e "—" no centro.
         Aquele tipo de scan nunca rodou. Lê-se como ausência, não como
         aprovação.

      2. COBERTO, RISCO ZERO -> anel INTEIRO preenchido em verde e "0".
         Aqui está a sutileza: com a escala de risco invertida (0 = melhor),
         desenhar 0 como um anel vazio faria a melhor notícia possível ficar
         visualmente idêntica a "não tenho nada". Um anel completo lê-se
         como "verificado e fechado", que é exatamente o que aconteceu.

      3. COBERTO, COM RISCO -> arco proporcional ao risco, na cor da faixa.

    Antes, os estados 1 e 2 eram o mesmo desenho (anel vazio), e a ASPM
    acabava afirmando cobertura que não tinha.
    """

    def __init__(self, color: str, thickness: int = 9, parent=None):
        super().__init__(parent)
        self._color = color
        self._thickness = thickness
        self._value = 0.0          # 0-100 (risco)
        self._display = "—"
        self._covered = True
        self.setFixedSize(84, 84)

    def set_color(self, color: str):
        """Troca a cor do arco. Existe para o Dashboard não precisar mexer
        no atributo interno _color como fazia antes."""
        self._color = color
        self.update()

    def set_uncovered(self):
        """Estado 1: este tipo de scan não foi executado."""
        self._covered = False
        self._value = 0.0
        self._display = "—"
        self.setToolTip("Nenhuma ferramenta importada cobre este tipo de scan")
        self.update()

    def set_value(self, value: float, display: str | None = None,
                  color: str | None = None):
        """Estados 2 e 3: o tipo foi coberto; `value` é o risco (0 = melhor)."""
        self._covered = True
        if color is not None:
            self._color = color
        self._value = max(0.0, min(100.0, value))
        self._display = display if display is not None else f"{value:.0f}"
        self.setToolTip("Escaneado — risco 0" if self._value <= 0
                        else f"Escaneado — risco {self._value:.0f} de 100")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        margin = self._thickness / 2 + 2
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        if not self._covered:
            # ── Estado 1: sem cobertura ──────────────────────────────────
            pen = QPen(QColor(theme.BORDER_STRONG))
            pen.setWidthF(self._thickness * 0.5)
            pen.setStyle(Qt.PenStyle.DotLine)
            p.setPen(pen)
            p.drawArc(rect, 0, 360 * 16)

            p.setPen(QColor(theme.TEXT_MUTED))
            p.setFont(QFont("Monospace", 13, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._display)
            p.end()
            return

        # trilho de fundo (só nos estados cobertos)
        track_pen = QPen(QColor(theme.BORDER))
        track_pen.setWidthF(self._thickness)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(track_pen)
        p.drawArc(rect, 0, 360 * 16)

        value_pen = QPen(QColor(self._color))
        value_pen.setWidthF(self._thickness)
        value_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(value_pen)

        if self._value <= 0:
            # ── Estado 2: coberto e limpo -> anel completo ───────────────
            p.drawArc(rect, 0, 360 * 16)
        else:
            # ── Estado 3: arco proporcional ao risco ─────────────────────
            span = int(-(self._value / 100.0) * 360 * 16)
            p.drawArc(rect, 90 * 16, span)

        p.setPen(QColor(theme.TEXT_PRIMARY))
        p.setFont(QFont("Monospace", 13, QFont.Weight.Bold))
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

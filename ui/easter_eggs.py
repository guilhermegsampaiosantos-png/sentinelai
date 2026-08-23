"""
ui/easter_eggs.py
Easter eggs escondidos da SentinelAI. Dois personagens, desenhados em
QPainter (sem assets externos, mesmo espírito do ui/icons.py), cada um
revelado por um gatilho diferente:

  1. Bruxo  -> clique 7x rápido no logo (escudo) da toolbar
  2. Tux    -> atalho de teclado Ctrl+Alt+T

Uso (ver ui/main_window.py):
    from ui.easter_eggs import show_easter_egg
    show_easter_egg(self, "wizard")
"""
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QFont, QPen
from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel

from ui import theme


# ── Desenhos ────────────────────────────────────────────────────────────────

def _draw_wizard(p: QPainter, w: int, h: int):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx = w / 2

    # Chapéu pontudo
    hat = QPainterPath()
    hat.moveTo(cx, h * 0.06)
    hat.lineTo(cx - w * 0.20, h * 0.34)
    hat.lineTo(cx + w * 0.20, h * 0.34)
    hat.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#5b3fd4"))
    p.drawPath(hat)

    brim = QRectF(cx - w * 0.26, h * 0.32, w * 0.52, h * 0.05)
    p.setBrush(QColor("#4a30b8"))
    p.drawRoundedRect(brim, 4, 4)

    # Estrelinhas no chapéu
    p.setBrush(QColor("#ffd75e"))
    for dx, dy, r in [(-0.06, 0.16, 3.5), (0.08, 0.24, 2.5), (0.0, 0.10, 2)]:
        p.drawEllipse(QPointF(cx + w * dx, h * dy), r, r)

    # Rosto
    p.setBrush(QColor("#e8c19a"))
    p.drawEllipse(QRectF(cx - w * 0.12, h * 0.34, w * 0.24, h * 0.16))

    # Barba
    beard = QPainterPath()
    beard.moveTo(cx - w * 0.16, h * 0.42)
    beard.cubicTo(cx - w * 0.18, h * 0.62, cx - w * 0.05, h * 0.72, cx, h * 0.74)
    beard.cubicTo(cx + w * 0.05, h * 0.72, cx + w * 0.18, h * 0.62, cx + w * 0.16, h * 0.42)
    beard.cubicTo(cx + w * 0.10, h * 0.50, cx - w * 0.10, h * 0.50, cx - w * 0.16, h * 0.42)
    p.setBrush(QColor("#f2f2f2"))
    p.drawPath(beard)

    # Olhos
    p.setBrush(QColor("#161d30"))
    p.drawEllipse(QPointF(cx - w * 0.045, h * 0.40), 1.6, 1.6)
    p.drawEllipse(QPointF(cx + w * 0.045, h * 0.40), 1.6, 1.6)

    # Robe
    robe = QPainterPath()
    robe.moveTo(cx - w * 0.10, h * 0.50)
    robe.lineTo(cx - w * 0.30, h * 0.94)
    robe.lineTo(cx + w * 0.30, h * 0.94)
    robe.lineTo(cx + w * 0.10, h * 0.50)
    robe.closeSubpath()
    p.setBrush(QColor("#5b3fd4"))
    p.drawPath(robe)

    # Cinto e estrela do robe
    p.setBrush(QColor("#4a30b8"))
    p.drawRect(QRectF(cx - w * 0.18, h * 0.66, w * 0.36, h * 0.035))
    p.setBrush(QColor("#ffd75e"))
    p.drawEllipse(QPointF(cx, h * 0.82), 4, 4)

    # Cajado
    p.setPen(QColor("#8a5a2b"))
    pen = p.pen()
    pen.setWidthF(3.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(cx + w * 0.32, h * 0.40), QPointF(cx + w * 0.32, h * 0.92))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#6ea1ff"))
    p.drawEllipse(QPointF(cx + w * 0.32, h * 0.38), 5.5, 5.5)


def _draw_tux(p: QPainter, w: int, h: int):
    """Tux sentado, no estilo clássico do mascote do Linux (Larry Ewing)."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx = w / 2
    outline = QColor("#000000")
    pen = QPen(outline)
    pen.setWidthF(w * 0.02)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)

    # Silhueta preta (cabeça + corpo, formato de "sino" sentado)
    body = QPainterPath()
    body.moveTo(cx, h * 0.03)
    body.cubicTo(cx - w * 0.30, h * 0.05, cx - w * 0.34, h * 0.30, cx - w * 0.30, h * 0.46)
    body.cubicTo(cx - w * 0.44, h * 0.58, cx - w * 0.46, h * 0.78, cx - w * 0.40, h * 0.90)
    body.cubicTo(cx - w * 0.30, h * 0.98, cx + w * 0.30, h * 0.98, cx + w * 0.40, h * 0.90)
    body.cubicTo(cx + w * 0.46, h * 0.78, cx + w * 0.44, h * 0.58, cx + w * 0.30, h * 0.46)
    body.cubicTo(cx + w * 0.34, h * 0.30, cx + w * 0.30, h * 0.05, cx, h * 0.03)
    body.closeSubpath()
    p.setPen(pen)
    p.setBrush(QColor("#000000"))
    p.drawPath(body)

    # Barriga branca
    belly = QPainterPath()
    belly.moveTo(cx, h * 0.30)
    belly.cubicTo(cx - w * 0.16, h * 0.34, cx - w * 0.22, h * 0.62, cx - w * 0.20, h * 0.90)
    belly.cubicTo(cx - w * 0.10, h * 0.96, cx + w * 0.10, h * 0.96, cx + w * 0.20, h * 0.90)
    belly.cubicTo(cx + w * 0.22, h * 0.62, cx + w * 0.16, h * 0.34, cx, h * 0.30)
    belly.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawPath(belly)

    # Pés amarelo/laranja
    p.setPen(pen)
    p.setBrush(QColor("#f5a623"))
    foot_l = QPainterPath()
    foot_l.moveTo(cx - w * 0.28, h * 0.90)
    foot_l.cubicTo(cx - w * 0.40, h * 0.90, cx - w * 0.44, h * 1.00, cx - w * 0.34, h * 1.02)
    foot_l.cubicTo(cx - w * 0.22, h * 1.03, cx - w * 0.14, h * 0.98, cx - w * 0.16, h * 0.90)
    foot_l.closeSubpath()
    p.drawPath(foot_l)
    foot_r = QPainterPath()
    foot_r.moveTo(cx + w * 0.28, h * 0.90)
    foot_r.cubicTo(cx + w * 0.40, h * 0.90, cx + w * 0.44, h * 1.00, cx + w * 0.34, h * 1.02)
    foot_r.cubicTo(cx + w * 0.22, h * 1.03, cx + w * 0.14, h * 0.98, cx + w * 0.16, h * 0.90)
    foot_r.closeSubpath()
    p.drawPath(foot_r)

    # Olhos (brancos com pupila preta, olhando para o lado)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(cx - w * 0.09, h * 0.15), w * 0.075, w * 0.075)
    p.drawEllipse(QPointF(cx + w * 0.09, h * 0.15), w * 0.075, w * 0.075)
    p.setBrush(QColor("#000000"))
    p.drawEllipse(QPointF(cx - w * 0.06, h * 0.155), w * 0.032, w * 0.032)
    p.drawEllipse(QPointF(cx + w * 0.12, h * 0.155), w * 0.032, w * 0.032)

    # Bico laranja
    p.setPen(pen)
    p.setBrush(QColor("#f5a623"))
    beak = QPainterPath()
    beak.moveTo(cx - w * 0.08, h * 0.19)
    beak.cubicTo(cx - w * 0.09, h * 0.24, cx + w * 0.02, h * 0.27, cx + w * 0.09, h * 0.24)
    beak.cubicTo(cx + w * 0.05, h * 0.20, cx - w * 0.02, h * 0.19, cx - w * 0.08, h * 0.19)
    beak.closeSubpath()
    p.drawPath(beak)



_DRAWERS = {
    "wizard": _draw_wizard,
    "tux": _draw_tux,
}

_TITLES = {
    "wizard": "Um bruxo selvagem aparece!",
    "tux": "É o Tux, mascote do Linux!",
}

_MESSAGES = {
    "wizard": "Ele conjurou um relatório de vulnerabilidades do nada.\n"
              "(clicou no logo 7 vezes... achou mesmo?)",
    "tux": "Ctrl+Alt+T encontrado. Linux aprova essa build.",
}


class _CharacterWidget(QWidget):
    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self._drawer = _DRAWERS[kind]
        self.setFixedSize(140, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        self._drawer(p, self.width(), self.height())
        p.end()


class EasterEggDialog(QDialog):
    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("???")
        self.setFixedSize(280, 300)
        self.setStyleSheet(f"background:{theme.BG_ELEVATED};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        char = _CharacterWidget(kind)
        layout.addWidget(char, alignment=Qt.AlignmentFlag.AlignHCenter)

        title = QLabel(_TITLES[kind])
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{theme.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        msg = QLabel(_MESSAGES[kind])
        msg.setFont(QFont("Segoe UI", 9))
        msg.setStyleSheet(f"color:{theme.TEXT_MUTED};")
        msg.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)


def show_easter_egg(parent, kind: str):
    """Abre o diálogo do easter egg indicado ('wizard', 'tux' ou 'gnu')."""
    dialog = EasterEggDialog(kind, parent)
    dialog.exec()

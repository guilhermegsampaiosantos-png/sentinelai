"""
ui/icons.py
Conjunto de ícones vetoriais minimalistas (estilo outline), desenhados via
QPainter num grid 24x24 — substitui os emojis por algo consistente,
recolorível e sem depender de nenhum asset externo.

Uso:
    from ui.icons import icon
    btn.setIcon(icon("upload", "#4f8dff"))
"""
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath


def _new_painter(size: int, color: str, stroke: float):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    pen = QPen(QColor(color))
    pen.setWidthF(stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    return pm, p


def _dot(p: QPainter, center: QPointF, r: float, color: str):
    p.save()
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(center, r, r)
    p.restore()


# ── Desenhos ────────────────────────────────────────────────────────────────

def _draw_shield(p, color):
    path = QPainterPath()
    path.moveTo(12, 2)
    path.lineTo(20, 5)
    path.lineTo(20, 11)
    path.cubicTo(20, 17, 16.3, 20.4, 12, 22)
    path.cubicTo(7.7, 20.4, 4, 17, 4, 11)
    path.lineTo(4, 5)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(8.3, 12.2), QPointF(10.7, 14.8))
    p.drawLine(QPointF(10.7, 14.8), QPointF(16, 9))


def _draw_upload(p, color):
    p.drawLine(QPointF(12, 3), QPointF(12, 15))
    p.drawLine(QPointF(12, 3), QPointF(7.2, 8))
    p.drawLine(QPointF(12, 3), QPointF(16.8, 8))
    p.drawLine(QPointF(4, 17), QPointF(4, 20.5))
    p.drawLine(QPointF(4, 20.5), QPointF(20, 20.5))
    p.drawLine(QPointF(20, 20.5), QPointF(20, 17))


def _draw_trash(p, color):
    p.drawLine(QPointF(4, 6.5), QPointF(20, 6.5))
    p.drawLine(QPointF(9, 6.5), QPointF(9, 3.5))
    p.drawLine(QPointF(15, 6.5), QPointF(15, 3.5))
    p.drawLine(QPointF(9, 3.5), QPointF(15, 3.5))
    p.drawLine(QPointF(6.2, 6.5), QPointF(7.2, 21))
    p.drawLine(QPointF(17.8, 6.5), QPointF(16.8, 21))
    p.drawLine(QPointF(7.2, 21), QPointF(16.8, 21))
    p.drawLine(QPointF(10.3, 10), QPointF(10.3, 18))
    p.drawLine(QPointF(13.7, 10), QPointF(13.7, 18))


def _draw_dashboard(p, color):
    for x, y in [(3, 3), (13, 3), (3, 13), (13, 13)]:
        p.drawRoundedRect(QRectF(x, y, 8, 8), 1.6, 1.6)


def _draw_list(p, color):
    for y in [6.5, 12, 17.5]:
        _dot(p, QPointF(4, y), 1.1, color)
        p.drawLine(QPointF(8, y), QPointF(20.5, y))


def _draw_brain(p, color):
    p.drawRoundedRect(QRectF(7, 7, 10, 10), 2.2, 2.2)
    for x in [9.5, 12, 14.5]:
        p.drawLine(QPointF(x, 1.5), QPointF(x, 7))
        p.drawLine(QPointF(x, 17), QPointF(x, 22.5))
    for y in [9.5, 12, 14.5]:
        p.drawLine(QPointF(1.5, y), QPointF(7, y))
        p.drawLine(QPointF(17, y), QPointF(22.5, y))
    _dot(p, QPointF(12, 12), 1.3, color)


def _draw_chat(p, color):
    p.drawRoundedRect(QRectF(3, 4, 18, 13), 3.2, 3.2)
    tail = QPainterPath()
    tail.moveTo(8, 17)
    tail.lineTo(8, 21.3)
    tail.lineTo(12.3, 17)
    p.drawPath(tail)
    for x in [8.2, 12, 15.8]:
        _dot(p, QPointF(x, 10.5), 0.9, color)


def _draw_document(p, color):
    p.drawRoundedRect(QRectF(5, 2.5, 14, 19), 2, 2)
    p.drawLine(QPointF(8, 8), QPointF(16, 8))
    p.drawLine(QPointF(8, 12), QPointF(16, 12))
    p.drawLine(QPointF(8, 16), QPointF(13, 16))


def _draw_server(p, color):
    p.drawRoundedRect(QRectF(3, 4, 18, 7), 1.8, 1.8)
    p.drawRoundedRect(QRectF(3, 13, 18, 7), 1.8, 1.8)
    _dot(p, QPointF(6.5, 7.5), 0.9, color)
    _dot(p, QPointF(6.5, 16.5), 0.9, color)


def _draw_target(p, color):
    c = QPointF(12, 12)
    p.drawEllipse(c, 9, 9)
    p.drawEllipse(c, 5, 5)
    _dot(p, c, 1.6, color)


def _draw_search(p, color):
    p.drawEllipse(QPointF(10.2, 10.2), 6.2, 6.2)
    p.drawLine(QPointF(14.8, 14.8), QPointF(20.5, 20.5))


def _draw_flame(p, color):
    path = QPainterPath()
    path.moveTo(12, 2)
    path.cubicTo(6.5, 9, 8, 12.5, 8, 15.5)
    path.cubicTo(8, 19.5, 10.3, 22, 12.3, 22)
    path.cubicTo(14.3, 22, 16.5, 20, 16.3, 16.5)
    path.cubicTo(16.1, 14.5, 15, 13.5, 14.3, 12.5)
    path.cubicTo(14.5, 15, 12.7, 15.5, 12.7, 13)
    path.cubicTo(12.7, 10, 14.3, 8, 12, 2)
    path.closeSubpath()
    p.drawPath(path)


def _draw_alert(p, color):
    path = QPainterPath()
    path.moveTo(12, 2.5)
    path.lineTo(21.5, 20)
    path.lineTo(2.5, 20)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(12, 9), QPointF(12, 14.2))
    _dot(p, QPointF(12, 17), 0.9, color)


def _draw_check(p, color):
    p.drawEllipse(QRectF(3, 3, 18, 18))
    p.drawLine(QPointF(7.5, 12.3), QPointF(10.6, 15.5))
    p.drawLine(QPointF(10.6, 15.5), QPointF(17, 8.5))


def _draw_x(p, color):
    p.drawEllipse(QRectF(3, 3, 18, 18))
    p.drawLine(QPointF(9, 9), QPointF(15, 15))
    p.drawLine(QPointF(15, 9), QPointF(9, 15))


def _draw_plug(p, color):
    p.drawLine(QPointF(9, 2), QPointF(9, 6.5))
    p.drawLine(QPointF(15, 2), QPointF(15, 6.5))
    p.drawRoundedRect(QRectF(6, 6.5, 12, 8), 3, 3)
    p.drawLine(QPointF(12, 14.5), QPointF(12, 19.5))
    p.drawLine(QPointF(8, 19.5), QPointF(16, 19.5))


def _draw_clock(p, color):
    p.drawEllipse(QRectF(3, 3, 18, 18))
    p.drawLine(QPointF(12, 12), QPointF(12, 7))
    p.drawLine(QPointF(12, 12), QPointF(16, 14.5))


def _draw_plus(p, color):
    p.drawLine(QPointF(12, 4.5), QPointF(12, 19.5))
    p.drawLine(QPointF(4.5, 12), QPointF(19.5, 12))


def _draw_save(p, color):
    p.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)
    p.drawRect(QRectF(7.5, 4, 9, 6))
    p.drawRect(QRectF(7, 13, 10, 7))


_DRAWERS = {
    "shield": _draw_shield,
    "upload": _draw_upload,
    "trash": _draw_trash,
    "dashboard": _draw_dashboard,
    "list": _draw_list,
    "brain": _draw_brain,
    "chat": _draw_chat,
    "document": _draw_document,
    "server": _draw_server,
    "target": _draw_target,
    "search": _draw_search,
    "flame": _draw_flame,
    "alert": _draw_alert,
    "check": _draw_check,
    "x": _draw_x,
    "plug": _draw_plug,
    "clock": _draw_clock,
    "plus": _draw_plus,
    "save": _draw_save,
}

_cache: dict[tuple, QIcon] = {}


def icon(name: str, color: str, size: int = 18, stroke: float = 1.7) -> QIcon:
    """Retorna um QIcon vetorial. Resultado é cacheado por (nome, cor, tamanho)."""
    key = (name, color, size, stroke)
    if key in _cache:
        return _cache[key]
    drawer = _DRAWERS.get(name)
    if drawer is None:
        raise ValueError(f"Ícone desconhecido: {name}")
    pm, p = _new_painter(size, color, stroke)
    drawer(p, color)
    p.end()
    ic = QIcon(pm)
    _cache[key] = ic
    return ic


def pixmap(name: str, color: str, size: int = 18, stroke: float = 1.7) -> QPixmap:
    pm, p = _new_painter(size, color, stroke)
    _DRAWERS[name](p, color)
    p.end()
    return pm


def dot_pixmap(color: str, size: int = 10) -> QPixmap:
    """Bolinha colorida sólida — usada nos indicadores de severidade."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(0, 0, size, size)
    p.end()
    return pm

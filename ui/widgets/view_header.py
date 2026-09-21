"""
ui/widgets/view_header.py
Cabeçalho padrão de view (56px, título com ícone vetorial + subtítulo
opcional) — extraído de Ativos/Contexto para as views pararem de reinventar
o mesmo bloco cada uma do seu jeito (uma com emoji, outra sem cabeçalho
nenhum). Usado por AssetsView, ContextView, FindingsView e AIView.
"""
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtGui import QFont

from ui import theme
from ui.icons import icon


def build_header(icon_name: str, title_text: str, subtitle_text: str = "") -> QFrame:
    header = QFrame()
    header.setStyleSheet(f"background:{theme.BG_SURFACE}; border-bottom:1px solid {theme.BORDER};")
    header.setFixedHeight(56)
    hl = QHBoxLayout(header)
    hl.setContentsMargins(20, 0, 20, 0)
    hl.setSpacing(10)

    icon_lbl = QLabel()
    icon_lbl.setPixmap(icon(icon_name, theme.TEXT_PRIMARY, 18).pixmap(18, 18))
    icon_lbl.setStyleSheet("border:none;")
    hl.addWidget(icon_lbl)

    title = QLabel(title_text)
    title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    title.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; border:none;")
    hl.addWidget(title)

    if subtitle_text:
        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:11px; border:none;")
        hl.addWidget(subtitle)

    hl.addStretch()
    header.content_layout = hl  # o chamador pode addWidget() extra (botões, status) antes de retornar
    return header

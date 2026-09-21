"""
ui/views/attack_path_view.py
Attack Path — cruza findings importados com o contexto dos ativos para montar
cadeias de risco (exposição → vulnerabilidade → impacto).

Ganhou aba própria na sidebar em vez de ficar dentro de "Inteligência
Artificial" (P1 #7 da revisão de UX): o motor é determinístico, não usa IA
nenhuma, mas morava ao lado de uma barra de Groq API Key que não tinha
nenhuma relação com ele — o usuário via "configure sua chave de IA" numa
tela que não precisa de IA para funcionar.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox

from core.models import Vulnerability
from core.attack_path import detect as detect_attack_paths
from ui import theme
from ui.icons import icon
from ui.widgets.view_header import build_header
from ui.widgets.ai_results import ResultsPanel


class AttackPathView(QWidget):
    def __init__(self):
        super().__init__()
        self._vulns: list[Vulnerability] = []
        self._assets: dict = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(build_header(
            "flame", "Attack Path",
            "cruza findings com o contexto dos ativos — determinístico, não usa IA"))

        body = QVBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)

        btn = QPushButton(" Mapear caminhos de ataque")
        btn.setIcon(icon("flame", theme.ACCENT_ON, 15))
        btn.setFixedHeight(38)
        btn.setStyleSheet(theme.button_style(theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED))
        btn.clicked.connect(self._run)
        body.addWidget(btn)

        self.output = ResultsPanel()
        self.output.setPlainText(
            "Cruza os achados importados com o contexto dos ativos para montar cadeias de risco\n"
            "(exposição → vulnerabilidade → impacto).\n\n"
            "Não depende de IA — o cálculo é determinístico."
        )
        body.addWidget(self.output)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; font-family:monospace;")
        body.addWidget(self.status)

        wrap = QWidget()
        wrap.setLayout(body)
        root.addWidget(wrap)

    # ── Dados ─────────────────────────────────────────────────────────────
    def set_assets(self, assets: dict):
        """Recebe {asset_id: Asset} do MainWindow."""
        self._assets = assets or {}

    def update_data(self, vulns: list[Vulnerability]):
        self._vulns = vulns

    # ── Ação ──────────────────────────────────────────────────────────────
    def _run(self):
        if not self._vulns:
            QMessageBox.information(self, "Sem dados", "Importe relatórios primeiro.")
            return

        paths = detect_attack_paths(self._vulns, self._assets)
        self.output.render_attack_paths(paths)

        if paths:
            self.status.setText(f"{len(paths)} caminho(s) identificado(s)")
        elif not self._assets:
            self.status.setText(
                "Nenhum caminho — cadastre ativos e vincule findings a eles para mais regras")
        else:
            self.status.setText("Nenhum caminho identificado")

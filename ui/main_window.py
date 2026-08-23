"""
ui/main_window.py
Janela principal da SentinelAI — PyQt6.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QStatusBar, QTabWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QSize, QElapsedTimer
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

from core.aggregator import Aggregator
from core.scorer import calculate
from ui.views.dashboard_view import DashboardView
from ui.views.findings_view import FindingsView
from ui.views.ai_view import AIView
from ai.provider import LLMProvider
from ui import theme
from ui.icons import icon
from ui.easter_eggs import show_easter_egg


class ClickableLabel(QLabel):
    """QLabel que aceita clique — usada só para o logo (easter egg)."""
    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self._on_click()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.aggregator = Aggregator()
        self.provider = LLMProvider()          # detecta Ollama ou usa Groq

        # --- estado dos easter eggs -----------------------------------
        self._logo_click_count = 0
        self._logo_click_timer = QElapsedTimer()

        self._setup_ui()
        self._setup_easter_eggs()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        self.setWindowTitle("SentinelAI — Application Security Posture Management")
        self.setMinimumSize(1280, 800)
        self._apply_dark_theme()

        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Toolbar
        root_layout.addWidget(self._build_toolbar())

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setIconSize(QSize(16, 16))

        self.dashboard_view = DashboardView()
        self.findings_view  = FindingsView()
        self.ai_view        = AIView(self.provider)

        self.tabs.addTab(self.dashboard_view, icon("dashboard", theme.TEXT_MUTED), "Dashboard")
        self.tabs.addTab(self.findings_view,  icon("list", theme.TEXT_MUTED), "Findings")
        self.tabs.addTab(self.ai_view,        icon("brain", theme.TEXT_MUTED), "Inteligência Artificial")
        root_layout.addWidget(self.tabs)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Pronto. Importe um relatório para começar.")

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background:{theme.BG_SURFACE}; border-bottom:1px solid {theme.BORDER};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 16, 0)
        layout.setSpacing(10)

        logo = ClickableLabel(self._on_logo_clicked)
        logo.setPixmap(icon("shield", theme.ACCENT, 22).pixmap(22, 22))
        layout.addWidget(logo)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand_box.setContentsMargins(0, 0, 0, 0)

        name = QLabel("SentinelAI")
        name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{theme.TEXT_PRIMARY};")
        brand_box.addWidget(name)

        subtitle = QLabel("Application Security Posture Management")
        subtitle.setFont(QFont("Segoe UI", 8))
        subtitle.setStyleSheet(f"color:{theme.TEXT_MUTED}; letter-spacing:0.5px;")
        brand_box.addWidget(subtitle)

        layout.addLayout(brand_box)
        layout.addStretch()

        btn_import = QPushButton(" Importar Relatório")
        btn_import.setIcon(icon("upload", theme.ACCENT_ON, 15))
        btn_import.setFixedHeight(34)
        btn_import.setStyleSheet(theme.button_style(
            theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED))
        btn_import.clicked.connect(self._on_import)
        layout.addWidget(btn_import)

        btn_clear = QPushButton(" Limpar")
        btn_clear.setIcon(icon("trash", theme.TEXT_MUTED, 15))
        btn_clear.setFixedHeight(34)
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {theme.TEXT_MUTED};
                border: 1px solid {theme.BORDER}; border-radius: 6px;
                padding: 0 14px; font-size: 13px;
            }}
            QPushButton:hover {{ color: {theme.TEXT_PRIMARY}; border-color: {theme.BORDER_STRONG}; }}
        """)
        btn_clear.clicked.connect(self._on_clear)
        layout.addWidget(btn_clear)

        return bar

    # ------------------------------------------------------------------
    # Easter eggs 🥚 — 2 personagens escondidos:
    #   1) bruxo -> clicar 7x rápido no logo da toolbar
    #   2) tux   -> atalho Ctrl+Alt+T
    def _setup_easter_eggs(self):
        QShortcut(QKeySequence("Ctrl+Alt+T"), self,
                  activated=lambda: show_easter_egg(self, "tux"))

    def _on_logo_clicked(self):
        if not self._logo_click_timer.isValid() or self._logo_click_timer.elapsed() > 1200:
            self._logo_click_count = 0
        self._logo_click_timer.restart()
        self._logo_click_count += 1
        if self._logo_click_count >= 7:
            self._logo_click_count = 0
            show_easter_egg(self, "wizard")

    # ------------------------------------------------------------------
    def _on_import(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecione relatório(s)",
            "",
            "Relatórios (*.json *.xml);;Todos os arquivos (*)",
        )
        if not paths:
            return

        errors = []
        imported = 0
        for path in paths:
            try:
                report = self.aggregator.import_file(path)
                imported += 1
                self.status.showMessage(
                    f"Importado: {report.tool.upper()} — "
                    f"{len(report.vulnerabilities)} vulnerabilidades encontradas."
                )
            except ValueError as e:
                errors.append(str(e))

        if errors:
            QMessageBox.warning(self, "Formato não reconhecido", "\n\n".join(errors))

        if imported > 0:
            self._refresh_views()

    def _on_clear(self):
        self.aggregator.clear()
        self._refresh_views()
        self.status.showMessage("Dados limpos.")

    def _refresh_views(self):
        vulns = self.aggregator.all_vulnerabilities
        score = calculate(vulns)
        self.dashboard_view.update_data(score, vulns)
        self.findings_view.update_data(vulns)
        self.ai_view.update_data(vulns)

    # ------------------------------------------------------------------
    def _apply_dark_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {theme.BG_APP}; color: {theme.TEXT_PRIMARY}; }}
            QTabWidget::pane {{ border: none; background: {theme.BG_APP}; }}
            QTabBar::tab {{
                background: {theme.BG_SURFACE}; color: {theme.TEXT_MUTED};
                padding: 10px 20px; border: none;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{ color: {theme.TEXT_PRIMARY}; border-bottom: 2px solid {theme.ACCENT}; }}
            QTabBar::tab:hover {{ color: {theme.TEXT_PRIMARY}; background: {theme.BG_ELEVATED}; }}
            QStatusBar {{ background: {theme.BG_SURFACE}; color: {theme.TEXT_MUTED}; font-size: 11px; }}
        """)

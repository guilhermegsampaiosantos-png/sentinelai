"""
ui/main_window.py
Janela principal da SentinelAI — PyQt6.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QStatusBar, QStackedWidget,
    QMessageBox, QButtonGroup, QFrame,
)
from PyQt6.QtCore import Qt, QSize, QElapsedTimer, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

from core.aggregator import Aggregator
from core.scorer import calculate
from core.company_context import load as load_context
from core.coverage import covered_scan_types
from core import asset as asset_store
from core import settings as settings_store
from ui.views.dashboard_view import DashboardView
from ui.views.findings_view import FindingsView
from ui.views.ai_view import AIView
from ui.views.attack_path_view import AttackPathView
from ui.views.context_view import ContextView
from ui.views.assets_view import AssetsView
from ai.provider import LLMProvider
from ui import theme
from ui.icons import icon
from ui.easter_eggs import show_easter_egg
from scanners.trivy_scanner import TrivyScanner
from scanners.semgrep_scanner import SemgrepScanner
from scanners.gitleaks_scanner import GitleaksScanner


# Índices da navegação lateral. A ordem aqui é a mesma do QStackedWidget e
# a mesma dos NavButton criados em _build_sidebar() — as três precisam bater.
NAV_DASHBOARD    = 0
NAV_FINDINGS     = 1
NAV_AI           = 2
NAV_ATTACK_PATH  = 3
NAV_ASSETS       = 4
NAV_CONTEXT      = 5


class ScanWorker(QObject):
    """
    Roda os scanners internos (Trivy, Semgrep, Gitleaks) em thread separada
    para não travar a UI enquanto os processos externos executam — alguns
    (ex: Semgrep com --config auto) podem levar bastante tempo.

    Executa os 3 sequencialmente (não em paralelo) para manter o log de
    progresso simples e evitar concorrência de I/O nos relatórios temporários.
    Emite `finished` com a lista de ScannerResult ao final (sempre — mesmo
    quando algum scanner falha ou não está instalado, o erro vai dentro do
    próprio ScannerResult).
    """
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def __init__(self, target: str):
        super().__init__()
        self.target = target
        self._scanners = [TrivyScanner(), SemgrepScanner(), GitleaksScanner()]

    def run(self):
        results = []
        for scanner in self._scanners:
            self.progress.emit(f"Executando {scanner.name}...")
            if not scanner.is_installed():
                from scanners.base_scanner import ScannerResult
                results.append(ScannerResult(
                    tool=scanner.name, report_path="", success=False,
                    error=scanner.install_hint(),
                ))
                continue
            result = scanner.run(self.target)
            results.append(result)
        self.finished.emit(results)


class ClickableLabel(QLabel):
    """QLabel que aceita clique — usada só para o logo (easter egg)."""
    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self._on_click()
        super().mousePressEvent(event)


class NavButton(QPushButton):
    """
    Item de navegação da sidebar lateral (estilo Wiz): ícone + rótulo
    empilhados horizontalmente, checkable (fica "ativo" ao ser selecionado).
    Cada instância guarda o nome do ícone pra poder recolorir o ícone
    quando o estado ativo/hover muda (ícone monocromático desenhado via
    QPainter em ui/icons.py, então precisamos redesenhar com outra cor).
    """
    def __init__(self, icon_name: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self.setText(f"  {label}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self.setFixedHeight(42)
        self.setIcon(icon(icon_name, theme.TEXT_MUTED, 18))
        self._refresh_icon()
        self.toggled.connect(self._refresh_icon)

    def _refresh_icon(self):
        color = theme.ACCENT if self.isChecked() else theme.TEXT_MUTED
        self.setIcon(icon(self._icon_name, color, 18))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.aggregator = Aggregator()
        self.provider = LLMProvider()          # detecta Ollama ou usa Groq

        # Groq API Key persistida (ver ui/dialogs/settings_dialog.py — P2 #15):
        # sem isso, o usuário precisava redigitar a chave a cada abertura.
        saved_key = settings_store.load().groq_api_key
        if saved_key:
            self.provider.set_groq_key(saved_key)

        # --- estado dos easter eggs -----------------------------------
        self._logo_click_count = 0
        self._logo_click_timer = QElapsedTimer()

        # --- estado do scan interno -------------------------------------
        self._scan_thread = None
        self._scan_worker = None

        self._setup_ui()
        self._setup_easter_eggs()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        self.setWindowTitle("SentinelAI — Application Security Posture Management")
        self.setMinimumSize(1280, 800)
        self._apply_dark_theme()

        # Widget central: sidebar lateral (esquerda) + coluna de conteúdo (direita).
        # Antes disso era um QTabWidget com abas no topo; a navegação lateral
        # (estilo Wiz) separa melhor "onde eu navego" (sidebar) de "o que eu
        # faço agora" (barra de ações no topo do conteúdo).
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())

        content_col = QWidget()
        content_layout = QVBoxLayout(content_col)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self._build_topbar())

        # Views — agora empilhadas num QStackedWidget, trocadas pela sidebar
        self.stack = QStackedWidget()

        self.dashboard_view    = DashboardView()
        self.findings_view     = FindingsView()
        self.ai_view           = AIView(self.provider)
        self.attack_path_view  = AttackPathView()
        self.context_view      = ContextView()
        self.assets_view       = AssetsView()
        self.context_view.context_saved.connect(self._on_context_saved)
        self.findings_view.status_changed.connect(self._on_status_changed)
        self.findings_view.asset_assigned.connect(self._on_asset_assigned)
        self.assets_view.assets_changed.connect(self._on_assets_changed)

        # Checklist de primeiros passos (estado vazio do Dashboard) -> navegação
        self.dashboard_view.go_to_context.connect(lambda: self._go_to(NAV_CONTEXT))
        self.dashboard_view.go_to_assets.connect(lambda: self._go_to(NAV_ASSETS))
        self.dashboard_view.scan_requested.connect(self._on_scan_folder)
        self.dashboard_view.import_requested.connect(self._on_import)

        # Ordem tem que bater 1:1 com a ordem dos NavButton criados em _build_sidebar()
        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.findings_view)
        self.stack.addWidget(self.ai_view)
        self.stack.addWidget(self.attack_path_view)
        self.stack.addWidget(self.assets_view)
        self.stack.addWidget(self.context_view)

        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_col, 1)

        # Carrega os ativos já salvos (data/assets.json) e distribui para as
        # views que precisam deles — mesmo antes de qualquer import de relatório.
        self._push_assets(self.assets_view.get_assets())

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Pronto. Importe um relatório para começar.")

        # Primeira renderização: sem isso o Dashboard abriria com os widgets
        # no estado padrão do construtor, e o checklist de primeiros passos
        # não refletiria o contexto/ativos já salvos em disco.
        self._refresh_views()

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(224)
        sidebar.setStyleSheet(f"background:{theme.BG_SURFACE_ALT}; border-right:1px solid {theme.BORDER};")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(2)

        # Marca, no topo da sidebar (era na toolbar, agora mora aqui)
        brand = QWidget()
        brand.setFixedHeight(64)
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(18, 0, 12, 0)
        brand_layout.setSpacing(10)

        logo = ClickableLabel(self._on_logo_clicked)
        logo.setPixmap(icon("shield", theme.ACCENT, 22).pixmap(22, 22))
        brand_layout.addWidget(logo)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand_box.setContentsMargins(0, 0, 0, 0)

        name = QLabel("SentinelAI")
        name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{theme.TEXT_PRIMARY};")
        brand_box.addWidget(name)

        subtitle = QLabel("ASPM")
        subtitle.setFont(QFont("Segoe UI", 8))
        subtitle.setStyleSheet(f"color:{theme.TEXT_MUTED}; letter-spacing:0.5px;")
        brand_box.addWidget(subtitle)

        brand_layout.addLayout(brand_box)
        brand_layout.addStretch()
        layout.addWidget(brand)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"background:{theme.BORDER}; max-height:1px; border:none;")
        layout.addWidget(divider)
        layout.addSpacing(10)

        # Itens de navegação — ordem tem que bater 1:1 com o QStackedWidget
        nav_items = [
            ("dashboard", "Dashboard"),
            ("list",      "Findings"),
            ("brain",     "Inteligência Artificial"),
            ("flame",     "Attack Path"),
            ("server",    "Ativos"),
            ("shield",    "Contexto da Empresa"),
        ]

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []

        for idx, (icon_name, label) in enumerate(nav_items):
            btn = NavButton(icon_name, label)
            btn.setStyleSheet(self._nav_button_style())
            self.nav_group.addButton(btn, idx)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        self.nav_buttons[0].setChecked(True)
        self.nav_group.idClicked.connect(self._on_nav_selected)

        layout.addStretch()
        return sidebar

    @staticmethod
    def _nav_button_style() -> str:
        return f"""
            QPushButton {{
                background: transparent; color: {theme.TEXT_MUTED};
                border: none; border-left: 3px solid transparent;
                text-align: left; padding-left: 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {theme.BG_ELEVATED}; color: {theme.TEXT_PRIMARY}; }}
            QPushButton:checked {{
                background: {theme.BG_ELEVATED}; color: {theme.TEXT_PRIMARY};
                border-left: 3px solid {theme.ACCENT}; font-weight: bold;
            }}
        """

    def _on_nav_selected(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def _go_to(self, idx: int):
        """Navega por código (usado pelo checklist de primeiros passos do
        Dashboard) — troca a página E marca o item certo na sidebar, senão o
        destaque lateral fica apontando pra tela errada."""
        self.stack.setCurrentIndex(idx)
        if 0 <= idx < len(self.nav_buttons):
            self.nav_buttons[idx].setChecked(True)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background:{theme.BG_SURFACE}; border-bottom:1px solid {theme.BORDER};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(10)

        layout.addStretch()

        btn_scan = QPushButton(" Escanear Pasta")
        btn_scan.setIcon(icon("shield", theme.TEXT_PRIMARY, 15))
        btn_scan.setFixedHeight(34)
        btn_scan.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.ACCENT}; border-radius: 6px;
                padding: 0 14px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {theme.BG_ELEVATED}; }}
            QPushButton:disabled {{ color: {theme.TEXT_FAINT}; border-color: {theme.BORDER}; }}
        """)
        btn_scan.clicked.connect(self._on_scan_folder)
        self.btn_scan = btn_scan
        layout.addWidget(btn_scan)

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

    # ------------------------------------------------------------------
    # Scan interno: a ASPM dispara Trivy + Semgrep + Gitleaks diretamente
    # contra uma pasta escolhida, sem o usuário precisar rodar as
    # ferramentas por fora e importar o JSON manualmente. Snyk (precisa de
    # auth/build) e ZAP (precisa da app rodando) ficam fora dessa automação
    # por enquanto — continuam só via importação manual de relatório.
    def _on_scan_folder(self):
        if self._scan_thread is not None:
            QMessageBox.information(self, "Scan em andamento", "Já existe um scan em execução.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Selecione a pasta do projeto para escanear")
        if not folder:
            return

        self.btn_scan.setEnabled(False)
        self.status.showMessage(f"Escaneando {folder}... (Trivy, Semgrep, Gitleaks)")

        self._scan_thread = QThread()
        self._scan_worker = ScanWorker(folder)
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.progress.connect(self.status.showMessage)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_thread.finished.connect(self._cleanup_scan_thread)

        self._scan_thread.start()

    def _cleanup_scan_thread(self):
        if self._scan_thread is not None:
            self._scan_thread.deleteLater()
        if self._scan_worker is not None:
            self._scan_worker.deleteLater()
        self._scan_thread = None
        self._scan_worker = None
        self.btn_scan.setEnabled(True)

    def _on_scan_finished(self, results: list):
        imported, not_installed, failed = [], [], []

        for result in results:
            if result.success:
                try:
                    report = self.aggregator.import_file(result.report_path)
                    imported.append(f"{result.tool.upper()} — {len(report.vulnerabilities)} achado(s)")
                except ValueError as e:
                    failed.append(f"{result.tool.upper()} — relatório gerado mas não pôde ser lido: {e}")
            elif "não encontrado no PATH" in (result.error or ""):
                not_installed.append(f"{result.tool.upper()} — {result.error}")
            else:
                failed.append(f"{result.tool.upper()} — {result.error}")

        lines = []
        if imported:
            lines.append("✅ Importado com sucesso:\n" + "\n".join(f"  • {x}" for x in imported))
        if not_installed:
            lines.append("⚠️ Ferramenta não instalada nesta máquina:\n" + "\n".join(f"  • {x}" for x in not_installed))
        if failed:
            lines.append("❌ Falhou:\n" + "\n".join(f"  • {x}" for x in failed))

        QMessageBox.information(self, "Resultado do scan", "\n\n".join(lines) or "Nenhum resultado.")

        if imported:
            self._refresh_views()
            self.status.showMessage(f"Scan concluído: {len(imported)} ferramenta(s) importada(s).")
        else:
            self.status.showMessage("Scan concluído sem novos achados importados.")

    def _on_context_saved(self, ctx):
        self.ai_view.set_context(ctx)
        self.status.showMessage(f"Contexto salvo: {ctx.setor} | {ctx.porte}")

    def _on_status_changed(self):
        # A Vulnerability já foi mutada em memória pelo FindingsView — só precisa
        # recalcular o score (que filtra por status == open) e refletir nas outras abas.
        self._refresh_views()
        self.status.showMessage("Status atualizado.")

    def _on_asset_assigned(self):
        # Vínculo com ativo não afeta o score de risco do Dashboard (que é só
        # severidade), mas a próxima rodada de Priorização IA já vai usar o
        # ativo certo, já que ai_view e findings_view compartilham as mesmas
        # instâncias de Vulnerability (a mutação do asset_id é vista por ambos).
        self.status.showMessage("Ativo vinculado.")

    def _on_assets_changed(self, assets: list):
        self._push_assets(assets)
        self.status.showMessage(f"{len(assets)} ativo(s) salvos.")

    def _push_assets(self, assets: list):
        """Distribui a lista de Ativos para as views que precisam deles."""
        self.findings_view.set_assets(assets)
        self.ai_view.set_assets(asset_store.as_dict(assets))
        self.attack_path_view.set_assets(asset_store.as_dict(assets))

    def _on_clear(self):
        self.aggregator.clear()
        self._refresh_views()
        self.status.showMessage("Dados limpos.")

    def _refresh_views(self):
        vulns = self.aggregator.all_vulnerabilities
        score = calculate(vulns)
        ctx   = self.context_view.get_context()

        # Cobertura vem das FERRAMENTAS importadas, não dos achados: um scan
        # do Trivy que não encontrou nada ainda assim cobriu IaC/Container/
        # Secrets. Sem isso, um scan limpo voltaria a parecer "não escaneado".
        coverage = covered_scan_types(self.aggregator.reports)

        self.dashboard_view.update_data(
            score, vulns,
            coverage=coverage,
            context_ok=bool(ctx and ctx.preenchido),
            assets_count=len(self.assets_view.get_assets()),
        )
        self.findings_view.update_data(vulns)
        self.ai_view.update_data(vulns)
        self.ai_view.set_context(ctx)
        self.attack_path_view.update_data(vulns)

    # ------------------------------------------------------------------
    def _apply_dark_theme(self):
        # Navegação por abas no topo virou sidebar lateral (ver _build_sidebar);
        # os estilos QTabWidget/QTabBar não se aplicam mais a nada.
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {theme.BG_APP}; color: {theme.TEXT_PRIMARY}; }}
            QStatusBar {{ background: {theme.BG_SURFACE}; color: {theme.TEXT_MUTED}; font-size: 11px; }}
        """)

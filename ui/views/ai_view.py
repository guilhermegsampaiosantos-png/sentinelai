"""
ui/views/ai_view.py
Tab de IA — versão corrigida com threading robusto.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem,
    QTabWidget, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QColor

from core.models import Vulnerability
from ai.provider import LLMProvider
from ai.explainer import explain_vulnerability, explain_batch_summary
from ai.prioritizer import prioritize, PrioritizedVuln
from ai.anomaly_detector import detect, AnomalyReport
from ui import theme
from ui.icons import icon
from ui.widgets.ai_results import ResultsPanel
from ui.dialogs.settings_dialog import SettingsDialog
from ui.widgets.view_header import build_header


# ── Workers ──────────────────────────────────────────────────────────────────

class ExplainWorker(QObject):
    finished = pyqtSignal(str, str)
    error    = pyqtSignal(str)

    def __init__(self, vuln, provider):
        super().__init__()
        self.vuln     = vuln
        self.provider = provider

    def run(self):
        try:
            resp = explain_vulnerability(self.vuln, self.provider)
            self.finished.emit(resp.text, resp.backend.value)
        except Exception as e:
            self.error.emit(str(e))


class SummaryWorker(QObject):
    finished = pyqtSignal(str, str)
    error    = pyqtSignal(str)

    def __init__(self, vulns, provider):
        super().__init__()
        self.vulns    = vulns
        self.provider = provider

    def run(self):
        try:
            resp = explain_batch_summary(self.vulns, self.provider)
            self.finished.emit(resp.text, resp.backend.value)
        except Exception as e:
            self.error.emit(str(e))


class PriorityWorker(QObject):
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, vulns, provider, ctx=None, assets=None):
        super().__init__()
        self.vulns    = vulns
        self.provider = provider
        self.ctx      = ctx
        self.assets   = assets

    def run(self):
        try:
            result = prioritize(self.vulns, self.provider, ctx=self.ctx, assets=self.assets)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AnomalyWorker(QObject):
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, vulns, provider):
        super().__init__()
        self.vulns    = vulns
        self.provider = provider

    def run(self):
        try:
            result = detect(self.vulns, self.provider)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ── View principal ────────────────────────────────────────────────────────────

class AIView(QWidget):
    def __init__(self, provider: LLMProvider):
        super().__init__()
        self.provider = provider
        self._vulns: list[Vulnerability] = []
        self._ctx = None   # CompanyContext — injetado pelo MainWindow
        self._assets: dict = {}   # {asset_id: Asset} — injetado pelo MainWindow
        self._active_threads: list[tuple] = []
        self._ai_buttons: list[tuple[QPushButton, str]] = []  # (botão, texto original) — ver _set_ai_busy
        self._build_ui()

    def set_context(self, ctx):
        """Recebe o CompanyContext salvo pelo ContextView."""
        self._ctx = ctx

    def set_assets(self, assets: dict):
        """Recebe {asset_id: Asset} do MainWindow — usado para dar contexto por
        ativo à priorização (ver ai/prioritizer.py)."""
        self._assets = assets or {}

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Cabeçalho padrão (P2 #13) — mesma consistência aplicada a Findings.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(build_header("brain", "Inteligência Artificial",
                                       "explicação, priorização e detecção de anomalias assistidas por IA"))
        layout.addWidget(self._build_provider_bar())

        self.sub_tabs = QTabWidget()
        self.sub_tabs.setIconSize(QSize(15, 15))
        self.sub_tabs.addTab(self._build_explainer_tab(), icon("chat", theme.TEXT_MUTED, 15), "Explicar Vuln")
        self.sub_tabs.addTab(self._build_priority_tab(),  icon("target", theme.TEXT_MUTED, 15), "Priorização IA")
        self.sub_tabs.addTab(self._build_anomaly_tab(),   icon("search", theme.TEXT_MUTED, 15), "Padrões && Anomalias")
        layout.addWidget(self.sub_tabs)
        # Attack Path saiu daqui — virou aba própria na sidebar (AttackPathView),
        # porque é determinístico e não usa esta barra de provedor de IA acima
        # (P1 #7 da revisão de UX).

    def _build_provider_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet(f"background:{theme.BG_SURFACE}; border-bottom:1px solid {theme.BORDER};")
        bar.setFixedHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        self.provider_icon_lbl = QLabel()
        layout.addWidget(self.provider_icon_lbl)
        self.provider_label = QLabel()
        self.provider_label.setStyleSheet("border:none;")
        self._update_provider_label()
        layout.addWidget(self.provider_label)
        layout.addStretch()

        # O campo de Groq API Key morava aqui, no meio da tela de trabalho —
        # agora vive num diálogo de Configurações próprio (persistido em
        # data/settings.json), e esta barra só mostra o status + um atalho
        # pra chegar lá (P2 #15 da revisão de UX).
        btn = QPushButton(" Configurações")
        btn.setIcon(icon("plug", theme.TEXT_PRIMARY, 13))
        btn.setFixedHeight(28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{theme.BG_ELEVATED}; color:{theme.TEXT_PRIMARY}; border:1px solid {theme.BORDER_STRONG};
                border-radius:5px; padding:0 12px; font-size:11px;
            }}
            QPushButton:hover {{ background:{theme.BORDER_STRONG}; }}
        """)
        btn.clicked.connect(self._open_settings)
        layout.addWidget(btn)
        return bar

    def _build_explainer_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        left = QVBoxLayout()
        lbl = QLabel("Selecione uma vulnerabilidade:")
        lbl.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:11px;")
        left.addWidget(lbl)

        self.vuln_list = QListWidget()
        self.vuln_list.setStyleSheet(f"""
            QListWidget {{
                background:{theme.BG_SURFACE}; border:1px solid {theme.BORDER};
                border-radius:10px; font-size:12px;
            }}
            QListWidget::item {{ padding:8px 12px; border-bottom:1px solid {theme.BG_ELEVATED}; }}
            QListWidget::item:selected {{ background:{theme.BG_ELEVATED}; color:{theme.ACCENT}; }}
        """)
        self.vuln_list.setFixedWidth(320)
        left.addWidget(self.vuln_list)

        btn_explain = QPushButton(" Explicar com IA")
        btn_explain.setIcon(icon("chat", theme.AI_ACCENT_ON, 15))
        btn_explain.setFixedHeight(36)
        btn_explain.setStyleSheet(theme.button_style(
            theme.AI_ACCENT, theme.AI_ACCENT_HOVER, theme.AI_ACCENT_PRESSED, fg=theme.AI_ACCENT_ON))
        btn_explain.clicked.connect(self._run_explain)
        left.addWidget(btn_explain)
        self.btn_explain = btn_explain
        self._ai_buttons.append((btn_explain, " Explicar com IA"))

        btn_summary = QPushButton(" Resumo Executivo")
        btn_summary.setIcon(icon("document", theme.AI_ACCENT, 15))
        btn_summary.setFixedHeight(36)
        btn_summary.setStyleSheet(theme.button_style(
            theme.AI_ACCENT, theme.AI_ACCENT_HOVER, theme.AI_ACCENT_PRESSED, outline=True))
        btn_summary.clicked.connect(self._run_summary)
        left.addWidget(btn_summary)
        self.btn_summary = btn_summary
        self._ai_buttons.append((btn_summary, " Resumo Executivo"))

        layout.addLayout(left)

        right = QVBoxLayout()
        self.explain_output = self._make_output()
        right.addWidget(self.explain_output)
        self.explain_status = QLabel("")
        self.explain_status.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; font-family:monospace;")
        right.addWidget(self.explain_status)
        layout.addLayout(right)
        return w

    def _build_priority_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        btn = QPushButton(" Priorizar todas as vulnerabilidades com IA")
        btn.setIcon(icon("target", theme.AI_ACCENT_ON, 15))
        btn.setFixedHeight(38)
        btn.setStyleSheet(theme.button_style(
            theme.AI_ACCENT, theme.AI_ACCENT_HOVER, theme.AI_ACCENT_PRESSED, fg=theme.AI_ACCENT_ON))
        btn.clicked.connect(self._run_priority)
        layout.addWidget(btn)
        self.btn_priority = btn
        self._ai_buttons.append((btn, " Priorizar todas as vulnerabilidades com IA"))

        self.priority_output = ResultsPanel()
        layout.addWidget(self.priority_output)

        self.priority_status = QLabel("")
        self.priority_status.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; font-family:monospace;")
        layout.addWidget(self.priority_status)
        return w

    def _build_anomaly_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        btn = QPushButton(" Detectar padrões e anomalias")
        btn.setIcon(icon("search", theme.AI_ACCENT_ON, 15))
        btn.setFixedHeight(38)
        btn.setStyleSheet(theme.button_style(
            theme.AI_ACCENT, theme.AI_ACCENT_HOVER, theme.AI_ACCENT_PRESSED, fg=theme.AI_ACCENT_ON))
        btn.clicked.connect(self._run_anomaly)
        layout.addWidget(btn)
        self.btn_anomaly = btn
        self._ai_buttons.append((btn, " Detectar padrões e anomalias"))

        self.anomaly_output = ResultsPanel()
        layout.addWidget(self.anomaly_output)

        self.anomaly_status = QLabel("")
        self.anomaly_status.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; font-family:monospace;")
        layout.addWidget(self.anomaly_status)
        return w

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_output(self) -> QTextEdit:
        te = QTextEdit()
        te.setReadOnly(True)
        te.setStyleSheet(f"""
            QTextEdit {{
                background:{theme.BG_SURFACE}; color:{theme.TEXT_PRIMARY};
                border:1px solid {theme.BORDER}; border-radius:10px;
                padding:12px; font-size:13px;
            }}
        """)
        te.setPlaceholderText("A resposta da IA aparecerá aqui...")
        return te

    def _update_provider_label(self):
        if self.provider.available:
            self.provider_icon_lbl.setPixmap(icon("check", theme.SUCCESS, 14).pixmap(14, 14))
            self.provider_label.setText(f"IA ativa — backend: {self.provider.backend_name.upper()}")
            self.provider_label.setStyleSheet(f"color:{theme.SUCCESS}; font-size:11px; font-family:monospace; border:none;")
        else:
            self.provider_icon_lbl.setPixmap(icon("x", theme.DANGER, 14).pixmap(14, 14))
            self.provider_label.setText("IA indisponível — configure Ollama ou Groq API Key")
            self.provider_label.setStyleSheet(f"color:{theme.DANGER}; font-size:11px; font-family:monospace; border:none;")

    def _open_settings(self):
        dlg = SettingsDialog(self.provider, self)
        dlg.exec()
        self._update_provider_label()

    def _check_ai(self) -> bool:
        if not self.provider.available:
            QMessageBox.warning(self, "IA Indisponível",
                "Configure o Ollama localmente ou insira uma Groq API Key.")
            return False
        return True

    def _is_busy(self) -> bool:
        # Remove threads já finalizadas da lista. Com os botões desabilitados
        # durante o processamento (ver _set_ai_busy), este método normalmente
        # nem chega a ser chamado com _active_threads não vazio — fica como
        # rede de segurança silenciosa, sem popup bloqueante (P2 #14).
        self._active_threads = [(t, w) for t, w in self._active_threads if t.isRunning()]
        return bool(self._active_threads)

    def _set_ai_busy(self, busy: bool, active_button: QPushButton | None = None,
                      busy_text: str | None = None):
        """Desabilita as ações de IA e troca o texto do botão clicado
        enquanto uma chamada está em andamento — em vez do popup "Aguarde"
        que travava a interação até o usuário clicar OK (P2 #14)."""
        for btn, original_text in self._ai_buttons:
            btn.setEnabled(not busy)
            if btn is active_button:
                btn.setText(busy_text if (busy and busy_text) else original_text)

    # ── Runner genérico ───────────────────────────────────────────────────

    def _run_in_thread(self, worker, on_finished, on_error, loading_text, output,
                        active_button: QPushButton | None = None, busy_text: str | None = None):
        output.setPlainText(loading_text)
        self._set_ai_busy(True, active_button, busy_text)

        thread = QThread()
        worker.moveToThread(thread)

        # Adiciona à lista para manter referências vivas
        self._active_threads.append((thread, worker))

        def _cleanup():
            # Remove esse par da lista quando a thread terminar
            self._active_threads[:] = [
                (t, w) for t, w in self._active_threads if t is not thread
            ]
            self._set_ai_busy(False)

        thread.started.connect(worker.run)
        worker.finished.connect(on_finished)
        worker.finished.connect(thread.quit)
        worker.error.connect(on_error)
        worker.error.connect(thread.quit)
        thread.finished.connect(_cleanup)
        thread.finished.connect(thread.deleteLater)

        thread.start()

    # ── Actions ───────────────────────────────────────────────────────────

    def _run_explain(self):
        if not self._check_ai() or self._is_busy():
            return
        item = self.vuln_list.currentItem()
        if not item:
            QMessageBox.information(self, "Selecione", "Clique em uma vulnerabilidade da lista primeiro.")
            return

        vuln   = item.data(Qt.ItemDataRole.UserRole)
        worker = ExplainWorker(vuln, self.provider)

        def on_done(text, backend):
            self.explain_output.setMarkdown(text)
            self.explain_status.setText(f"Gerado via {backend.upper()}")

        def on_err(msg):
            self.explain_output.setPlainText(f"Erro:\n{msg}")
            self.explain_status.setText("Falha na consulta")

        self._run_in_thread(worker, on_done, on_err,
                            "Consultando IA...", self.explain_output,
                            active_button=self.btn_explain, busy_text=" Consultando IA...")

    def _run_summary(self):
        if not self._check_ai() or self._is_busy():
            return
        if not self._vulns:
            QMessageBox.information(self, "Sem dados", "Importe relatórios primeiro.")
            return

        worker = SummaryWorker(self._vulns, self.provider)

        def on_done(text, backend):
            self.explain_output.setMarkdown(text)
            self.explain_status.setText(f"Resumo gerado via {backend.upper()}")

        def on_err(msg):
            self.explain_output.setPlainText(f"Erro:\n{msg}")

        self._run_in_thread(worker, on_done, on_err,
                            "Gerando resumo executivo...", self.explain_output,
                            active_button=self.btn_summary, busy_text=" Gerando resumo...")

    def _run_priority(self):
        if not self._check_ai() or self._is_busy():
            return
        if not self._vulns:
            QMessageBox.information(self, "Sem dados", "Importe relatórios primeiro.")
            return

        # Avisa se não há contexto configurado
        ctx = self._ctx
        if not ctx or not ctx.preenchido:
            resp = QMessageBox.question(
                self, "Contexto não configurado",
                "O contexto da empresa não foi preenchido.\n"
                "A IA usará critérios técnicos genéricos.\n\n"
                "Deseja continuar mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.No:
                return
            ctx = None

        worker = PriorityWorker(self._vulns, self.provider, ctx=ctx, assets=self._assets)

        def on_done(result):
            self._show_priority(result, ctx)
            self.priority_status.setText(f"{len(result)} vulnerabilidades priorizadas")

        def on_err(msg):
            self.priority_output.setPlainText(f"Erro:\n{msg}")

        loading = (
            f"Priorizando com contexto: {ctx.setor} | {ctx.porte}..."
            if ctx and ctx.preenchido
            else "Priorizando com critérios técnicos padrão..."
        )
        self._run_in_thread(worker, on_done, on_err, loading, self.priority_output,
                            active_button=self.btn_priority, busy_text=" Priorizando...")

    def _run_anomaly(self):
        if not self._check_ai() or self._is_busy():
            return
        if not self._vulns:
            QMessageBox.information(self, "Sem dados", "Importe relatórios primeiro.")
            return

        worker = AnomalyWorker(self._vulns, self.provider)

        def on_done(report):
            self._show_anomaly(report)
            self.anomaly_status.setText("Análise concluída")

        def on_err(msg):
            self.anomaly_output.setPlainText(f"Erro:\n{msg}")

        self._run_in_thread(worker, on_done, on_err,
                            "Analisando padrões...", self.anomaly_output,
                            active_button=self.btn_anomaly, busy_text=" Analisando...")

    # ── Renderização ──────────────────────────────────────────────────────

    def _show_priority(self, result: list, ctx=None):
        self.priority_output.render_priority(result, ctx)

    def _show_anomaly(self, report):
        self.anomaly_output.render_anomaly(report)

    # ── Dados ─────────────────────────────────────────────────────────────

    def update_data(self, vulns: list[Vulnerability]):
        self._vulns = vulns
        self.vuln_list.clear()
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        for v in sorted(vulns, key=lambda v: order.get(v.severity.value, 9)):
            item = QListWidgetItem(f"[{v.severity.value.upper()}] {v.title[:55]}")
            item.setForeground(QColor(theme.SEVERITY_COLORS.get(v.severity.value, theme.TEXT_MUTED)))
            item.setData(Qt.ItemDataRole.UserRole, v)
            self.vuln_list.addItem(item)

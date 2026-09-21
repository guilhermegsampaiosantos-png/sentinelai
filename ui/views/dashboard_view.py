"""
ui/views/dashboard_view.py
Dashboard principal: tira de severidade, score, distribuição por ferramenta,
score por tipo de scan (donuts) e destaques de vulnerabilidades.

Layout inspirado em dashboards de AppSec de mercado (blocos grandes de
severidade + anéis de progresso + tabela de destaques), mas com a paleta
de cores própria da SentinelAI.
"""
from collections import Counter, defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStackedWidget, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from core.models import Vulnerability, PostureScore
from ui import theme
from ui.charts import DonutRing, BarChart
from ui.icons import icon

#: Tipos de scan exibidos nos anéis, na ordem da grade.
SCAN_TYPES_UI = ["SAST", "DAST", "SCA", "SECRETS", "CONTAINER", "IAC"]


class DashboardView(QWidget):
    """
    Duas telas em uma:

      - Sem nenhum relatório importado -> checklist de primeiros passos.
      - Com dados -> o painel de métricas de sempre.

    O motivo de existir o primeiro caso: antes, abrir a ASPM limpa mostrava
    score 0 em verde com "Boa postura". Como a escala de risco é invertida
    (0 = melhor), "nunca escaneei" ficava visualmente idêntico a "escaneei e
    está impecável" — a ferramenta se declarava segura sem ter olhado nada.
    """

    # Repassados ao MainWindow para que os botões do checklist naveguem
    go_to_context  = pyqtSignal()
    go_to_assets   = pyqtSignal()
    scan_requested = pyqtSignal()
    import_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # ── Página 0: estado inicial / primeiros passos ──────────────────
        self._empty = EmptyState()
        self._empty.go_to_context.connect(self.go_to_context)
        self._empty.go_to_assets.connect(self.go_to_assets)
        self._empty.scan_requested.connect(self.scan_requested)
        self._empty.import_requested.connect(self.import_requested)
        self._stack.addWidget(self._empty)

        # ── Página 1: dashboard com dados ────────────────────────────────
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        self._score_panel = ScorePanel()
        top_row.addWidget(self._score_panel, 0)
        self._severity_strip = SeverityStrip()
        top_row.addWidget(self._severity_strip, 1)
        layout.addLayout(top_row)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)
        self._tool_chart = ToolChartCard()
        mid_row.addWidget(self._tool_chart, 3)
        self._scan_donuts = ScanTypeDonuts()
        mid_row.addWidget(self._scan_donuts, 2)
        layout.addLayout(mid_row)

        self._highlights = HighlightsTable()
        layout.addWidget(self._highlights, 1)

        self._stack.addWidget(content)
        outer.addWidget(self._stack)

    def update_data(self, score: PostureScore, vulns: list[Vulnerability],
                     coverage: set | None = None,
                     context_ok: bool = False, assets_count: int = 0):
        """`coverage` é o conjunto de tipos de scan efetivamente executados
        (ver core/coverage.py). Vazio = nada importado ainda -> primeiros passos."""
        coverage = coverage or set()

        if not coverage:
            self._empty.set_progress(context_ok, assets_count)
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1)
        self._score_panel.update_score(score)
        self._severity_strip.update_score(score)
        self._tool_chart.update_data(vulns)
        self._scan_donuts.update_score(score, coverage)
        self._highlights.update_data(vulns)


# ──────────────────────────────────────────────────────────────────────
class StepRow(QFrame):
    """Uma linha do checklist de primeiros passos: marcador de estado,
    título, explicação do porquê, e o botão que leva até lá."""

    def __init__(self, number: int, title: str, why: str, action_text: str,
                  required: bool = False, parent=None):
        super().__init__(parent)
        self._required = required
        self.setStyleSheet(f"""
            QFrame {{ background:{theme.BG_SURFACE}; border:1px solid {theme.BORDER};
                border-radius:10px; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)

        self._marker = QLabel()
        self._marker.setFixedWidth(22)
        self._marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._marker.setStyleSheet("border:none; background:transparent;")
        lay.addWidget(self._marker)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title = QLabel(f"{number}. {title}")
        self._title.setStyleSheet(
            f"color:{theme.TEXT_PRIMARY}; font-size:13px; font-weight:600; "
            f"border:none; background:transparent;")
        text_col.addWidget(self._title)

        why_lbl = QLabel(why)
        why_lbl.setWordWrap(True)
        why_lbl.setStyleSheet(
            f"color:{theme.TEXT_MUTED}; font-size:11px; border:none; background:transparent;")
        text_col.addWidget(why_lbl)
        lay.addLayout(text_col, 1)

        self.button = QPushButton(action_text)
        self.button.setFixedHeight(30)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        lay.addWidget(self.button)

        self.set_done(False)

    def set_done(self, done: bool, detail: str | None = None):
        if done:
            self._marker.setPixmap(icon("check", theme.SUCCESS, 16).pixmap(16, 16))
            self.button.setStyleSheet(f"""
                QPushButton {{ background:transparent; color:{theme.TEXT_MUTED};
                    border:1px solid {theme.BORDER}; border-radius:6px;
                    padding:0 12px; font-size:12px; }}
                QPushButton:hover {{ color:{theme.TEXT_PRIMARY};
                    border-color:{theme.BORDER_STRONG}; }}
            """)
        else:
            # Pendente: só o passo obrigatório ganha peso visual de ação
            # primária — os opcionais não devem parecer bloqueio.
            color = theme.ACCENT if self._required else theme.TEXT_FAINT
            self._marker.setText("○")
            self._marker.setStyleSheet(
                f"color:{color}; font-size:15px; border:none; background:transparent;")
            if self._required:
                self.button.setStyleSheet(theme.button_style(
                    theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED))
            else:
                self.button.setStyleSheet(f"""
                    QPushButton {{ background:transparent; color:{theme.ACCENT};
                        border:1px solid {theme.ACCENT}; border-radius:6px;
                        padding:0 12px; font-size:12px; }}
                    QPushButton:hover {{ background:{theme.rgba(theme.ACCENT, 0.12)}; }}
                """)
        if detail:
            self._title.setToolTip(detail)


class EmptyState(QWidget):
    """Primeira tela de quem abre a ASPM sem nada importado.

    Em vez de um painel de zeros (que lê como 'tudo certo'), mostra o que
    ainda não aconteceu e o caminho até lá — na ordem real de uso, que é
    justamente o inverso da ordem em que as telas aparecem na sidebar."""

    go_to_context = pyqtSignal()
    go_to_assets = pyqtSignal()
    scan_requested = pyqtSignal()
    import_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch()

        card = QFrame()
        card.setMaximumWidth(720)
        card.setStyleSheet("background:transparent; border:none;")
        lay = QVBoxLayout(card)
        lay.setSpacing(10)

        badge = QLabel()
        badge.setPixmap(icon("shield", theme.TEXT_MUTED, 34).pixmap(34, 34))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(badge)

        title = QLabel("Nenhum dado de segurança ainda")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; border:none;")
        lay.addWidget(title)

        sub = QLabel("A SentinelAI ainda não analisou nada — por isso não há postura a exibir.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:12px; border:none;")
        lay.addWidget(sub)
        lay.addSpacing(12)

        self._step_ctx = StepRow(
            1, "Descreva sua empresa",
            "Opcional. Faz a priorização da IA considerar o seu negócio, não só a severidade técnica.",
            "Preencher")
        self._step_ctx.button.clicked.connect(self.go_to_context)
        lay.addWidget(self._step_ctx)

        self._step_assets = StepRow(
            2, "Cadastre seus ativos",
            "Opcional. É o que permite mapear caminhos de ataque e pesar o risco por sistema.",
            "Cadastrar")
        self._step_assets.button.clicked.connect(self.go_to_assets)
        lay.addWidget(self._step_assets)

        self._step_scan = StepRow(
            3, "Escaneie um projeto",
            "Necessário. Roda Trivy, Semgrep e Gitleaks numa pasta e traz os achados para cá.",
            "Escanear pasta", required=True)
        self._step_scan.button.clicked.connect(self.scan_requested)
        lay.addWidget(self._step_scan)

        alt = QPushButton("ou importar um relatório que você já tem")
        alt.setFlat(True)
        alt.setCursor(Qt.CursorShape.PointingHandCursor)
        alt.setStyleSheet(f"""
            QPushButton {{ color:{theme.TEXT_MUTED}; background:transparent; border:none;
                font-size:11.5px; padding:6px 0; }}
            QPushButton:hover {{ color:{theme.ACCENT}; text-decoration:underline; }}
        """)
        alt.clicked.connect(self.import_requested)
        lay.addWidget(alt)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card)
        row.addStretch()
        outer.addLayout(row)
        outer.addStretch()

    def set_progress(self, context_ok: bool, assets_count: int):
        self._step_ctx.set_done(context_ok)
        self._step_assets.set_done(
            assets_count > 0,
            detail=f"{assets_count} ativo(s) cadastrado(s)" if assets_count else None)
        self._step_scan.set_done(False)


# ──────────────────────────────────────────────────────────────────────
class ScorePanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(200)
        self.setStyleSheet(f"""
            QFrame {{ background:{theme.BG_SURFACE}; border:1px solid {theme.BORDER}; border-radius:14px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(20, 24, 20, 24)

        lbl = QLabel("NÍVEL DE RISCO")
        lbl.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; letter-spacing:2px; border:none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        self.score_label = QLabel("—")
        self.score_label.setFont(QFont("Monospace", 48, QFont.Weight.Bold))
        self.score_label.setStyleSheet(f"color:{theme.ACCENT}; border:none;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score_label)

        self.grade_label = QLabel("Sem dados")
        self.grade_label.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:12px; border:none;")
        self.grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.grade_label)

        self.total_label = QLabel("0 findings no total")
        self.total_label.setStyleSheet(f"color:{theme.TEXT_FAINT}; font-size:10px; border:none;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.total_label)

    def update_score(self, score: PostureScore):
        self.score_label.setText(str(int(score.overall)))
        color, grade = self._grade(score.overall)
        self.score_label.setStyleSheet(f"color:{color}; border:none;")
        self.grade_label.setText(grade)
        self.total_label.setText(f"{score.total} findings no total")

    @staticmethod
    def _grade(s: float):
        # Só é dito "nenhum risco aberto" quando ALGO foi escaneado — este
        # painel nunca é exibido sem cobertura (ver DashboardView.update_data),
        # então aqui o 0 significa de fato "escaneado e limpo".
        if s <= 0:  return theme.SUCCESS, "Nenhum risco aberto"
        if s <= 15: return theme.SUCCESS, "Boa postura"
        if s <= 40: return theme.WARNING, "Requer atenção"
        return theme.DANGER, "Postura crítica"


# ──────────────────────────────────────────────────────────────────────
class SeverityStrip(QWidget):
    """Tira de blocos grandes por severidade — contagem em destaque."""

    # (chave, rótulo, cor, cor do texto sobre o bloco)
    _SPEC = [
        ("critical_count", "Críticas", theme.SEV_CRITICAL, "#fff5f5"),
        ("high_count",     "Altas",    theme.SEV_HIGH,     "#241505"),
        ("medium_count",   "Médias",   theme.SEV_MEDIUM,   "#241c05"),
        ("low_count",      "Baixas",   theme.SEV_LOW,      "#04170e"),
    ]

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._value_labels: dict[str, QLabel] = {}
        for key, label, color, fg in self._SPEC:
            block = QFrame()
            block.setStyleSheet(f"QFrame {{ background:{color}; border-radius:14px; }}")
            b_layout = QVBoxLayout(block)
            b_layout.setContentsMargins(16, 14, 16, 14)
            b_layout.setSpacing(2)

            val = QLabel("0")
            val.setFont(QFont("Monospace", 34, QFont.Weight.Bold))
            val.setStyleSheet(f"color:{fg}; border:none; background:transparent;")
            b_layout.addWidget(val)

            name = QLabel(label.upper())
            name.setStyleSheet(f"color:{fg}; font-size:10px; letter-spacing:2px; border:none; background:transparent;")
            b_layout.addWidget(name)

            self._value_labels[key] = val
            layout.addWidget(block, 1)

    def update_score(self, score: PostureScore):
        for key, lbl in self._value_labels.items():
            lbl.setText(str(getattr(score, key)))


# ──────────────────────────────────────────────────────────────────────
class ToolChartCard(QFrame):
    """Distribuição de findings por ferramenta de scan."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background:{theme.BG_SURFACE}; border:1px solid {theme.BORDER}; border-radius:14px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("VULNERABILIDADES POR FERRAMENTA")
        title.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; letter-spacing:2px; border:none;")
        layout.addWidget(title)

        self._chart = BarChart()
        layout.addWidget(self._chart)
        layout.addStretch()

    def update_data(self, vulns: list[Vulnerability]):
        counts = Counter(v.tool for v in vulns)
        items = [
            (tool, n, theme.CHART_PALETTE[i % len(theme.CHART_PALETTE)])
            for i, (tool, n) in enumerate(counts.most_common())
        ]
        self._chart.set_data(items)


# ──────────────────────────────────────────────────────────────────────
class ScanTypeDonuts(QFrame):
    """Score por tipo de scan (SAST / DAST / SCA / SECRETS) em anéis."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background:{theme.BG_SURFACE}; border:1px solid {theme.BORDER}; border-radius:14px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("RISCO POR TIPO DE SCAN")
        title.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; letter-spacing:2px; border:none;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._rings: dict[str, DonutRing] = {}
        self._ring_labels: dict[str, QLabel] = {}
        for i, scan_type in enumerate(SCAN_TYPES_UI):
            cell = QVBoxLayout()
            cell.setSpacing(4)
            ring = DonutRing(theme.ACCENT)
            self._rings[scan_type] = ring
            cell.addWidget(ring, 0, Qt.AlignmentFlag.AlignHCenter)
            lbl = QLabel(scan_type)
            lbl.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; border:none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self._ring_labels[scan_type] = lbl
            cell.addWidget(lbl)
            wrap = QWidget()
            wrap.setLayout(cell)
            grid.addWidget(wrap, i // 2, i % 2)
        layout.addLayout(grid)

        self._coverage_note = QLabel("")
        self._coverage_note.setWordWrap(True)
        self._coverage_note.setStyleSheet(
            f"color:{theme.TEXT_MUTED}; font-size:10px; border:none;")
        layout.addWidget(self._coverage_note)
        layout.addStretch()

    def update_score(self, score: PostureScore, coverage: set):
        """`coverage` = tipos de scan realmente executados. Um tipo fora dela
        vira anel pontilhado com "—": ausência de dado, não aprovação."""
        uncovered = []
        for scan_type, ring in self._rings.items():
            lbl = self._ring_labels[scan_type]
            if scan_type not in coverage:
                ring.set_uncovered()
                lbl.setStyleSheet(f"color:{theme.TEXT_FAINT}; font-size:10px; border:none;")
                uncovered.append(scan_type)
                continue

            val = score.by_scan_type.get(scan_type, 0.0)
            color = theme.SUCCESS if val <= 15 else theme.WARNING if val <= 40 else theme.DANGER
            ring.set_value(val, f"{val:.0f}", color=color)
            lbl.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; border:none;")

        if uncovered:
            self._coverage_note.setText(
                "Sem cobertura: " + ", ".join(uncovered) +
                " — nenhuma ferramenta importada verifica esses tipos.")
        else:
            self._coverage_note.setText("Todos os tipos de scan têm cobertura.")


# ──────────────────────────────────────────────────────────────────────
class HighlightsTable(QFrame):
    """Top vulnerabilidades — agrupadas por título, ordenadas por severidade."""

    _ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background:{theme.BG_SURFACE}; border:1px solid {theme.BORDER}; border-radius:14px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(8)

        title = QLabel("PRINCIPAIS VULNERABILIDADES")
        title.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; letter-spacing:2px; border:none;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Severidade", "Título", "Ferramenta", "Ocorrências"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent; color: {theme.TEXT_PRIMARY};
                border: none; font-size: 12px;
            }}
            QTableWidget::item {{ padding: 6px 4px; border: none; border-bottom: 1px solid {theme.BG_ELEVATED}; }}
            QHeaderView::section {{
                background: transparent; color: {theme.TEXT_MUTED};
                padding: 4px; border: none; border-bottom: 1px solid {theme.BORDER};
                font-size: 10px; letter-spacing: 1px; text-transform: uppercase;
            }}
        """)
        layout.addWidget(self.table)

    def update_data(self, vulns: list[Vulnerability]):
        grouped: dict[str, dict] = {}
        for v in vulns:
            g = grouped.setdefault(v.title, {"severity": v.severity.value, "tool": v.tool, "count": 0})
            g["count"] += 1
            if self._ORDER.get(v.severity.value, 9) < self._ORDER.get(g["severity"], 9):
                g["severity"] = v.severity.value

        rows = sorted(
            grouped.items(),
            key=lambda kv: (self._ORDER.get(kv[1]["severity"], 9), -kv[1]["count"]),
        )[:8]

        self.table.setRowCount(0)
        for title, data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            color = theme.SEVERITY_COLORS.get(data["severity"], theme.TEXT_MUTED)

            sev_item = QTableWidgetItem(theme.SEVERITY_LABELS_PT.get(data["severity"], "—"))
            sev_item.setForeground(QColor(color))
            self.table.setItem(row, 0, sev_item)

            title_item = QTableWidgetItem(title)
            title_item.setForeground(QColor(theme.TEXT_PRIMARY))
            self.table.setItem(row, 1, title_item)

            tool_item = QTableWidgetItem(data["tool"])
            tool_item.setForeground(QColor(theme.TEXT_MUTED))
            self.table.setItem(row, 2, tool_item)

            count_item = QTableWidgetItem(str(data["count"]))
            count_item.setForeground(QColor(theme.TEXT_PRIMARY))
            self.table.setItem(row, 3, count_item)

        if not rows:
            self.table.setRowCount(1)
            empty = QTableWidgetItem("Sem dados — importe um relatório para começar.")
            empty.setForeground(QColor(theme.TEXT_FAINT))
            self.table.setItem(0, 0, empty)
            self.table.setSpan(0, 0, 1, 4)

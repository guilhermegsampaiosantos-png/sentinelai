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
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from core.models import Vulnerability, PostureScore
from ui import theme
from ui.charts import DonutRing, BarChart


class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # Linha 1: score geral + tira de severidade
        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        self._score_panel = ScorePanel()
        top_row.addWidget(self._score_panel, 0)
        self._severity_strip = SeverityStrip()
        top_row.addWidget(self._severity_strip, 1)
        layout.addLayout(top_row)

        # Linha 2: distribuição por ferramenta + score por tipo de scan
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)
        self._tool_chart = ToolChartCard()
        mid_row.addWidget(self._tool_chart, 3)
        self._scan_donuts = ScanTypeDonuts()
        mid_row.addWidget(self._scan_donuts, 2)
        layout.addLayout(mid_row)

        # Linha 3: destaques
        self._highlights = HighlightsTable()
        layout.addWidget(self._highlights, 1)

    def update_data(self, score: PostureScore, vulns: list[Vulnerability]):
        self._score_panel.update_score(score)
        self._severity_strip.update_score(score)
        self._tool_chart.update_data(vulns)
        self._scan_donuts.update_score(score)
        self._highlights.update_data(vulns)


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

        lbl = QLabel("POSTURA GERAL")
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
        if s >= 85: return theme.SUCCESS, "Boa postura"
        if s >= 60: return theme.WARNING, "Requer atenção"
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

        title = QLabel("SCORE POR TIPO DE SCAN")
        title.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; letter-spacing:2px; border:none;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._rings: dict[str, DonutRing] = {}
        for i, scan_type in enumerate(["SAST", "DAST", "SCA", "SECRETS"]):
            cell = QVBoxLayout()
            cell.setSpacing(4)
            ring = DonutRing(theme.ACCENT)
            self._rings[scan_type] = ring
            cell.addWidget(ring, 0, Qt.AlignmentFlag.AlignHCenter)
            lbl = QLabel(scan_type)
            lbl.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:10px; border:none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            cell.addWidget(lbl)
            wrap = QWidget()
            wrap.setLayout(cell)
            grid.addWidget(wrap, i // 2, i % 2)
        layout.addLayout(grid)
        layout.addStretch()

    def update_score(self, score: PostureScore):
        for scan_type, ring in self._rings.items():
            val = score.by_scan_type.get(scan_type)
            if val is None:
                ring.set_value(0, "N/A")
                continue
            color = theme.SUCCESS if val >= 85 else theme.WARNING if val >= 60 else theme.DANGER
            ring._color = color
            ring.set_value(val, f"{val:.0f}")


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

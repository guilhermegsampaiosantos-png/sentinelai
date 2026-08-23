"""
ui/views/findings_view.py
Tabela de vulnerabilidades com filtros por severidade e ferramenta.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QComboBox, QLabel, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from core.models import Vulnerability, Severity
from ui import theme

SEVERITY_COLORS = theme.SEVERITY_COLORS

COLUMNS = ["Severidade", "Ferramenta", "Tipo", "Título", "Arquivo / URL", "CVE", "CVSS", "Status"]


class FindingsView(QWidget):
    def __init__(self):
        super().__init__()
        self._all_vulns: list[Vulnerability] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 24)
        layout.setSpacing(12)

        # Filtros
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        filter_row.addWidget(QLabel("Filtrar:"))

        self.filter_severity = QComboBox()
        self.filter_severity.addItems(["Todas as severidades", "critical", "high", "medium", "low"])
        self.filter_severity.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.filter_severity)

        self.filter_tool = QComboBox()
        self.filter_tool.addItems(["Todas as ferramentas", "semgrep", "zap", "snyk", "gitleaks"])
        self.filter_tool.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.filter_tool)

        self.filter_status = QComboBox()
        self.filter_status.addItems(["Todos os status", "open", "in_review", "fixed", "accepted"])
        self.filter_status.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.filter_status)

        filter_row.addStretch()
        self.count_label = QLabel("0 findings")
        self.count_label.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:12px;")
        filter_row.addWidget(self.count_label)

        layout.addLayout(filter_row)

        # Tabela
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {theme.BG_SURFACE}; color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER}; border-radius: 10px;
                font-size: 12px; font-family: monospace;
            }}
            QTableWidget::item {{ padding: 6px 10px; border: none; }}
            QTableWidget::item:selected {{ background: {theme.BG_ELEVATED}; color: {theme.TEXT_PRIMARY}; }}
            QTableWidget::item:alternate {{ background: {theme.BG_SURFACE_ALT}; }}
            QHeaderView::section {{
                background: {theme.BG_ELEVATED}; color: {theme.TEXT_MUTED};
                padding: 8px 10px; border: none;
                font-size: 10px; letter-spacing: 1px; text-transform: uppercase;
            }}
            QComboBox {{
                background: {theme.BG_SURFACE}; color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER}; border-radius: 6px;
                padding: 4px 10px; font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QLabel {{ color: {theme.TEXT_PRIMARY}; font-size: 12px; }}
        """)
        layout.addWidget(self.table)

    def update_data(self, vulns: list[Vulnerability]):
        self._all_vulns = vulns
        self._apply_filters()

    def _apply_filters(self):
        sev = self.filter_severity.currentText()
        tool = self.filter_tool.currentText()
        status = self.filter_status.currentText()

        filtered = self._all_vulns
        if not sev.startswith("Todas"):
            filtered = [v for v in filtered if v.severity.value == sev]
        if not tool.startswith("Todas"):
            filtered = [v for v in filtered if v.tool == tool]
        if not status.startswith("Todos"):
            filtered = [v for v in filtered if v.status.value == status]

        self._populate_table(filtered)
        self.count_label.setText(f"{len(filtered)} findings")

    def _populate_table(self, vulns: list[Vulnerability]):
        self.table.setRowCount(0)
        # Ordenar: critical → high → medium → low → info
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        vulns = sorted(vulns, key=lambda v: order.get(v.severity.value, 9))

        for v in vulns:
            row = self.table.rowCount()
            self.table.insertRow(row)

            color = SEVERITY_COLORS.get(v.severity.value, "#888")

            cells = [
                (v.severity.value.upper(), color),
                (v.tool, theme.TEXT_MUTED),
                (v.scan_type.value, theme.TEXT_MUTED),
                (v.title, theme.TEXT_PRIMARY),
                (v.file_path or v.url or "—", theme.ACCENT),
                (v.cve_id or "—", theme.TEXT_MUTED),
                (str(v.cvss_score) if v.cvss_score else "—", theme.TEXT_MUTED),
                (v.status.value, theme.TEXT_MUTED),
            ]

            for col, (text, fcolor) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setForeground(QColor(fcolor))
                self.table.setItem(row, col, item)

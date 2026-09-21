"""
ui/views/findings_view.py
Tabela de vulnerabilidades com filtros por severidade e ferramenta.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QComboBox, QLabel, QHeaderView, QAbstractItemView, QMenu, QLineEdit,
    QStackedWidget, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QAction

from core.models import Vulnerability, Severity, Status
from core.asset import Asset
from ui import theme
from ui.icons import icon
from ui.widgets.view_header import build_header

SEVERITY_COLORS = theme.SEVERITY_COLORS

COLUMNS = ["Severidade", "Ferramenta", "Tipo", "Título", "Arquivo / URL", "CVE", "CVSS", "Status", "Ativo"]

# Cor de cada status na coluna Status, e rótulo em pt-br pro menu de contexto
STATUS_COLORS = {
    "open":      theme.TEXT_MUTED,
    "in_review": theme.WARNING,
    "fixed":     theme.SUCCESS,
    "accepted":  theme.TEXT_FAINT,
}
STATUS_LABELS_PT = {
    Status.OPEN:      "Aberta",
    Status.IN_REVIEW:  "Em revisão",
    Status.FIXED:      "Corrigida",
    Status.ACCEPTED:   "Risco aceito",
}
# Mesmo dicionário, indexado pelo valor string (Status.value) — usado para
# colorir/rotular a célula da tabela a partir de v.status.value.
STATUS_LABELS_PT_BY_VALUE = {s.value: label for s, label in STATUS_LABELS_PT.items()}


class FindingsView(QWidget):
    status_changed = pyqtSignal()  # emitido quando o usuário muda o status de um finding
    asset_assigned = pyqtSignal()  # emitido quando o usuário vincula/desvincula um ativo

    def __init__(self):
        super().__init__()
        self._all_vulns: list[Vulnerability] = []
        self._assets: list[Asset] = []
        self._assets_by_id: dict[str, Asset] = {}
        self._build_ui()

    def _build_ui(self):
        # Cabeçalho padrão (P2 #13) — antes Findings era uma das telas sem
        # nenhum header, ao lado de Ativos/Contexto que tinham um cada.
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(build_header("list", "Findings", "vulnerabilidades importadas de todos os scans"))

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 16, 24, 24)
        layout.setSpacing(12)

        # Filtros
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        filter_row.addWidget(QLabel("Filtrar:"))

        # Severidade e Status mostram rótulos em pt-br, mas guardam o valor
        # em inglês (currentData()) para comparar direto com Severity/Status
        # — antes a comparação usava currentText() contra v.severity.value,
        # o que quebraria no instante em que o texto virasse português.
        self.filter_severity = QComboBox()
        self.filter_severity.addItem("Todas as severidades", None)
        for sev in Severity:
            self.filter_severity.addItem(theme.SEVERITY_LABELS_PT.get(sev.value, sev.value.upper()), sev.value)
        self.filter_severity.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.filter_severity)

        # Ferramenta é populada dinamicamente a partir do que foi
        # efetivamente importado (ver _refresh_tool_filter) em vez de uma
        # lista fixa — uma lista fixa ficava desatualizada a cada scanner
        # novo e mostrava ferramentas que nunca rodaram.
        self.filter_tool = QComboBox()
        self.filter_tool.addItem("Todas as ferramentas", None)
        self.filter_tool.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.filter_tool)

        self.filter_status = QComboBox()
        self.filter_status.addItem("Todos os status", None)
        for status in Status:
            self.filter_status.addItem(STATUS_LABELS_PT[status], status.value)
        self.filter_status.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.filter_status)

        self.filter_asset = QComboBox()
        self.filter_asset.addItems(["Todos os ativos", "Sem ativo"])
        self.filter_asset.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.filter_asset)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar por título ou CVE...")
        self.search_box.setFixedWidth(220)
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background:{theme.BG_INPUT}; color:{theme.TEXT_PRIMARY};
                border:1px solid {theme.BORDER}; border-radius:6px;
                padding:4px 10px; font-size:12px;
            }}
        """)
        self.search_box.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self.search_box)

        filter_row.addStretch()
        hint_label = QLabel("clique direito num finding para mudar o status")
        hint_label.setStyleSheet(f"color:{theme.TEXT_FAINT}; font-size:10px; font-style:italic;")
        filter_row.addWidget(hint_label)
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
        # Ordenação por coluna, clicando no cabeçalho. A referência ao
        # objeto Vulnerability vai na célula (UserRole), não num índice de
        # linha — assim o menu de contexto continua certo mesmo depois de
        # o usuário reordenar a tabela clicando num cabeçalho.
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_status_menu)
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

        # Estado vazio: distingue "nada foi importado ainda" de "os filtros
        # não bateram com nada" — antes as duas situações mostravam a mesma
        # tabela vazia e o usuário não sabia se precisava importar um
        # relatório ou só afrouxar um filtro.
        self._results_stack = QStackedWidget()
        self._results_stack.addWidget(self.table)
        self._results_stack.addWidget(self._build_empty_panel())
        layout.addWidget(self._results_stack)

        root.addWidget(body)

    def _build_empty_panel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addStretch()

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_icon_lbl = icon_lbl
        lay.addWidget(icon_lbl)

        msg = QLabel("")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:13px; border:none;")
        self._empty_msg = msg
        lay.addWidget(msg)

        btn = QPushButton("Limpar filtros")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedWidth(160)
        btn.setFixedHeight(30)
        btn.setStyleSheet(theme.button_style(
            theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED, outline=True))
        btn.clicked.connect(self._clear_filters)
        self._clear_filters_btn = btn
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    def update_data(self, vulns: list[Vulnerability]):
        self._all_vulns = vulns
        self._refresh_tool_filter()
        self._apply_filters()

    def _refresh_tool_filter(self):
        """Recalcula a lista de ferramentas do filtro a partir do que foi
        efetivamente importado (P2 #11) — uma lista fixa desatualiza a cada
        scanner novo e mostra opções que nunca vão ter resultado."""
        tools = sorted({v.tool for v in self._all_vulns})
        current = self.filter_tool.currentData()

        self.filter_tool.blockSignals(True)
        self.filter_tool.clear()
        self.filter_tool.addItem("Todas as ferramentas", None)
        for tool in tools:
            self.filter_tool.addItem(tool, tool)
        idx = self.filter_tool.findData(current)
        self.filter_tool.setCurrentIndex(idx if idx >= 0 else 0)
        self.filter_tool.blockSignals(False)

    def set_assets(self, assets: list[Asset]):
        """Chamado pelo MainWindow sempre que a lista de Ativos muda (criação,
        edição ou exclusão na aba Ativos) — atualiza o filtro, a coluna Ativo
        e o submenu de vinculação."""
        self._assets = assets
        self._assets_by_id = {a.id: a for a in assets}

        current = self.filter_asset.currentText()
        self.filter_asset.blockSignals(True)
        self.filter_asset.clear()
        self.filter_asset.addItems(["Todos os ativos", "Sem ativo"] + [a.label for a in assets])
        idx = self.filter_asset.findText(current)
        self.filter_asset.setCurrentIndex(idx if idx >= 0 else 0)
        self.filter_asset.blockSignals(False)

        self._apply_filters()

    def _clear_filters(self):
        for combo in (self.filter_severity, self.filter_tool, self.filter_status, self.filter_asset):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.search_box.blockSignals(True)
        self.search_box.clear()
        self.search_box.blockSignals(False)
        self._apply_filters()

    def _apply_filters(self):
        sev = self.filter_severity.currentData()
        tool = self.filter_tool.currentData()
        status = self.filter_status.currentData()
        asset_filter = self.filter_asset.currentText()
        query = self.search_box.text().strip().lower()

        filtered = self._all_vulns
        if sev is not None:
            filtered = [v for v in filtered if v.severity.value == sev]
        if tool is not None:
            filtered = [v for v in filtered if v.tool == tool]
        if status is not None:
            filtered = [v for v in filtered if v.status.value == status]
        if asset_filter == "Sem ativo":
            filtered = [v for v in filtered if not v.asset_id]
        elif asset_filter != "Todos os ativos":
            asset_id = next((a.id for a in self._assets if a.label == asset_filter), None)
            filtered = [v for v in filtered if v.asset_id == asset_id]
        if query:
            filtered = [
                v for v in filtered
                if query in v.title.lower() or query in (v.cve_id or "").lower()
            ]

        self.count_label.setText(f"{len(filtered)} findings")

        if not self._all_vulns:
            self._show_empty(
                "shield",
                "Nenhum finding importado ainda — escaneie um projeto ou importe um relatório.",
                allow_clear=False,
            )
        elif not filtered:
            self._show_empty(
                "search",
                "Nenhum finding corresponde aos filtros atuais.",
                allow_clear=True,
            )
        else:
            self._results_stack.setCurrentIndex(0)
            self._populate_table(filtered)

    def _show_empty(self, icon_name: str, text: str, allow_clear: bool):
        self._empty_icon_lbl.setPixmap(icon(icon_name, theme.TEXT_FAINT, 32).pixmap(32, 32))
        self._empty_msg.setText(text)
        self._clear_filters_btn.setVisible(allow_clear)
        self._results_stack.setCurrentIndex(1)

    def _populate_table(self, vulns: list[Vulnerability]):
        self.table.setSortingEnabled(False)  # evita reordenar linha a linha durante o insert
        self.table.setRowCount(0)
        # Ordenar: critical → high → medium → low → info (ordem inicial;
        # o usuário pode clicar num cabeçalho depois para reordenar)
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        vulns = sorted(vulns, key=lambda v: order.get(v.severity.value, 9))

        for v in vulns:
            row = self.table.rowCount()
            self.table.insertRow(row)

            color = SEVERITY_COLORS.get(v.severity.value, "#888")
            has_link = bool(v.file_path or v.url)

            asset = self._assets_by_id.get(v.asset_id) if v.asset_id else None
            cells = [
                (theme.SEVERITY_LABELS_PT.get(v.severity.value, v.severity.value.upper()), color),
                (v.tool, theme.TEXT_MUTED),
                (v.scan_type.value, theme.TEXT_MUTED),
                (v.title, theme.TEXT_PRIMARY),
                (v.file_path or v.url or "—", theme.ACCENT if has_link else theme.TEXT_FAINT),
                (v.cve_id or "—", theme.TEXT_MUTED),
                (f"{v.cvss_score:.1f}" if v.cvss_score is not None else "—", theme.TEXT_MUTED),
                (STATUS_LABELS_PT_BY_VALUE.get(v.status.value, v.status.value),
                 STATUS_COLORS.get(v.status.value, theme.TEXT_MUTED)),
                (asset.label if asset else "—", theme.ACCENT if asset else theme.TEXT_FAINT),
            ]

            for col, (text, fcolor) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setForeground(QColor(fcolor))
                if col == 0:
                    # A referência à Vulnerability real mora na célula, não
                    # num índice de linha — sobrevive a reordenação por sort.
                    item.setData(Qt.ItemDataRole.UserRole, v)
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)

    # ------------------------------------------------------------------
    def _vuln_at_row(self, row: int) -> Vulnerability | None:
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _show_status_menu(self, pos):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        if not rows:
            row = self.table.rowAt(pos.y())
            if row < 0:
                return
            rows = [row]

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{theme.BG_ELEVATED}; color:{theme.TEXT_PRIMARY};
                     border:1px solid {theme.BORDER}; }}
            QMenu::item:selected {{ background:{theme.ACCENT}; }}
        """)
        label = "Marcar finding como:" if len(rows) == 1 else f"Marcar {len(rows)} findings como:"
        title_action = QAction(label, self)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        for status in Status:
            action = QAction(STATUS_LABELS_PT[status], self)
            action.triggered.connect(lambda checked=False, s=status, rs=rows: self._set_status(rs, s))
            menu.addAction(action)

        menu.addSeparator()
        asset_menu = menu.addMenu("Vincular a ativo")
        asset_menu.setStyleSheet(menu.styleSheet())
        if self._assets:
            for asset in self._assets:
                action = QAction(asset.label, self)
                action.triggered.connect(lambda checked=False, aid=asset.id, rs=rows: self._set_asset(rs, aid))
                asset_menu.addAction(action)
            asset_menu.addSeparator()
        else:
            none_action = QAction("Nenhum ativo cadastrado — crie um na aba Ativos", self)
            none_action.setEnabled(False)
            asset_menu.addAction(none_action)
            asset_menu.addSeparator()
        unset_action = QAction("Remover vínculo", self)
        unset_action.triggered.connect(lambda checked=False, rs=rows: self._set_asset(rs, None))
        asset_menu.addAction(unset_action)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _set_status(self, rows: list[int], status: Status):
        for row in rows:
            v = self._vuln_at_row(row)
            if v is not None:
                v.status = status
        self.status_changed.emit()

    def _set_asset(self, rows: list[int], asset_id: str | None):
        for row in rows:
            v = self._vuln_at_row(row)
            if v is not None:
                v.asset_id = asset_id
        self._apply_filters()  # re-renderiza a coluna Ativo com o novo vínculo
        self.asset_assigned.emit()

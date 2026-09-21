"""
ui/views/assets_view.py
Aba "Ativos" — CRUD de aplicações/serviços individuais da empresa.

Diferente do Contexto da Empresa (um contexto único, global), cada Ativo
aqui representa um sistema específico com sua própria exposição e
criticidade. Vulnerabilidades importadas podem ser vinculadas a um Ativo
na aba Findings (clique direito → Vincular a ativo), e isso alimenta a
priorização com contexto real daquele sistema — ver ai/prioritizer.py.

Salva automaticamente em data/assets.json.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox, QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.asset import Asset, ENVIRONMENTS, load_all, save_all
from ui import theme
from ui.icons import icon
from ui.widgets.view_header import build_header

ENV_LABELS_PT = {"development": "Desenvolvimento", "staging": "Staging", "production": "Produção"}
ENV_LABELS_PT_REV = {v: k for k, v in ENV_LABELS_PT.items()}


class AssetsView(QWidget):
    """Tab de CRUD de Ativos."""
    assets_changed = pyqtSignal(list)   # emite list[Asset] sempre que a lista muda

    def __init__(self):
        super().__init__()
        self._assets: list[Asset] = load_all()
        self._current: Asset | None = None
        self._suppress_dirty_check = False  # evita re-perguntar ao reverter a seleção
        self._build_ui()
        self._refresh_list()
        if self._assets:
            self._list.setCurrentRow(0)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        header = build_header(
            "server", "Ativos",
            "aplicações/serviços vinculáveis a vulnerabilidades na aba Findings")
        root.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(16)

        # ── Coluna esquerda: lista ──────────────────────────────────────
        left = QVBoxLayout()
        btn_new = QPushButton(" Novo Ativo")
        btn_new.setIcon(icon("plus", theme.ACCENT_ON, 14))
        btn_new.setFixedHeight(32)
        btn_new.setStyleSheet(theme.button_style(theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED))
        btn_new.clicked.connect(self._new_asset)
        left.addWidget(btn_new)

        self._list = QListWidget()
        self._list.setFixedWidth(280)
        self._list.setStyleSheet(f"""
            QListWidget {{ background:{theme.BG_SURFACE}; border:1px solid {theme.BORDER};
                border-radius:10px; font-size:12px; }}
            QListWidget::item {{ padding:10px 12px; border-bottom:1px solid {theme.BG_ELEVATED}; }}
            QListWidget::item:selected {{ background:{theme.BG_ELEVATED}; color:{theme.ACCENT}; }}
        """)
        self._list.currentRowChanged.connect(self._on_select)
        left.addWidget(self._list)
        body.addLayout(left)

        # ── Coluna direita: formulário ───────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(12)

        right.addWidget(self._lbl("Nome do ativo:"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("ex.: Portal Financeiro, API de Pagamentos")
        self._name.setStyleSheet(self._le_style())
        right.addWidget(self._name)

        right.addWidget(self._lbl("Ambiente:"))
        self._env = QComboBox()
        self._env.addItems([ENV_LABELS_PT[e] for e in ENVIRONMENTS])
        self._env.setStyleSheet(self._combo_style())
        right.addWidget(self._env)

        right.addWidget(self._lbl("Exposição e criticidade:"))
        self._internet = QCheckBox("Internet-facing (acessível pela internet)")
        self._sensitive = QCheckBox("Contém dados sensíveis (PII, financeiro, saúde...)")
        self._critical = QCheckBox("Ativo crítico para a operação")
        self._customer = QCheckBox("Customer-facing (acessado diretamente por clientes)")
        for cb in [self._internet, self._sensitive, self._critical, self._customer]:
            cb.setStyleSheet(self._cb_style())
            right.addWidget(cb)

        right.addStretch()

        btn_row = QHBoxLayout()
        btn_save = QPushButton(" Salvar")
        btn_save.setIcon(icon("save", theme.ACCENT_ON, 14))
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet(theme.button_style(theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED))
        btn_save.clicked.connect(self._save_current)
        btn_row.addWidget(btn_save)

        btn_delete = QPushButton(" Excluir")
        btn_delete.setIcon(icon("trash", theme.DANGER, 14))
        btn_delete.setFixedHeight(34)
        btn_delete.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{theme.DANGER}; border:1px solid {theme.DANGER};
                border-radius:6px; padding:0 14px; font-size:13px; }}
            QPushButton:hover {{ background:{theme.rgba(theme.DANGER, 0.12)}; }}
        """)
        btn_delete.clicked.connect(self._delete_current)
        btn_row.addWidget(btn_delete)
        btn_row.addStretch()
        right.addLayout(btn_row)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color:{theme.AI_ACCENT}; font-size:11px; font-family:monospace;")
        right.addWidget(self._status_label)

        body.addLayout(right, 1)
        root.addLayout(body)

    # ── Ações ─────────────────────────────────────────────────────────────

    def _form_snapshot(self) -> tuple:
        return (
            self._name.text().strip(),
            ENV_LABELS_PT_REV.get(self._env.currentText(), "production"),
            self._internet.isChecked(),
            self._sensitive.isChecked(),
            self._critical.isChecked(),
            self._customer.isChecked(),
        )

    def _current_snapshot(self) -> tuple:
        a = self._current
        if a is None:
            return ("", "production", False, False, False, False)
        return (a.name, a.environment, a.internet_facing,
                a.contains_sensitive_data, a.critical_asset, a.customer_facing)

    def _is_dirty(self) -> bool:
        """Formulário tem alterações não salvas em relação ao ativo atual
        (ou, se nenhum estiver selecionado, em relação ao formulário em branco)."""
        return self._form_snapshot() != self._current_snapshot()

    def _confirm_discard(self) -> bool:
        """Pergunta antes de descartar alterações não salvas. Antes disso,
        trocar de ativo na lista ou clicar em 'Novo Ativo' simplesmente
        sobrescrevia o formulário sem avisar — perda silenciosa de dados."""
        if not self._is_dirty():
            return True
        resp = QMessageBox.question(
            self, "Alterações não salvas",
            "Este ativo tem alterações que ainda não foram salvas. "
            "Descartar essas alterações?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return resp == QMessageBox.StandardButton.Yes

    def _new_asset(self):
        if not self._suppress_dirty_check and not self._confirm_discard():
            return
        self._current = None
        self._name.clear()
        self._env.setCurrentIndex(ENVIRONMENTS.index("production"))
        for cb in [self._internet, self._sensitive, self._critical, self._customer]:
            cb.setChecked(False)
        self._suppress_dirty_check = True
        self._list.setCurrentRow(-1)
        self._suppress_dirty_check = False
        self._name.setFocus()
        self._status_label.setText("Novo ativo — preencha e clique em Salvar")

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._assets):
            return

        if not self._suppress_dirty_check and not self._confirm_discard():
            # Usuário recusou descartar — reverte a seleção da lista sem
            # disparar este mesmo aviso de novo.
            self._suppress_dirty_check = True
            prev_row = self._assets.index(self._current) if self._current in self._assets else -1
            self._list.setCurrentRow(prev_row)
            self._suppress_dirty_check = False
            return

        a = self._assets[row]
        self._current = a
        self._name.setText(a.name)
        idx = self._env.findText(ENV_LABELS_PT.get(a.environment, a.environment))
        if idx >= 0:
            self._env.setCurrentIndex(idx)
        self._internet.setChecked(a.internet_facing)
        self._sensitive.setChecked(a.contains_sensitive_data)
        self._critical.setChecked(a.critical_asset)
        self._customer.setChecked(a.customer_facing)
        self._status_label.setText("")

    def _save_current(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Campo obrigatório", "Dê um nome ao ativo.")
            self._name.setFocus()
            return

        env = ENV_LABELS_PT_REV.get(self._env.currentText(), "production")
        if self._current is None:
            self._current = Asset(name=name, environment=env)
            self._assets.append(self._current)
        else:
            self._current.name = name
            self._current.environment = env
        self._current.internet_facing = self._internet.isChecked()
        self._current.contains_sensitive_data = self._sensitive.isChecked()
        self._current.critical_asset = self._critical.isChecked()
        self._current.customer_facing = self._customer.isChecked()

        if save_all(self._assets):
            self._status_label.setText("✓ Salvo")
            self._refresh_list()
            row = self._assets.index(self._current)
            self._list.setCurrentRow(row)
            self.assets_changed.emit(list(self._assets))
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível salvar o ativo.")

    def _delete_current(self):
        if self._current is None:
            return
        resp = QMessageBox.question(
            self, "Excluir ativo",
            f'Excluir o ativo "{self._current.label}"? '
            "Vulnerabilidades vinculadas a ele ficam sem ativo, mas não são apagadas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        self._assets = [a for a in self._assets if a.id != self._current.id]
        save_all(self._assets)
        self._refresh_list()
        self._new_asset()
        self.assets_changed.emit(list(self._assets))

    def _refresh_list(self):
        self._list.blockSignals(True)
        self._list.clear()
        for a in self._assets:
            tags = []
            if a.internet_facing: tags.append("🌐")
            if a.critical_asset: tags.append("⭐")
            if a.contains_sensitive_data: tags.append("🔒")
            prefix = " ".join(tags) + " " if tags else ""
            item = QListWidgetItem(f"{prefix}{a.label}  ({ENV_LABELS_PT.get(a.environment, a.environment)})")
            self._list.addItem(item)
        self._list.blockSignals(False)

    # ── Estilos ───────────────────────────────────────────────────────────

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; font-size:12px;")
        return l

    def _cb_style(self) -> str:
        return f"""
            QCheckBox {{ color:{theme.TEXT_PRIMARY}; font-size:12px; spacing:6px; }}
            QCheckBox::indicator {{ width:16px; height:16px; border:1px solid {theme.BORDER_STRONG};
                border-radius:3px; background:{theme.BG_INPUT}; }}
            QCheckBox::indicator:checked {{ background:{theme.ACCENT}; border-color:{theme.ACCENT}; }}
        """

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{ background:{theme.BG_INPUT}; color:{theme.TEXT_PRIMARY}; border:1px solid {theme.BORDER};
                border-radius:6px; padding:4px 10px; font-size:12px; }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{ background:{theme.BG_ELEVATED}; color:{theme.TEXT_PRIMARY};
                selection-background-color:{theme.BORDER}; }}
        """

    def _le_style(self) -> str:
        return f"""
            QLineEdit {{ background:{theme.BG_INPUT}; color:{theme.TEXT_PRIMARY}; border:1px solid {theme.BORDER};
                border-radius:6px; padding:6px 10px; font-size:12px; }}
        """

    # ── Acesso externo ────────────────────────────────────────────────────

    def get_assets(self) -> list[Asset]:
        return self._assets

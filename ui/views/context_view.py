"""
ui/views/context_view.py
Formulário de contexto da empresa — preenchido antes da priorização pela IA.
Salva automaticamente em data/company_context.json.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QCheckBox, QComboBox, QSlider,
    QTextEdit, QLineEdit, QMessageBox, QGroupBox, QGridLayout,
    QButtonGroup, QRadioButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.company_context import CompanyContext, save, load
from ui import theme
from ui.icons import icon
from ui.widgets.view_header import build_header


class NoScrollComboBox(QComboBox):
    """
    QComboBox que ignora o scroll do mouse enquanto a lista de opções NÃO
    está aberta.

    Problema que isso resolve: dentro de um formulário longo (QScrollArea),
    rolar a página com a roda do mouse passando por cima de um combo box
    troca o valor selecionado sem o usuário querer — o scroll "vaza" pra
    dentro do campo em vez de rolar a página.

    A primeira versão disso checava `self.hasFocus()`, mas um QComboBox
    continua com foco depois de um clique legítimo (pra escolher uma opção)
    até outra coisa roubar o foco — então qualquer scroll acidental
    *depois* daquele clique, passando o mouse por cima do campo já
    selecionado, ainda mudava o valor. Checar `self.view().isVisible()` em
    vez de foco resolve isso de verdade: só reage ao scroll enquanto a
    lista está literalmente aberta na tela (ou seja, o usuário já clicou
    pra abrir e está navegando pelas opções agora, não em algum momento
    no passado) — fora disso, o evento é ignorado aqui e sobe pra
    QScrollArea, que rola a página normalmente.
    """
    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoScrollSlider(QSlider):
    """Slider de prioridade (Disponibilidade/Confidencialidade/Integridade)
    que ignora scroll por completo — a interação prevista é clicar e
    arrastar (ver tooltip), então não há um estado equivalente a "lista
    aberta" que justifique reagir ao scroll em algum momento."""
    def wheelEvent(self, event):
        event.ignore()


class ContextView(QWidget):
    """Tab de configuração do contexto da empresa."""
    context_saved = pyqtSignal(object)   # emite CompanyContext quando salvo

    def __init__(self):
        super().__init__()
        self._ctx = load()
        self._build_ui()
        self._populate(self._ctx)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        header = build_header("target", "Contexto da Empresa")
        hl = header.content_layout

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color:{theme.AI_ACCENT}; font-size:11px; font-family:monospace; border:none;")
        hl.addWidget(self._status_label)

        btn_save = QPushButton(" Salvar Contexto")
        btn_save.setIcon(icon("save", theme.ACCENT_ON, 14))
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet(theme.button_style(theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED))
        btn_save.clicked.connect(self._save)
        hl.addWidget(btn_save)
        root.addWidget(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{theme.BG_APP}; }}")

        content = QWidget()
        content.setStyleSheet(f"background:{theme.BG_APP};")
        form = QVBoxLayout(content)
        form.setContentsMargins(24, 20, 24, 40)
        form.setSpacing(16)

        # ── Seções ────────────────────────────────────────────────────────
        form.addWidget(self._section("1. Perfil da Empresa", self._build_perfil()))
        form.addWidget(self._section("2. Prioridades de Negócio", self._build_prioridades()))
        form.addWidget(self._section("3. Dados Sensíveis", self._build_dados()))
        form.addWidget(self._section("4. Sistemas Críticos", self._build_sistemas()))
        form.addWidget(self._section("5. Exposição e Infraestrutura", self._build_infra()))
        form.addWidget(self._section("6. Controles de Acesso", self._build_acesso()))
        form.addWidget(self._section("7. Regulamentações", self._build_reg()))
        form.addWidget(self._section("8. Impacto ao Negócio", self._build_negocio()))
        form.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _make_combo(self, items: list, placeholder: str) -> "NoScrollComboBox":
        """
        Combo box com uma instrução clara como primeiro item (ex: "Selecione
        o setor...") em vez de um item em branco — o usuário via exatamente
        "" antes, sem nenhuma pista do que fazer ali. Esse primeiro item fica
        desabilitado (itálico/apagado) depois que uma opção real é escolhida,
        pra não dar pra "voltar" pro placeholder por engano.
        """
        combo = NoScrollComboBox()
        combo.addItem(placeholder)
        combo.addItems(items)
        combo.model().item(0).setEnabled(False)
        combo.setStyleSheet(self._combo_style())
        combo.setToolTip("Clique para selecionar")
        return combo

    @staticmethod
    def _combo_value(combo: QComboBox) -> str:
        """O índice 0 é sempre o placeholder de instrução — tratamos como
        campo ainda não preenchido (valor vazio), nunca como um setor/porte/
        impacto/exposição de verdade chamado "Selecione o setor..."."""
        return "" if combo.currentIndex() <= 0 else combo.currentText()

    def _section(self, title: str, inner: QWidget) -> QGroupBox:
        box = QGroupBox(title)
        box.setStyleSheet(f"""
            QGroupBox {{
                color:{theme.ACCENT}; font-weight:bold; font-size:12px;
                border:1px solid {theme.BORDER}; border-radius:8px;
                margin-top:8px; padding-top:12px;
                background:{theme.BG_SURFACE};
            }}
            QGroupBox::title {{ subcontrol-origin:margin; left:12px; padding:0 6px; }}
        """)
        lay = QVBoxLayout(box)
        lay.addWidget(inner)
        return box

    # ── Seção 1: Perfil ───────────────────────────────────────────────────

    def _build_perfil(self) -> QWidget:
        w = QWidget()
        lay = QGridLayout(w)
        lay.setSpacing(12)

        lay.addWidget(self._lbl("Setor da empresa: (clique aqui)"), 0, 0)
        self._setor = self._make_combo(
            ["Financeiro", "Saúde", "Governo", "Varejo",
             "Tecnologia", "Educação", "Indústria", "Outro"],
            "Selecione o setor...")
        lay.addWidget(self._setor, 0, 1)

        self._setor_outro = QLineEdit()
        self._setor_outro.setPlaceholderText("Qual setor?")
        self._setor_outro.setStyleSheet(self._le_style())
        self._setor_outro.setVisible(False)
        lay.addWidget(self._setor_outro, 0, 2)
        self._setor.currentTextChanged.connect(
            lambda text: self._setor_outro.setVisible(text == "Outro"))

        lay.addWidget(self._lbl("Porte da empresa: (clique aqui)"), 1, 0)
        self._porte = self._make_combo(
            ["Pequena", "Média", "Grande", "Enterprise"],
            "Selecione o porte...")
        lay.addWidget(self._porte, 1, 1)

        lay.addWidget(self._lbl("Regiões de operação:"), 2, 0)
        reg_w = QWidget()
        reg_l = QHBoxLayout(reg_w)
        reg_l.setContentsMargins(0,0,0,0)
        self._reg_brasil = QCheckBox("Brasil")
        self._reg_latam  = QCheckBox("América Latina")
        self._reg_global = QCheckBox("Global")
        for cb in [self._reg_brasil, self._reg_latam, self._reg_global]:
            cb.setStyleSheet(self._cb_style())
            reg_l.addWidget(cb)
        reg_l.addStretch()
        lay.addWidget(reg_w, 2, 1)

        return w

    # ── Seção 2: Prioridades ──────────────────────────────────────────────

    def _build_prioridades(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        self._slider_disp, disp_w = self._slider_row("Disponibilidade dos sistemas")
        self._slider_conf, conf_w = self._slider_row("Confidencialidade dos dados")
        self._slider_intg, intg_w = self._slider_row("Integridade das informações")
        lay.addWidget(disp_w)
        lay.addWidget(conf_w)
        lay.addWidget(intg_w)
        return w

    def _slider_row(self, label: str):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        lbl = self._lbl(f"{label}:")
        lbl.setFixedWidth(260)
        lay.addWidget(lbl)

        slider = NoScrollSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 10)
        slider.setValue(5)
        slider.setFixedWidth(200)
        slider.setToolTip("Clique e arraste para ajustar")
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height:4px; background:{theme.BORDER}; border-radius:2px; }}
            QSlider::handle:horizontal {{ width:14px; height:14px; background:{theme.ACCENT};
                border-radius:7px; margin:-5px 0; }}
            QSlider::sub-page:horizontal {{ background:{theme.ACCENT}; border-radius:2px; }}
        """)

        val_lbl = QLabel("5")
        val_lbl.setFixedWidth(24)
        val_lbl.setStyleSheet(f"color:{theme.ACCENT}; font-family:monospace; font-weight:bold; font-size:13px;")
        slider.valueChanged.connect(lambda v: val_lbl.setText(str(v)))

        lay.addWidget(slider)
        lay.addWidget(val_lbl)
        lay.addStretch()
        return slider, w

    # ── Seção 3: Dados sensíveis ──────────────────────────────────────────

    def _build_dados(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._pii     = QCheckBox("Armazena dados pessoais (PII)")
        self._fin     = QCheckBox("Processa dados financeiros")
        self._med     = QCheckBox("Armazena informações médicas")
        self._pi      = QCheckBox("Possui propriedade intelectual crítica")
        self._seg_ind = QCheckBox("Possui segredos industriais")
        for cb in [self._pii, self._fin, self._med, self._pi, self._seg_ind]:
            cb.setStyleSheet(self._cb_style())
            lay.addWidget(cb)
        return w

    # ── Seção 4: Sistemas críticos ────────────────────────────────────────

    def _build_sistemas(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        lay.addWidget(self._lbl("Sistemas essenciais para o funcionamento (um por linha):"))
        self._sistemas = QTextEdit()
        self._sistemas.setPlaceholderText("Portal de clientes\nERP\nAPI de pagamentos\nBanco de dados principal")
        self._sistemas.setFixedHeight(90)
        self._sistemas.setStyleSheet(self._te_style())
        lay.addWidget(self._sistemas)

        lay.addWidget(self._lbl("Sistema mais crítico (único sobrevivente em uma crise):"))
        self._sistema_critico = QLineEdit()
        self._sistema_critico.setStyleSheet(self._le_style())
        lay.addWidget(self._sistema_critico)

        lay.addWidget(self._lbl("Impacto financeiro de 1h de indisponibilidade: (clique aqui)"))
        self._impacto = self._make_combo(
            ["Baixo", "Médio", "Alto", "Crítico"],
            "Selecione o impacto...")
        lay.addWidget(self._impacto)

        self._receita_online = QCheckBox("A receita depende diretamente de aplicações online")
        self._perda_receita  = QCheckBox("Existe perda de receita imediata quando sistemas param")
        for cb in [self._receita_online, self._perda_receita]:
            cb.setStyleSheet(self._cb_style())
            lay.addWidget(cb)
        return w

    # ── Seção 5: Exposição e Infra ────────────────────────────────────────

    def _build_infra(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        self._apps_internet = QCheckBox("Existem aplicações expostas à internet")
        self._clientes_direto = QCheckBox("Clientes acessam sistemas diretamente pela internet")
        for cb in [self._apps_internet, self._clientes_direto]:
            cb.setStyleSheet(self._cb_style())
            lay.addWidget(cb)

        lay.addWidget(self._lbl("Maioria dos sistemas: (clique aqui)"))
        self._exposicao = self._make_combo(
            ["Interna", "Mista", "Pública"],
            "Selecione a exposição...")
        lay.addWidget(self._exposicao)

        lay.addWidget(self._lbl("Infraestrutura utilizada:"))
        infra_w = QWidget()
        infra_l = QHBoxLayout(infra_w)
        infra_l.setContentsMargins(0,0,0,0)
        self._aws = QCheckBox("AWS")
        self._azure = QCheckBox("Azure")
        self._gcp = QCheckBox("GCP")
        self._onprem = QCheckBox("On-Premise")
        for cb in [self._aws, self._azure, self._gcp, self._onprem]:
            cb.setStyleSheet(self._cb_style())
            infra_l.addWidget(cb)
        infra_l.addStretch()
        lay.addWidget(infra_w)

        self._k8s = QCheckBox("Utiliza Kubernetes")
        self._containers = QCheckBox("Utiliza containers")
        self._hibrido = QCheckBox("Possui ambiente híbrido")
        for cb in [self._k8s, self._containers, self._hibrido]:
            cb.setStyleSheet(self._cb_style())
            lay.addWidget(cb)
        return w

    # ── Seção 6: Acesso ───────────────────────────────────────────────────

    def _build_acesso(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._mfa = QCheckBox("Existe MFA para contas administrativas")
        self._pam = QCheckBox("Existe PAM (Privileged Access Management)")
        self._contas_comp = QCheckBox("Existem contas compartilhadas")
        self._fornecedores = QCheckBox("Existem fornecedores com acesso remoto")
        for cb in [self._mfa, self._pam, self._contas_comp, self._fornecedores]:
            cb.setStyleSheet(self._cb_style())
            lay.addWidget(cb)
        return w

    # ── Seção 7: Regulamentações ──────────────────────────────────────────

    def _build_reg(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(self._lbl("Regulamentações que a empresa precisa atender:"))
        reg_w = QWidget()
        reg_l = QHBoxLayout(reg_w)
        reg_l.setContentsMargins(0,0,0,0)
        self._lgpd   = QCheckBox("LGPD")
        self._pci    = QCheckBox("PCI-DSS")
        self._iso    = QCheckBox("ISO 27001")
        self._soc2   = QCheckBox("SOC 2")
        self._hipaa  = QCheckBox("HIPAA")
        self._outro_reg = QCheckBox("Outro")
        for cb in [self._lgpd, self._pci, self._iso, self._soc2, self._hipaa, self._outro_reg]:
            cb.setStyleSheet(self._cb_style())
            reg_l.addWidget(cb)

        self._outro_reg_txt = QLineEdit()
        self._outro_reg_txt.setPlaceholderText("Qual?")
        self._outro_reg_txt.setStyleSheet(self._le_style())
        self._outro_reg_txt.setFixedWidth(160)
        self._outro_reg_txt.setVisible(False)
        reg_l.addWidget(self._outro_reg_txt)
        self._outro_reg.toggled.connect(self._outro_reg_txt.setVisible)

        reg_l.addStretch()
        lay.addWidget(reg_w)

        self._multas = QCheckBox("Uma violação de dados pode gerar multas significativas")
        self._multas.setStyleSheet(self._cb_style())
        lay.addWidget(self._multas)
        return w

    # ── Seção 8: Impacto ao negócio ───────────────────────────────────────

    def _build_negocio(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        campos = [
            ("Quais serviços geram receita diretamente?", "_neg_receita"),
            ("Quais sistemas impactam a experiência do cliente?", "_neg_cliente"),
            ("Quais sistemas causariam maior dano à reputação se comprometidos?", "_neg_reputacao"),
            ("Quais aplicações são consideradas missão crítica?", "_neg_missao"),
        ]
        for label, attr in campos:
            lay.addWidget(self._lbl(label))
            te = QTextEdit()
            te.setFixedHeight(60)
            te.setStyleSheet(self._te_style())
            setattr(self, attr, te)
            lay.addWidget(te)
        return w

    # ── Save / Load ───────────────────────────────────────────────────────

    def _save(self):
        ctx = self._read_form()
        if not ctx.setor:
            QMessageBox.warning(self, "Campo obrigatório", "Selecione o setor da empresa.")
            return
        if ctx.setor == "Outro" and not ctx.setor_outro:
            QMessageBox.warning(self, "Campo obrigatório", "Especifique qual é o setor da empresa.")
            self._setor_outro.setFocus()
            return
        if "Outro" in ctx.regulamentacoes and not ctx.regulamentacao_outro:
            QMessageBox.warning(self, "Campo obrigatório", "Especifique qual regulamentação em 'Outro'.")
            self._outro_reg_txt.setFocus()
            return
        if save(ctx):
            self._ctx = ctx
            self._status_label.setText("✓ Salvo")
            self.context_saved.emit(ctx)
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível salvar o contexto.")

    def _read_form(self) -> CompanyContext:
        regioes = []
        if self._reg_brasil.isChecked(): regioes.append("Brasil")
        if self._reg_latam.isChecked():  regioes.append("América Latina")
        if self._reg_global.isChecked(): regioes.append("Global")

        infra = []
        if self._aws.isChecked():    infra.append("AWS")
        if self._azure.isChecked():  infra.append("Azure")
        if self._gcp.isChecked():    infra.append("GCP")
        if self._onprem.isChecked(): infra.append("On-Premise")

        regs = []
        if self._lgpd.isChecked():     regs.append("LGPD")
        if self._pci.isChecked():      regs.append("PCI-DSS")
        if self._iso.isChecked():      regs.append("ISO 27001")
        if self._soc2.isChecked():     regs.append("SOC 2")
        if self._hipaa.isChecked():    regs.append("HIPAA")
        if self._outro_reg.isChecked(): regs.append("Outro")

        return CompanyContext(
            setor=self._combo_value(self._setor),
            setor_outro=self._setor_outro.text().strip(),
            porte=self._combo_value(self._porte),
            regioes=regioes,
            importancia_disponibilidade=self._slider_disp.value(),
            importancia_confidencialidade=self._slider_conf.value(),
            importancia_integridade=self._slider_intg.value(),
            armazena_pii=self._pii.isChecked(),
            processa_financeiro=self._fin.isChecked(),
            armazena_dados_medicos=self._med.isChecked(),
            possui_propriedade_intelectual=self._pi.isChecked(),
            possui_segredos_industriais=self._seg_ind.isChecked(),
            sistemas_criticos=self._sistemas.toPlainText().strip(),
            sistema_mais_critico=self._sistema_critico.text().strip(),
            impacto_indisponibilidade_1h=self._combo_value(self._impacto),
            receita_depende_apps_online=self._receita_online.isChecked(),
            perda_receita_imediata=self._perda_receita.isChecked(),
            apps_expostas_internet=self._apps_internet.isChecked(),
            clientes_acessam_diretamente=self._clientes_direto.isChecked(),
            exposicao_sistemas=self._combo_value(self._exposicao),
            infraestrutura=infra,
            usa_kubernetes=self._k8s.isChecked(),
            usa_containers=self._containers.isChecked(),
            ambiente_hibrido=self._hibrido.isChecked(),
            mfa_admin=self._mfa.isChecked(),
            possui_pam=self._pam.isChecked(),
            contas_compartilhadas=self._contas_comp.isChecked(),
            fornecedores_acesso_remoto=self._fornecedores.isChecked(),
            regulamentacoes=regs,
            regulamentacao_outro=self._outro_reg_txt.text().strip(),
            violacao_gera_multas=self._multas.isChecked(),
            servicos_geram_receita=self._neg_receita.toPlainText().strip(),
            sistemas_impactam_cliente=self._neg_cliente.toPlainText().strip(),
            sistemas_dano_reputacao=self._neg_reputacao.toPlainText().strip(),
            apps_missao_critica=self._neg_missao.toPlainText().strip(),
        )

    def _populate(self, ctx: CompanyContext):
        """Preenche o formulário com dados salvos."""
        idx = self._setor.findText(ctx.setor)
        if idx >= 0: self._setor.setCurrentIndex(idx)
        self._setor_outro.setText(ctx.setor_outro)
        self._setor_outro.setVisible(ctx.setor == "Outro")
        idx = self._porte.findText(ctx.porte)
        if idx >= 0: self._porte.setCurrentIndex(idx)

        self._reg_brasil.setChecked("Brasil" in ctx.regioes)
        self._reg_latam.setChecked("América Latina" in ctx.regioes)
        self._reg_global.setChecked("Global" in ctx.regioes)

        self._slider_disp.setValue(ctx.importancia_disponibilidade)
        self._slider_conf.setValue(ctx.importancia_confidencialidade)
        self._slider_intg.setValue(ctx.importancia_integridade)

        self._pii.setChecked(ctx.armazena_pii)
        self._fin.setChecked(ctx.processa_financeiro)
        self._med.setChecked(ctx.armazena_dados_medicos)
        self._pi.setChecked(ctx.possui_propriedade_intelectual)
        self._seg_ind.setChecked(ctx.possui_segredos_industriais)

        self._sistemas.setPlainText(ctx.sistemas_criticos)
        self._sistema_critico.setText(ctx.sistema_mais_critico)
        idx = self._impacto.findText(ctx.impacto_indisponibilidade_1h)
        if idx >= 0: self._impacto.setCurrentIndex(idx)
        self._receita_online.setChecked(ctx.receita_depende_apps_online)
        self._perda_receita.setChecked(ctx.perda_receita_imediata)

        self._apps_internet.setChecked(ctx.apps_expostas_internet)
        self._clientes_direto.setChecked(ctx.clientes_acessam_diretamente)
        idx = self._exposicao.findText(ctx.exposicao_sistemas)
        if idx >= 0: self._exposicao.setCurrentIndex(idx)

        self._aws.setChecked("AWS" in ctx.infraestrutura)
        self._azure.setChecked("Azure" in ctx.infraestrutura)
        self._gcp.setChecked("GCP" in ctx.infraestrutura)
        self._onprem.setChecked("On-Premise" in ctx.infraestrutura)
        self._k8s.setChecked(ctx.usa_kubernetes)
        self._containers.setChecked(ctx.usa_containers)
        self._hibrido.setChecked(ctx.ambiente_hibrido)

        self._mfa.setChecked(ctx.mfa_admin)
        self._pam.setChecked(ctx.possui_pam)
        self._contas_comp.setChecked(ctx.contas_compartilhadas)
        self._fornecedores.setChecked(ctx.fornecedores_acesso_remoto)

        self._lgpd.setChecked("LGPD" in ctx.regulamentacoes)
        self._pci.setChecked("PCI-DSS" in ctx.regulamentacoes)
        self._iso.setChecked("ISO 27001" in ctx.regulamentacoes)
        self._soc2.setChecked("SOC 2" in ctx.regulamentacoes)
        self._hipaa.setChecked("HIPAA" in ctx.regulamentacoes)
        self._outro_reg.setChecked("Outro" in ctx.regulamentacoes)
        self._outro_reg_txt.setText(ctx.regulamentacao_outro)
        self._outro_reg_txt.setVisible(self._outro_reg.isChecked())
        self._multas.setChecked(ctx.violacao_gera_multas)

        self._neg_receita.setPlainText(ctx.servicos_geram_receita)
        self._neg_cliente.setPlainText(ctx.sistemas_impactam_cliente)
        self._neg_reputacao.setPlainText(ctx.sistemas_dano_reputacao)
        self._neg_missao.setPlainText(ctx.apps_missao_critica)

        if ctx.preenchido:
            self._status_label.setText("✓ Contexto carregado")
            self._status_label.setStyleSheet(f"color:{theme.AI_ACCENT}; font-size:11px; font-family:monospace; border:none;")

    def get_context(self) -> CompanyContext:
        return self._ctx

    # ── Estilos ───────────────────────────────────────────────────────────

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; font-size:12px;")
        l.setWordWrap(True)
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
            QComboBox QAbstractItemView::item:disabled {{
                color:{theme.TEXT_FAINT}; font-style:italic;
            }}
        """

    def _te_style(self) -> str:
        return f"""
            QTextEdit {{ background:{theme.BG_INPUT}; color:{theme.TEXT_PRIMARY}; border:1px solid {theme.BORDER};
                border-radius:6px; padding:6px; font-size:12px; }}
        """

    def _le_style(self) -> str:
        return f"""
            QLineEdit {{ background:{theme.BG_INPUT}; color:{theme.TEXT_PRIMARY}; border:1px solid {theme.BORDER};
                border-radius:6px; padding:6px 10px; font-size:12px; }}
        """

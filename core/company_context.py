"""
core/company_context.py
Modelo e persistência do contexto da empresa.
Salvo em data/company_context.json — carregado automaticamente na inicialização.
"""
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

if getattr(sys, "frozen", False):
    # Empacotado (.exe): salva em %APPDATA%\SentinelAI, pasta persistente do
    # usuário — a pasta do executável/instalação não deve ser usada para
    # gravação (fica em Program Files, ou é uma extração temporária do PyInstaller).
    _DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "SentinelAI"
else:
    _DATA_DIR = Path(__file__).parent.parent / "data"

CONTEXT_FILE = _DATA_DIR / "company_context.json"


@dataclass
class CompanyContext:
    # 1. Perfil
    setor: str = ""                        # Financeiro, Saúde, Governo...
    setor_outro: str = ""                  # detalhe quando setor == "Outro"
    porte: str = ""                        # Pequena, Média, Grande, Enterprise
    regioes: list[str] = field(default_factory=list)  # Brasil, América Latina, Global

    # 2. Prioridades de negócio (0-10)
    importancia_disponibilidade: int = 5
    importancia_confidencialidade: int = 5
    importancia_integridade: int = 5

    # 3. Dados sensíveis
    armazena_pii: bool = False
    processa_financeiro: bool = False
    armazena_dados_medicos: bool = False
    possui_propriedade_intelectual: bool = False
    possui_segredos_industriais: bool = False

    # 4. Sistemas críticos
    sistemas_criticos: str = ""            # lista livre
    sistema_mais_critico: str = ""
    impacto_indisponibilidade_1h: str = ""  # Baixo, Médio, Alto, Crítico
    receita_depende_apps_online: bool = False
    perda_receita_imediata: bool = False

    # 5. Exposição
    apps_expostas_internet: bool = False
    clientes_acessam_diretamente: bool = False
    exposicao_sistemas: str = ""           # Interna, Mista, Pública

    # 6. Infraestrutura
    infraestrutura: list[str] = field(default_factory=list)  # AWS, Azure, GCP, On-Premise
    usa_kubernetes: bool = False
    usa_containers: bool = False
    ambiente_hibrido: bool = False

    # 7. Controles de acesso
    mfa_admin: bool = False
    possui_pam: bool = False
    contas_compartilhadas: bool = False
    fornecedores_acesso_remoto: bool = False

    # 8. Regulamentações
    regulamentacoes: list[str] = field(default_factory=list)  # LGPD, PCI-DSS...
    regulamentacao_outro: str = ""         # detalhe quando "Outro" está em regulamentacoes
    violacao_gera_multas: bool = False

    # 9. Impacto ao negócio
    servicos_geram_receita: str = ""
    sistemas_impactam_cliente: str = ""
    sistemas_dano_reputacao: str = ""
    apps_missao_critica: str = ""

    @property
    def preenchido(self) -> bool:
        """Retorna True se o contexto tem pelo menos o setor preenchido."""
        return bool(self.setor)

    def to_prompt_text(self) -> str:
        """Converte o contexto para texto descritivo para injetar no prompt da IA."""
        lines = ["CONTEXTO DA EMPRESA:"]

        if self.setor:
            setor_txt = self.setor
            if self.setor == "Outro" and self.setor_outro:
                setor_txt = f"Outro ({self.setor_outro})"
            lines.append(f"- Setor: {setor_txt}")
        if self.porte:
            lines.append(f"- Porte: {self.porte}")
        if self.regioes:
            lines.append(f"- Regiões de operação: {', '.join(self.regioes)}")

        lines.append(f"\nPRIORIDADES DE NEGÓCIO (escala 0-10):")
        lines.append(f"- Disponibilidade: {self.importancia_disponibilidade}/10")
        lines.append(f"- Confidencialidade: {self.importancia_confidencialidade}/10")
        lines.append(f"- Integridade: {self.importancia_integridade}/10")

        dados = []
        if self.armazena_pii: dados.append("dados pessoais (PII)")
        if self.processa_financeiro: dados.append("dados financeiros")
        if self.armazena_dados_medicos: dados.append("informações médicas")
        if self.possui_propriedade_intelectual: dados.append("propriedade intelectual")
        if self.possui_segredos_industriais: dados.append("segredos industriais")
        if dados:
            lines.append(f"\nDADOS SENSÍVEIS: {', '.join(dados)}")

        if self.sistemas_criticos:
            lines.append(f"\nSISTEMAS CRÍTICOS:\n{self.sistemas_criticos}")
        if self.sistema_mais_critico:
            lines.append(f"Sistema mais crítico: {self.sistema_mais_critico}")
        if self.impacto_indisponibilidade_1h:
            lines.append(f"Impacto de 1h de indisponibilidade: {self.impacto_indisponibilidade_1h}")
        if self.receita_depende_apps_online:
            lines.append("A receita depende diretamente de aplicações online.")
        if self.perda_receita_imediata:
            lines.append("Existe perda de receita imediata quando sistemas param.")

        exposicao = []
        if self.apps_expostas_internet: exposicao.append("apps expostas à internet")
        if self.clientes_acessam_diretamente: exposicao.append("clientes acessam sistemas diretamente")
        if self.exposicao_sistemas: exposicao.append(f"sistemas {self.exposicao_sistemas.lower()}")
        if exposicao:
            lines.append(f"\nEXPOSIÇÃO: {', '.join(exposicao)}")

        if self.infraestrutura:
            lines.append(f"\nINFRAESTRUTURA: {', '.join(self.infraestrutura)}")
        infra_extras = []
        if self.usa_kubernetes: infra_extras.append("Kubernetes")
        if self.usa_containers: infra_extras.append("containers")
        if self.ambiente_hibrido: infra_extras.append("ambiente híbrido")
        if infra_extras:
            lines.append(f"Tecnologias: {', '.join(infra_extras)}")

        controles = []
        if self.mfa_admin: controles.append("MFA para admins")
        if self.possui_pam: controles.append("PAM")
        if self.contas_compartilhadas: controles.append("ATENÇÃO: contas compartilhadas existem")
        if self.fornecedores_acesso_remoto: controles.append("fornecedores com acesso remoto")
        if controles:
            lines.append(f"\nCONTROLES DE ACESSO: {', '.join(controles)}")

        if self.regulamentacoes:
            regs_txt = self.regulamentacoes
            if "Outro" in regs_txt and self.regulamentacao_outro:
                regs_txt = [f"Outro ({self.regulamentacao_outro})" if r == "Outro" else r for r in regs_txt]
            lines.append(f"\nREGULAMENTAÇÕES: {', '.join(regs_txt)}")
        if self.violacao_gera_multas:
            lines.append("Uma violação de dados pode gerar multas significativas.")

        negocio = []
        if self.servicos_geram_receita:
            negocio.append(f"Serviços que geram receita: {self.servicos_geram_receita}")
        if self.sistemas_impactam_cliente:
            negocio.append(f"Sistemas que impactam clientes: {self.sistemas_impactam_cliente}")
        if self.sistemas_dano_reputacao:
            negocio.append(f"Sistemas de alto risco reputacional: {self.sistemas_dano_reputacao}")
        if self.apps_missao_critica:
            negocio.append(f"Apps missão crítica: {self.apps_missao_critica}")
        if negocio:
            lines.append(f"\nIMPACTO AO NEGÓCIO:")
            lines.extend(negocio)

        return "\n".join(lines)


def load() -> CompanyContext:
    """Carrega o contexto do arquivo JSON. Retorna contexto vazio se não existir."""
    try:
        if CONTEXT_FILE.exists():
            with open(CONTEXT_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return CompanyContext(**data)
    except Exception as e:
        print(f"[context] Erro ao carregar: {e}")
    return CompanyContext()


def save(ctx: CompanyContext) -> bool:
    """Salva o contexto em JSON. Retorna True se sucesso."""
    try:
        CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(ctx), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[context] Erro ao salvar: {e}")
        return False

"""
core/coverage.py
Responde a uma pergunta que o score sozinho não responde: "este tipo de
scan chegou a ser executado?"

Por que isso existe
-------------------
O scorer devolve 0 para um tipo de scan sem nenhuma vulnerabilidade aberta.
Só que 0 pode significar duas coisas MUITO diferentes:

    a) "rodei DAST e não encontrei nada"        -> ótima notícia
    b) "nunca rodei DAST"                       -> nenhuma notícia

Antes deste módulo, o Dashboard pintava as duas situações do mesmo jeito:
anel verde com 0. Ou seja, a ASPM afirmava cobertura que não tinha — o
pior tipo de erro numa ferramenta de postura de segurança, porque
tranquiliza sem base.

Como a cobertura é inferida
---------------------------
Pelas FERRAMENTAS cujos relatórios foram importados, não pelos achados.
Se o Trivy rodou e não achou nenhuma má configuração de IaC, IaC continua
coberto (e com risco 0 de verdade) — inferir pelos achados faria esse caso
voltar a parecer "não escaneado".
"""
from core.models import ScanReport

#: O que cada ferramenta é capaz de cobrir. Uma ferramenta que rodou cobre
#: TODOS os tipos desta lista, mesmo que não tenha achado nada em algum
#: deles — foi justamente isso que ela foi lá verificar.
TOOL_SCAN_TYPES: dict[str, set[str]] = {
    "semgrep":  {"SAST"},
    "zap":      {"DAST"},
    "snyk":     {"SCA"},
    "gitleaks": {"SECRETS"},
    # O Trivy é multi-estágio: uma execução cobre imagem, IaC e segredos.
    "trivy":    {"CONTAINER", "IAC", "SECRETS"},
}


def covered_scan_types(reports: list[ScanReport]) -> set[str]:
    """Tipos de scan efetivamente cobertos pelos relatórios importados.

    Conjunto vazio = nada foi importado ainda (o Dashboard usa isso para
    mostrar o estado inicial em vez de um painel de zeros)."""
    covered: set[str] = set()
    for report in reports:
        covered |= TOOL_SCAN_TYPES.get(report.tool, set())
        # Ferramenta desconhecida (parser novo que ainda não está no mapa):
        # cai no tipo declarado pelo próprio relatório, para não sumir da tela.
        if report.tool not in TOOL_SCAN_TYPES:
            covered.add(report.scan_type.value)
    return covered


def uncovered_scan_types(reports: list[ScanReport], known: list[str]) -> list[str]:
    """Tipos que aparecem na UI mas que ninguém escaneou — usado para dizer
    ao usuário o que ainda falta, em vez de deixar o vazio passar por 'ok'."""
    covered = covered_scan_types(reports)
    return [t for t in known if t not in covered]

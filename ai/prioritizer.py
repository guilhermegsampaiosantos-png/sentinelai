"""
ai/prioritizer.py
Função 2 — Priorização inteligente de vulnerabilidades com contexto de negócio.
"""
from dataclasses import dataclass, field
from ai.provider import LLMProvider
from core.models import Vulnerability, Severity, ScanType
from core.company_context import CompanyContext
from core.asset import Asset

SYSTEM_PROMPT = """Você é um analista sênior de segurança de aplicações (AppSec).
Sua função é priorizar vulnerabilidades para times de desenvolvimento com base em
risco real, exploitabilidade e impacto ao negócio — considerando o contexto
específico da empresa fornecido.
Responda sempre em português brasileiro e em formato JSON válido.
Quando uma vulnerabilidade tiver o campo "asset" preenchido, considere a
exposição daquele ativo específico (internet_facing, critical_asset,
contains_sensitive_data, customer_facing) como fator de risco tão ou mais
importante que a severidade técnica isolada."""

SEV_SCORE  = {Severity.CRITICAL: 40, Severity.HIGH: 25, Severity.MEDIUM: 10, Severity.LOW: 3, Severity.INFO: 0}
TYPE_SCORE = {ScanType.SECRETS: 20, ScanType.DAST: 15, ScanType.SAST: 10, ScanType.SCA: 8}
CVSS_WEIGHT = 2.5


@dataclass
class ScoreComponent:
    """Uma parcela nomeada do pre_score — permite mostrar o cálculo de forma
    transparente na UI (ex.: 'CVSS: +18.0', 'Setor Financeiro (contexto): +5')."""
    label: str
    value: float


@dataclass
class PrioritizedVuln:
    vuln: Vulnerability
    pre_score: float
    ai_rank: int | None
    ai_reason: str
    final_score: float
    score_breakdown: list[ScoreComponent] = field(default_factory=list)
    ai_reason_summary: str = ""   # resumo de 1 linha — mostrado sempre visível na UI,
                                   # com ai_reason (o parágrafo completo) atrás de "ver detalhes"


_SEV_LABEL_PT = {
    Severity.CRITICAL: "crítica", Severity.HIGH: "alta",
    Severity.MEDIUM: "média", Severity.LOW: "baixa", Severity.INFO: "informativa",
}

_SUMMARY_TYPE_PT = {
    ScanType.SECRETS:   "Segredo exposto",
    ScanType.DAST:       "Falha explorável remotamente",
    ScanType.SAST:       "Falha no código-fonte",
    ScanType.SCA:        "Dependência vulnerável",
    ScanType.CONTAINER:  "Vulnerabilidade na imagem do container",
    ScanType.IAC:        "Infraestrutura mal configurada",
}


def _build_summary_line(vuln: Vulnerability, ctx: CompanyContext | None = None,
                         asset: Asset | None = None) -> str:
    """Resumo de 1 linha pra "bater o olho": o tipo técnico + o único fator de
    negócio/ativo mais forte, se houver. Deliberadamente curto — o raciocínio
    completo continua em _build_fallback_reason()/ai_reason, só que atrás de
    'ver detalhes' na UI."""
    parts = [_SUMMARY_TYPE_PT.get(vuln.scan_type, "Vulnerabilidade identificada")]

    highlight = None
    if asset:
        if asset.internet_facing and asset.critical_asset:
            highlight = f"ativo crítico exposto à internet ({asset.label})"
        elif asset.internet_facing:
            highlight = f"ativo exposto à internet ({asset.label})"
        elif asset.critical_asset:
            highlight = f"ativo crítico ({asset.label})"
        elif asset.contains_sensitive_data:
            highlight = f"ativo com dados sensíveis ({asset.label})"
    if not highlight and ctx and ctx.preenchido:
        if ctx.setor in ("Financeiro", "Saúde", "Governo") and vuln.severity in (Severity.CRITICAL, Severity.HIGH):
            highlight = f"setor {ctx.setor}"
        elif ctx.armazena_pii and "LGPD" in ctx.regulamentacoes and vuln.scan_type == ScanType.SECRETS:
            highlight = "dados pessoais sob LGPD"

    if highlight:
        parts.append(highlight)
    return " — ".join(parts)


def pre_score_breakdown(vuln: Vulnerability, ctx: CompanyContext | None = None,
                         asset: Asset | None = None) -> list[ScoreComponent]:
    """Mesma lógica que antes vivia só dentro de pre_score(), mas agora cada
    parcela é mantida separada e nomeada — é o que a UI usa para mostrar
    'por que essa vulnerabilidade virou prioridade'."""
    components: list[ScoreComponent] = []

    sev_val = SEV_SCORE.get(vuln.severity, 0)
    components.append(ScoreComponent(f"Severidade base ({_SEV_LABEL_PT.get(vuln.severity, vuln.severity.value)})", sev_val))

    type_val = TYPE_SCORE.get(vuln.scan_type, 0)
    if type_val:
        components.append(ScoreComponent(f"Tipo de scan ({vuln.scan_type.value})", type_val))

    if vuln.cvss_score:
        components.append(ScoreComponent(f"CVSS ({vuln.cvss_score})", round(vuln.cvss_score * CVSS_WEIGHT, 1)))

    if vuln.scan_type == ScanType.SECRETS:
        components.append(ScoreComponent("Segredo exposto", 15))

    # Ajustes de contexto no pre-score
    if ctx and ctx.preenchido:
        # Confidencialidade alta → secrets e SCA sobem
        if ctx.importancia_confidencialidade >= 8 and vuln.scan_type in (ScanType.SECRETS, ScanType.SCA):
            components.append(ScoreComponent("Confidencialidade prioritária (contexto)", 8))
        # Disponibilidade alta → DAST sobe
        if ctx.importancia_disponibilidade >= 8 and vuln.scan_type == ScanType.DAST:
            components.append(ScoreComponent("Disponibilidade prioritária (contexto)", 8))
        # Setor financeiro/saúde/governo → criticidade geral maior
        if ctx.setor in ("Financeiro", "Saúde", "Governo") and vuln.severity in (Severity.CRITICAL, Severity.HIGH):
            components.append(ScoreComponent(f"Setor {ctx.setor} (contexto)", 5))
        # LGPD/PCI → PII e dados financeiros têm peso maior
        if ctx.armazena_pii and "LGPD" in ctx.regulamentacoes and vuln.scan_type == ScanType.SECRETS:
            components.append(ScoreComponent("PII sob LGPD (contexto)", 5))

    # Ajustes de contexto POR ATIVO — mais específico que o contexto global da
    # empresa: reflete a exposição real do sistema onde essa vulnerabilidade
    # foi encontrada, não a empresa como um todo.
    if asset:
        if asset.internet_facing:
            components.append(ScoreComponent(f"Ativo internet-facing ({asset.label})", 10))
        if asset.critical_asset:
            components.append(ScoreComponent(f"Ativo crítico ({asset.label})", 8))
        if asset.contains_sensitive_data and vuln.scan_type in (ScanType.SECRETS, ScanType.SCA, ScanType.DAST):
            components.append(ScoreComponent(f"Ativo com dados sensíveis ({asset.label})", 8))
        if asset.customer_facing and vuln.severity in (Severity.CRITICAL, Severity.HIGH):
            components.append(ScoreComponent(f"Ativo customer-facing ({asset.label})", 5))

    return components


def pre_score(vuln: Vulnerability, ctx: CompanyContext | None = None,
              asset: Asset | None = None) -> float:
    """Score determinístico — ajustado pelo contexto da empresa e do ativo quando
    disponíveis. Soma as parcelas de pre_score_breakdown() e aplica o teto de 100."""
    total = sum(c.value for c in pre_score_breakdown(vuln, ctx, asset))
    return min(total, 100.0)


_TYPE_DESCRIPTION = {
    ScanType.SECRETS: "um segredo exposto no código ou repositório",
    ScanType.DAST: "uma falha explorável remotamente, direto pela aplicação em execução",
    ScanType.SAST: "uma falha identificada diretamente no código-fonte",
    ScanType.SCA: "uma dependência de terceiros com vulnerabilidade conhecida",
    ScanType.CONTAINER: "uma vulnerabilidade em pacote do sistema operacional dentro de uma imagem de container",
    ScanType.IAC: "uma má configuração em arquivo de infraestrutura como código (Dockerfile, Kubernetes, Terraform)",
}

_TYPE_RISK = {
    ScanType.SECRETS: "Segredos expostos dão acesso direto a sistemas e dados sem precisar explorar nenhuma outra falha, o que os torna fáceis de abusar assim que alguém os encontra.",
    ScanType.DAST: "Por ser explorável remotamente, um invasor pode tentar essa falha direto pela internet, sem precisar de acesso prévio ao ambiente.",
    ScanType.SAST: "Por estar no código-fonte, esse tipo de falha costuma se repetir em outros pontos do sistema que seguem o mesmo padrão, o que amplia o impacto real.",
    ScanType.SCA: "Dependências vulneráveis costumam ter exploits públicos já documentados, o que reduz bastante o esforço necessário para um ataque.",
    ScanType.CONTAINER: "Uma imagem vulnerável se propaga para todo container criado a partir dela, então o impacto tende a se repetir em cada ambiente onde essa imagem for implantada.",
    ScanType.IAC: "Más configurações de infraestrutura costumam abrir uma porta de entrada estrutural (ex.: privilégios excessivos, rede exposta) que facilita ou amplia outros ataques.",
}

_URGENCY_BY_SEVERITY = {
    Severity.CRITICAL: "Recomenda-se correção imediata, antes de qualquer outra tarefa de desenvolvimento.",
    Severity.HIGH: "Recomenda-se corrigir na próxima janela de deploy disponível.",
    Severity.MEDIUM: "Pode entrar no planejamento normal da sprint, sem precisar de correção emergencial.",
    Severity.LOW: "Baixa urgência — pode ficar no backlog de melhorias técnicas.",
    Severity.INFO: "Caráter informativo — avaliar se vale a pena corrigir junto de outras tarefas do mesmo módulo.",
}


def _build_fallback_reason(vuln: Vulnerability, ctx: CompanyContext | None, in_top: bool,
                            asset: Asset | None = None) -> str:
    """Monta uma justificativa em várias frases, com o raciocínio por trás do
    score (fator técnico + risco + contexto de negócio + ativo + recomendação).
    Usada quando a IA não está disponível (ou o item não veio na resposta do LLM)."""
    sev_label = {
        Severity.CRITICAL: "severidade crítica", Severity.HIGH: "severidade alta",
        Severity.MEDIUM: "severidade média", Severity.LOW: "severidade baixa",
        Severity.INFO: "severidade informativa",
    }.get(vuln.severity, "severidade não classificada")
    tipo_desc = _TYPE_DESCRIPTION.get(vuln.scan_type, "uma vulnerabilidade identificada na aplicação")

    frase1 = f"Vulnerabilidade de {sev_label}: trata-se de {tipo_desc}"
    if vuln.cvss_score:
        frase1 += f", com CVSS {vuln.cvss_score}"
    frase1 += "."

    frases = [frase1]

    risco = _TYPE_RISK.get(vuln.scan_type)
    if risco:
        frases.append(risco)

    motivos_negocio = []
    if ctx and ctx.preenchido:
        if ctx.importancia_confidencialidade >= 8 and vuln.scan_type in (ScanType.SECRETS, ScanType.SCA):
            motivos_negocio.append("a empresa declarou confidencialidade dos dados como prioridade alta")
        if ctx.importancia_disponibilidade >= 8 and vuln.scan_type == ScanType.DAST:
            motivos_negocio.append("a empresa declarou disponibilidade dos sistemas como prioridade alta")
        if ctx.setor in ("Financeiro", "Saúde", "Governo") and vuln.severity in (Severity.CRITICAL, Severity.HIGH):
            motivos_negocio.append(f"o setor {ctx.setor} costuma ter exigências regulatórias e reputacionais mais rígidas")
        if ctx.armazena_pii and "LGPD" in ctx.regulamentacoes and vuln.scan_type == ScanType.SECRETS:
            motivos_negocio.append("há dados pessoais em jogo sob LGPD, o que aumenta o risco legal de um vazamento")
    if motivos_negocio:
        frases.append("No contexto informado da empresa, " + "; ".join(motivos_negocio) + ".")

    motivos_ativo = []
    if asset:
        if asset.internet_facing:
            motivos_ativo.append(f"o ativo \"{asset.label}\" está exposto à internet")
        if asset.critical_asset:
            motivos_ativo.append("é um ativo marcado como crítico para a operação")
        if asset.contains_sensitive_data:
            motivos_ativo.append("esse ativo armazena ou processa dados sensíveis")
        if asset.customer_facing:
            motivos_ativo.append("é um ativo diretamente acessado por clientes")
    if motivos_ativo:
        frases.append("Sobre o ativo afetado: " + "; ".join(motivos_ativo) + ".")

    if in_top:
        frases.append(_URGENCY_BY_SEVERITY.get(vuln.severity, ""))
    else:
        frases.append("Não entrou entre os itens de prioridade máxima analisados pela IA nesta rodada, mas ainda deve ser corrigida dentro do ciclo normal de desenvolvimento.")

    return " ".join(f for f in frases if f)


def prioritize(
    vulns: list[Vulnerability],
    provider: LLMProvider,
    ctx: CompanyContext | None = None,
    assets: dict[str, Asset] | None = None,
    top_n: int = 10,
) -> list[PrioritizedVuln]:
    if not vulns:
        return []
    assets = assets or {}

    def _asset_of(v: Vulnerability) -> Asset | None:
        return assets.get(v.asset_id) if v.asset_id else None

    # Calcula o breakdown uma única vez por vuln — pre_score() deriva o total
    # da mesma lista, então não duplicamos a lógica de pontuação.
    breakdowns = {v.id: pre_score_breakdown(v, ctx, _asset_of(v)) for v in vulns}
    scored = [(v, min(sum(c.value for c in breakdowns[v.id]), 100.0)) for v in vulns]
    scored.sort(key=lambda x: x[1], reverse=True)

    top  = scored[:top_n]
    rest = scored[top_n:]

    ai_results: dict[str, tuple[int, str]] = {}
    if provider.available:
        ai_results = _llm_rerank(top, provider, ctx, assets)

    result: list[PrioritizedVuln] = []
    for i, (vuln, ps) in enumerate(top):
        default = (i + 1, _build_fallback_reason(vuln, ctx, in_top=True, asset=_asset_of(vuln)))
        ai_rank, ai_reason = ai_results.get(vuln.id, default)
        ai_weight = max(0, (top_n - ai_rank + 1) / top_n * 100)
        final = round(ps * 0.7 + ai_weight * 0.3, 1)
        summary = _build_summary_line(vuln, ctx, _asset_of(vuln))
        result.append(PrioritizedVuln(vuln=vuln, pre_score=ps, ai_rank=ai_rank,
                                      ai_reason=ai_reason, final_score=final,
                                      score_breakdown=breakdowns[vuln.id],
                                      ai_reason_summary=summary))

    for vuln, ps in rest:
        reason = _build_fallback_reason(vuln, ctx, in_top=False, asset=_asset_of(vuln))
        summary = _build_summary_line(vuln, ctx, _asset_of(vuln))
        result.append(PrioritizedVuln(vuln=vuln, pre_score=ps, ai_rank=None,
                                      ai_reason=reason, final_score=ps,
                                      score_breakdown=breakdowns[vuln.id],
                                      ai_reason_summary=summary))

    result.sort(key=lambda x: x.final_score, reverse=True)
    return result


def _llm_rerank(
    scored: list[tuple[Vulnerability, float]],
    provider: LLMProvider,
    ctx: CompanyContext | None = None,
    assets: dict[str, Asset] | None = None,
) -> dict[str, tuple[int, str]]:
    import json
    assets = assets or {}

    vuln_list = []
    for i, (v, ps) in enumerate(scored):
        asset = assets.get(v.asset_id) if v.asset_id else None
        vuln_list.append({
            "index": i,
            "id": v.id,
            "title": v.title,
            "severity": v.severity.value,
            "type": v.scan_type.value,
            "tool": v.tool,
            "file": v.file_path or v.url or "",
            "cve": v.cve_id or "",
            "cvss": v.cvss_score,
            "pre_score": ps,
            "asset": ({
                "name": asset.label,
                "environment": asset.environment,
                "internet_facing": asset.internet_facing,
                "critical_asset": asset.critical_asset,
                "contains_sensitive_data": asset.contains_sensitive_data,
                "customer_facing": asset.customer_facing,
            } if asset else None),
        })

    # Injeta contexto da empresa no prompt se disponível
    context_block = ""
    if ctx and ctx.preenchido:
        context_block = f"""
{ctx.to_prompt_text()}

Com base nesse contexto empresarial, considere:
- Vulnerabilidades em sistemas de missão crítica têm peso maior
- O setor {ctx.setor} tem requisitos regulatórios específicos
- Disponibilidade ({ctx.importancia_disponibilidade}/10), Confidencialidade ({ctx.importancia_confidencialidade}/10) e Integridade ({ctx.importancia_integridade}/10) são as prioridades declaradas
- Prefira corrigir primeiro o que impacta diretamente os sistemas que geram receita
"""
    else:
        context_block = "\n(Contexto da empresa não configurado — usando critérios técnicos padrão)\n"

    prompt = f"""Você recebeu vulnerabilidades detectadas em uma aplicação.
Re-ordene-as da mais urgente para a menos urgente considerando o contexto abaixo.
{context_block}
Vulnerabilidades:
{json.dumps(vuln_list, ensure_ascii=False, indent=2)}

Responda APENAS com JSON válido, sem texto antes ou depois:
{{
  "ranking": [
    {{
      "id": "<id da vuln>",
      "rank": 1,
      "reason": "Explique em 2 a 4 frases o raciocínio por trás dessa posição: (1) o principal fator técnico (severidade, tipo de falha, CVSS), (2) por que isso é ou não fácil de explorar / qual o risco concreto, (3) se o contexto da empresa foi informado, cite o motivo de negócio específico que pesou na decisão, e (4) uma recomendação objetiva de urgência (ex: corrigir imediatamente, próxima sprint, backlog)."
    }}
  ]
}}"""

    try:
        response = provider.chat(prompt, system=SYSTEM_PROMPT, timeout=90)
        text = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        return {item["id"]: (item["rank"], item["reason"]) for item in data.get("ranking", [])}
    except Exception as e:
        print(f"[prioritizer] LLM rerank falhou: {e}")
        return {}


"""
ai/anomaly_detector.py
Função 3 — Detecção de padrões e anomalias entre relatórios.

Analisa o conjunto de vulnerabilidades em busca de:
  - Padrões recorrentes (mesma categoria aparece em muitos arquivos)
  - Concentração de risco em componentes específicos
  - Anomalias estatísticas (pico de vulns em uma área)
  - Correlações suspeitas (ex: secrets + SQL injection no mesmo módulo)

Usa heurísticas locais + LLM para interpretação.
"""
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from ai.provider import LLMProvider, LLMResponse
from core.models import Vulnerability, Severity, ScanType

SYSTEM_PROMPT = """Você é um especialista em análise de segurança de aplicações.
Analise padrões em dados de vulnerabilidades e identifique anomalias, concentrações
de risco e padrões preocupantes. Responda em português brasileiro de forma clara e direta."""


@dataclass
class AnomalyReport:
    """Resultado da análise de anomalias."""
    patterns: list[str] = field(default_factory=list)      # padrões detectados localmente
    hotspots: list[str] = field(default_factory=list)      # arquivos/módulos com mais risco
    correlations: list[str] = field(default_factory=list)  # correlações suspeitas
    ai_analysis: str = ""                                   # análise narrativa do LLM
    risk_map: dict = field(default_factory=dict)           # mapa arquivo → contagem de vulns


def detect(vulns: list[Vulnerability], provider: LLMProvider) -> AnomalyReport:
    """
    Detecta padrões e anomalias. Sempre retorna resultado mesmo sem LLM.
    """
    if not vulns:
        return AnomalyReport(ai_analysis="Nenhuma vulnerabilidade para analisar.")

    report = AnomalyReport()

    # ── Análise local (determinística) ──────────────────────────────────
    report.patterns   = _find_patterns(vulns)
    report.hotspots   = _find_hotspots(vulns)
    report.correlations = _find_correlations(vulns)
    report.risk_map   = _build_risk_map(vulns)

    # ── Análise do LLM ──────────────────────────────────────────────────
    if provider.available:
        report.ai_analysis = _llm_analysis(vulns, report, provider)
    else:
        report.ai_analysis = _local_narrative(report)

    return report


# ── Heurísticas locais ───────────────────────────────────────────────────

def _find_patterns(vulns: list[Vulnerability]) -> list[str]:
    patterns = []

    # Padrão 1: tipo de vuln dominante
    title_words = Counter()
    for v in vulns:
        for word in v.title.lower().split():
            if len(word) > 4:
                title_words[word] += 1
    top_word, top_count = title_words.most_common(1)[0] if title_words else ("", 0)
    if top_count >= 3:
        patterns.append(f"Padrão recorrente: '{top_word}' aparece em {top_count} vulnerabilidades — provável problema sistêmico.")

    # Padrão 2: concentração por ferramenta
    tool_counts = Counter(v.tool for v in vulns)
    dominant_tool, dominant_count = tool_counts.most_common(1)[0]
    pct = dominant_count / len(vulns) * 100
    if pct > 60:
        patterns.append(f"{dominant_tool.upper()} responde por {pct:.0f}% das vulnerabilidades — considere revisar as regras ou a cobertura das outras ferramentas.")

    # Padrão 3: muitas críticas em proporção
    critical_count = sum(1 for v in vulns if v.severity == Severity.CRITICAL)
    if critical_count / len(vulns) > 0.15:
        patterns.append(f"Alta proporção de críticas: {critical_count}/{len(vulns)} ({critical_count/len(vulns)*100:.0f}%) — situação fora do normal.")

    # Padrão 4: secrets com muitas ocorrências
    secrets = [v for v in vulns if v.scan_type == ScanType.SECRETS]
    if len(secrets) >= 3:
        patterns.append(f"{len(secrets)} segredos expostos detectados — possível cultura de hardcoded credentials no projeto.")

    return patterns


def _find_hotspots(vulns: list[Vulnerability]) -> list[str]:
    """Arquivos/módulos com mais vulnerabilidades."""
    file_counts: Counter = Counter()
    file_severity: dict[str, list] = defaultdict(list)

    for v in vulns:
        key = v.file_path or v.url or "desconhecido"
        # Agrupa por módulo (primeiros 2 segmentos do path)
        parts = key.replace("\\", "/").split("/")
        module = "/".join(parts[:2]) if len(parts) > 1 else key
        file_counts[module] += 1
        file_severity[module].append(v.severity.value)

    hotspots = []
    for module, count in file_counts.most_common(5):
        if count >= 2:
            sev_summary = Counter(file_severity[module])
            worst = "critical" if "critical" in sev_summary else "high" if "high" in sev_summary else "medium"
            hotspots.append(f"{module} → {count} vulnerabilidades (pior: {worst.upper()})")

    return hotspots


def _find_correlations(vulns: list[Vulnerability]) -> list[str]:
    """Detecta combinações suspeitas de tipos no mesmo módulo."""
    correlations = []
    module_types: dict[str, set] = defaultdict(set)

    for v in vulns:
        key = v.file_path or v.url or "desconhecido"
        parts = key.replace("\\", "/").split("/")
        module = "/".join(parts[:2]) if len(parts) > 1 else key
        module_types[module].add(v.scan_type.value)

    for module, types in module_types.items():
        if "SECRETS" in types and "SAST" in types:
            correlations.append(f"⚠ {module}: secrets expostos E falhas de código no mesmo módulo — risco combinado elevado.")
        if "DAST" in types and "SAST" in types:
            correlations.append(f"⚠ {module}: vulnerabilidade confirmada em runtime (DAST) e no código-fonte (SAST) — exploração ativa provável.")

    return correlations


def _build_risk_map(vulns: list[Vulnerability]) -> dict:
    risk_map: dict[str, dict] = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0})
    for v in vulns:
        key = v.file_path or v.url or "desconhecido"
        parts = key.replace("\\", "/").split("/")
        module = "/".join(parts[:2]) if len(parts) > 1 else key
        risk_map[module]["total"] += 1
        if v.severity == Severity.CRITICAL:
            risk_map[module]["critical"] += 1
        elif v.severity == Severity.HIGH:
            risk_map[module]["high"] += 1
    return dict(risk_map)


# ── Narrativa local (sem LLM) ────────────────────────────────────────────

def _local_narrative(report: AnomalyReport) -> str:
    parts = []
    if report.patterns:
        parts.append("Padrões detectados:\n" + "\n".join(f"• {p}" for p in report.patterns))
    if report.hotspots:
        parts.append("Módulos de maior risco:\n" + "\n".join(f"• {h}" for h in report.hotspots))
    if report.correlations:
        parts.append("Correlações suspeitas:\n" + "\n".join(f"• {c}" for c in report.correlations))
    return "\n\n".join(parts) if parts else "Nenhum padrão significativo detectado."


# ── Análise narrativa do LLM ─────────────────────────────────────────────

def _llm_analysis(
    vulns: list[Vulnerability],
    local_report: AnomalyReport,
    provider: LLMProvider,
) -> str:
    sev_counts = Counter(v.severity.value for v in vulns)
    type_counts = Counter(v.scan_type.value for v in vulns)

    prompt = f"""Analise os seguintes dados de segurança de uma aplicação e identifique
padrões preocupantes, anomalias e correlações que merecem atenção.

DADOS QUANTITATIVOS:
- Total de vulnerabilidades: {len(vulns)}
- Por severidade: {dict(sev_counts)}
- Por tipo de scan: {dict(type_counts)}

PADRÕES JÁ DETECTADOS AUTOMATICAMENTE:
{chr(10).join(f'- {p}' for p in local_report.patterns) or '(nenhum)'}

HOTSPOTS (módulos mais afetados):
{chr(10).join(f'- {h}' for h in local_report.hotspots) or '(nenhum)'}

CORRELAÇÕES SUSPEITAS:
{chr(10).join(f'- {c}' for c in local_report.correlations) or '(nenhuma)'}

Com base nesses dados, escreva uma análise em 3 parágrafos:
1. O que os padrões indicam sobre a maturidade de segurança do projeto
2. Quais anomalias são mais preocupantes e por quê
3. Recomendações estratégicas (não apenas táticas) para melhorar a postura"""

    try:
        response = provider.chat(prompt, system=SYSTEM_PROMPT, timeout=90)
        return response.text
    except Exception as e:
        return _local_narrative(local_report) + f"\n\n(Análise de IA indisponível: {e})"

"""
ai/prioritizer.py
Função 2 — Priorização inteligente de vulnerabilidades.

Combina heurísticas determinísticas (rápidas) com raciocínio do LLM
para gerar uma lista ordenada de "o que corrigir primeiro" com justificativa.

Arquitetura:
  1. Pre-score determinístico (sem LLM) — instantâneo
  2. LLM re-rank das top-N — adiciona contexto e raciocínio
"""
from dataclasses import dataclass
from ai.provider import LLMProvider
from core.models import Vulnerability, Severity, ScanType

SYSTEM_PROMPT = """Você é um analista sênior de segurança de aplicações (AppSec).
Sua função é priorizar vulnerabilidades para times de desenvolvimento com base em
risco real, exploitabilidade e impacto ao negócio.
Responda sempre em português brasileiro e em formato JSON válido."""

# Pesos do pre-score determinístico (0-100)
SEV_SCORE   = {Severity.CRITICAL: 40, Severity.HIGH: 25, Severity.MEDIUM: 10, Severity.LOW: 3, Severity.INFO: 0}
TYPE_SCORE  = {ScanType.SECRETS: 20, ScanType.DAST: 15, ScanType.SAST: 10, ScanType.SCA: 8}
CVSS_WEIGHT = 2.5   # multiplicador do CVSS score


@dataclass
class PrioritizedVuln:
    vuln: Vulnerability
    pre_score: float          # score determinístico (0-100)
    ai_rank: int | None       # posição no ranking do LLM (1 = mais urgente)
    ai_reason: str            # justificativa do LLM
    final_score: float        # score final combinado


def pre_score(vuln: Vulnerability) -> float:
    """Score determinístico rápido — não usa LLM."""
    score = SEV_SCORE.get(vuln.severity, 0)
    score += TYPE_SCORE.get(vuln.scan_type, 0)
    if vuln.cvss_score:
        score += vuln.cvss_score * CVSS_WEIGHT
    # Penalidade extra: secrets sempre sobem
    if vuln.scan_type == ScanType.SECRETS:
        score += 15
    return min(score, 100.0)


def prioritize(
    vulns: list[Vulnerability],
    provider: LLMProvider,
    top_n: int = 10,
) -> list[PrioritizedVuln]:
    """
    Retorna lista de PrioritizedVuln ordenada do mais urgente para o menos.

    Fluxo:
      1. Calcula pre_score para todas as vulns
      2. Seleciona top_n pelo pre_score para enviar ao LLM
      3. LLM re-ranqueia e justifica
      4. Combina scores e retorna lista completa ordenada
    """
    if not vulns:
        return []

    # Passo 1: pre-score de todas
    scored = [(v, pre_score(v)) for v in vulns]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Passo 2: top_n para o LLM
    top = scored[:top_n]
    rest = scored[top_n:]

    # Passo 3: LLM re-rank
    ai_results: dict[str, tuple[int, str]] = {}
    if provider.available:
        ai_results = _llm_rerank(top, provider)

    # Passo 4: montar PrioritizedVuln
    result: list[PrioritizedVuln] = []

    for i, (vuln, ps) in enumerate(top):
        ai_rank, ai_reason = ai_results.get(vuln.id, (i + 1, "Priorizado pelo score automático."))
        # Score final: 70% pre_score + 30% peso inverso do rank LLM
        ai_weight = max(0, (top_n - ai_rank + 1) / top_n * 100)
        final = round(ps * 0.7 + ai_weight * 0.3, 1)
        result.append(PrioritizedVuln(vuln=vuln, pre_score=ps, ai_rank=ai_rank, ai_reason=ai_reason, final_score=final))

    for vuln, ps in rest:
        result.append(PrioritizedVuln(vuln=vuln, pre_score=ps, ai_rank=None, ai_reason="Fora do top analisado pela IA.", final_score=ps))

    result.sort(key=lambda x: x.final_score, reverse=True)
    return result


def _llm_rerank(
    scored: list[tuple[Vulnerability, float]],
    provider: LLMProvider,
) -> dict[str, tuple[int, str]]:
    """Pede ao LLM para reordenar e justificar as top vulns."""
    vuln_list = []
    for i, (v, ps) in enumerate(scored):
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
        })

    prompt = f"""Você recebeu as seguintes vulnerabilidades detectadas em uma aplicação.
Re-ordene-as da mais urgente para a menos urgente considerando:
- Exploitabilidade real (secrets e DAST tendem a ser mais exploráveis)
- Impacto ao negócio
- Facilidade de exploração
- Se há CVE conhecido e CVSS alto

Vulnerabilidades:
{__import__('json').dumps(vuln_list, ensure_ascii=False, indent=2)}

Responda APENAS com JSON válido, sem texto antes ou depois, neste formato:
{{
  "ranking": [
    {{
      "id": "<id da vuln>",
      "rank": 1,
      "reason": "Justificativa em 1 frase em português"
    }}
  ]
}}"""

    try:
        response = provider.chat(prompt, system=SYSTEM_PROMPT, timeout=90)
        # Strip possível markdown do LLM
        text = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = __import__('json').loads(text)
        return {
            item["id"]: (item["rank"], item["reason"])
            for item in data.get("ranking", [])
        }
    except Exception as e:
        # Se o LLM falhar, retorna dict vazio (pre_score assume controle)
        print(f"[prioritizer] LLM rerank falhou: {e}")
        return {}

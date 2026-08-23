"""
ai/explainer.py
Função 1 — Explicar vulnerabilidades em linguagem simples.

Recebe uma Vulnerability e retorna uma explicação estruturada
em português, sem jargão técnico excessivo.
"""
from ai.provider import LLMProvider, LLMResponse
from core.models import Vulnerability

SYSTEM_PROMPT = """Você é um especialista em cibersegurança que explica vulnerabilidades
para times de desenvolvimento. Seja claro, direto e prático.
Sempre responda em português brasileiro.
Nunca invente CVEs ou referências que não foram fornecidas."""


def explain_vulnerability(vuln: Vulnerability, provider: LLMProvider) -> LLMResponse:
    """
    Gera uma explicação em linguagem simples para uma vulnerabilidade.
    Retorna LLMResponse com o texto gerado.
    """
    # Trunca campos longos para evitar estouro de token limit no Groq free tier
    def _trunc(text: str, limit: int = 300) -> str:
        return text[:limit] + "..." if len(text) > limit else text

    context_parts = [
        f"Título: {vuln.title}",
        f"Ferramenta: {vuln.tool.upper()} ({vuln.scan_type.value})",
        f"Severidade: {vuln.severity.value.upper()}",
    ]
    if vuln.file_path:
        context_parts.append(f"Arquivo: {vuln.file_path}")
    if vuln.line:
        context_parts.append(f"Linha: {vuln.line}")
    if vuln.url:
        context_parts.append(f"URL: {_trunc(vuln.url, 100)}")
    if vuln.cve_id:
        context_parts.append(f"CVE: {vuln.cve_id}")
    if vuln.cvss_score:
        context_parts.append(f"CVSS: {vuln.cvss_score}")
    if vuln.description:
        context_parts.append(f"Descrição: {_trunc(vuln.description, 400)}")
    if vuln.remediation:
        context_parts.append(f"Remediação sugerida: {_trunc(vuln.remediation, 200)}")

    context = "\n".join(context_parts)

    prompt = f"""Analise esta vulnerabilidade e responda em 4 seções curtas:

{context}

**O QUE É**
[2 frases simples explicando a vulnerabilidade]

**POR QUE É PERIGOSA**
[2 frases sobre o impacto real para o sistema]

**COMO CORRIGIR**
[3 passos práticos de correção]

**PRIORIDADE**
[Uma frase: imediata / 7 dias / próximo ciclo, e por quê]"""

    return provider.chat(prompt, system=SYSTEM_PROMPT)


def explain_batch_summary(vulns: list[Vulnerability], provider: LLMProvider) -> LLMResponse:
    """
    Gera um resumo executivo de um conjunto de vulnerabilidades.
    Útil para relatórios e apresentações.
    """
    from collections import Counter
    sev_counts = Counter(v.severity.value for v in vulns)
    tool_counts = Counter(v.tool for v in vulns)

    top_vulns = sorted(vulns, key=lambda v: ["critical","high","medium","low","info"].index(v.severity.value))[:5]
    top_list = "\n".join(f"- [{v.severity.value.upper()}] {v.title} ({v.tool})" for v in top_vulns)

    prompt = f"""Gere um resumo executivo de segurança com base nos dados abaixo.
Escreva em português para um gestor não técnico entender.

DADOS DO SCAN:
Total de vulnerabilidades: {len(vulns)}
Por severidade: {dict(sev_counts)}
Por ferramenta: {dict(tool_counts)}

Top 5 vulnerabilidades mais críticas:
{top_list}

Responda em 3 parágrafos curtos:
1. Situação atual (como está a postura de segurança)
2. Principais riscos identificados
3. Recomendações prioritárias de ação"""

    return provider.chat(prompt, system=SYSTEM_PROMPT)

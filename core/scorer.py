"""
core/scorer.py
Calcula o score de RISCO de postura de segurança (0-100).

Escala: 0 = risco mínimo (melhor postura), 100 = risco máximo (pior postura).

Fórmula:
  Score = penalidade_ponderada, com teto em 100
  Pesos por severidade: Critical=+25, High=+10, Medium=+3, Low=+1
  Score máximo = 100
"""
from core.models import Vulnerability, Severity, ScanType, PostureScore

WEIGHTS = {
    Severity.CRITICAL: 25,
    Severity.HIGH:     10,
    Severity.MEDIUM:    3,
    Severity.LOW:       1,
    Severity.INFO:      0,
}

# Penalidade máxima por tipo de scan (para o score breakdown)
MAX_PENALTY_PER_TYPE = 100


def calculate(vulnerabilities: list[Vulnerability]) -> PostureScore:
    """Calcula o PostureScore (escala de risco) a partir da lista de vulnerabilidades abertas."""
    open_vulns = [v for v in vulnerabilities if v.status.value == "open"]

    counts = {s: 0 for s in Severity}
    for v in open_vulns:
        counts[v.severity] += 1

    total_penalty = sum(WEIGHTS[sev] * count for sev, count in counts.items())
    overall = min(100.0, total_penalty)

    # Score por tipo de scan
    by_type: dict[str, float] = {}
    for scan_type in ScanType:
        type_vulns = [v for v in open_vulns if v.scan_type == scan_type]
        penalty = sum(WEIGHTS[v.severity] for v in type_vulns)
        by_type[scan_type.value] = min(100.0, penalty)

    return PostureScore(
        overall=round(overall, 1),
        by_scan_type=by_type,
        critical_count=counts[Severity.CRITICAL],
        high_count=counts[Severity.HIGH],
        medium_count=counts[Severity.MEDIUM],
        low_count=counts[Severity.LOW],
        total=len(open_vulns),
    )

"""
core/models.py
Modelos de dados centrais do ASPM.
Todas as ferramentas convertem seus achados para esses dataclasses.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class ScanType(str, Enum):
    SAST      = "SAST"
    DAST      = "DAST"
    SCA       = "SCA"
    SECRETS   = "SECRETS"
    CONTAINER = "CONTAINER"  # novo: CVEs em imagens Docker (ex.: Trivy)
    IAC       = "IAC"        # novo: más configurações em Terraform/K8s/Dockerfile (ex.: Trivy, Checkov)


class Status(str, Enum):
    OPEN       = "open"
    IN_REVIEW  = "in_review"
    FIXED      = "fixed"
    ACCEPTED   = "accepted"   # risco aceito intencionalmente


@dataclass
class Vulnerability:
    """Vulnerabilidade normalizada — formato único independente da ferramenta."""
    id: str                          # gerado internamente (uuid)
    title: str
    severity: Severity
    scan_type: ScanType
    tool: str                        # "semgrep" | "zap" | "snyk" | "gitleaks"
    file_path: Optional[str] = None  # arquivo afetado (SAST/Secrets)
    line: Optional[int] = None       # linha do código
    url: Optional[str] = None        # endpoint afetado (DAST)
    cve_id: Optional[str] = None     # CVE quando disponível (SCA)
    cvss_score: Optional[float] = None
    description: str = ""
    remediation: str = ""
    status: Status = Status.OPEN
    found_at: datetime = field(default_factory=datetime.now)
    rule_id: Optional[str] = None    # ID da regra na ferramenta de origem
    asset_id: Optional[str] = None   # vincula a um Asset (core/asset.py) — contexto por ativo


@dataclass
class ScanReport:
    """Representa um relatório importado de uma ferramenta."""
    tool: str
    scan_type: ScanType
    target: str                      # app/repo/url escaneado
    scanned_at: datetime
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    raw_file: Optional[str] = None   # caminho do arquivo importado


@dataclass
class PostureScore:
    """Score de postura calculado pelo scorer.py."""
    overall: float                   # 0-100 (0 = risco mínimo/melhor postura, 100 = risco máximo)
    by_scan_type: dict[str, float] = field(default_factory=dict)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total: int = 0
